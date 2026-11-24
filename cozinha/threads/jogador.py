"""O cozinheiro do jogador (single player): uma thread que executa comandos da tela.

Usa exatamente o mesmo caminho dos automáticos para as estações (`_fazer_etapa` →
`Cozinha.ocupar_todas`): espera na fila justa, ordem fixa, nunca segura estação
entre etapas. A tela só enfileira comandos; nada aqui bloqueia a thread da tela.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, replace
from threading import Event

from cozinha.config import Config
from cozinha.modelo.estacoes import Cozinha
from cozinha.modelo.fila import FilaDePedidos
from cozinha.modelo.pedido import Pedido
from cozinha.modelo.pontuacao import Pontuacao
from cozinha.modelo.relogio import Relogio
from cozinha.modelo.retrato import CozinheiroView
from cozinha.modelo.tipos import EstadoCozinheiro, EstadoPedido, TipoEstacao
from cozinha.threads.cozinheiro import Cozinheiro

LIVRE, ESPERANDO, TRABALHANDO = EstadoCozinheiro
NOMES = {TipoEstacao.TABUA: "TÁBUA", TipoEstacao.PIA: "PIA",
         TipoEstacao.FOGAO: "FOGÃO", TipoEstacao.BALCAO: "BALCÃO"}


@dataclass(frozen=True)
class PegarPedido:
    pedido_id: int | None = None      # None: o mais antigo da fila que não é de outro


@dataclass(frozen=True)
class UsarEstacao:
    tipo: TipoEstacao


@dataclass(frozen=True)
class Desistir:
    """Na fila de uma estação: sai da fila (o pedido continua na mão). Parado: descarta."""
    quando: float = 0.0               # preenchido pelo comandar (time.monotonic)


Comando = PegarPedido | UsarEstacao | Desistir


def _nomes(tipos: tuple[TipoEstacao, ...]) -> str:
    return " + ".join(NOMES[t] for t in tipos)


class CozinheiroJogador(Cozinheiro):
    def __init__(self, id: int, fila: FilaDePedidos, cozinha: Cozinha,
                 pontuacao: Pontuacao, relogio: Relogio, config: Config,
                 parar: Event) -> None:
        super().__init__(id, fila, cozinha, pontuacao, relogio, config, parar)
        self._comandos: queue.Queue[Comando] = queue.Queue()
        self._desistir = threading.Event()   # lido pelo `cancelar` enquanto espera estação
        self._indice = 0                     # etapa da receita que falta fazer
        self._mensagem: str | None = None
        self._usar_inicio = -1.0             # quando o último UsarEstacao começou e terminou
        self._usar_fim = -1.0                # (para ignorar um Q que era para ele)

    # ---------- entrada (thread da tela) ----------

    def comandar(self, comando: Comando) -> None:
        """Não bloqueia. O `Desistir` (tecla Q) nunca joga fora um pedido sem querer:

        - na fila de uma estação: sai da fila na hora (o pedido continua na mão);
        - trabalhando numa etapa: ignorado (a etapa não se interrompe);
        - com comandos ainda na fila (ex.: E e Q durante a pausa): cancela esses comandos;
        - parado com pedido: descarta o pedido.
        """
        if isinstance(comando, Desistir):
            with self._lock:
                estado = self._estado
            if estado is TRABALHANDO:
                return
            if estado is ESPERANDO:
                self._desistir.set()
                return
            cancelou = False
            while True:
                try:
                    self._comandos.get_nowait()
                    cancelou = True
                except queue.Empty:
                    break
            if cancelou:
                return
            comando = Desistir(quando=time.monotonic())
        self._comandos.put_nowait(comando)

    # ---------- loop (esta thread) ----------

    def _loop(self) -> None:
        tick = self._config.tick
        while not self._parar.is_set():
            self._relogio.esperar_rodando(self._parar, tick)
            if self._parar.is_set():
                break
            self._vigiar_pedido()
            try:
                comando = self._comandos.get(timeout=tick)
            except queue.Empty:
                continue
            recebido = time.monotonic()      # um Q depois disto e antes do fim é para este comando
            self._relogio.esperar_rodando(self._parar, tick)   # comando chegou na pausa
            if self._parar.is_set():
                break
            self._vigiar_pedido()
            match comando:
                case PegarPedido(pedido_id=pid):
                    self._pegar(pid)
                case UsarEstacao(tipo=tipo):
                    self._usar_inicio = recebido
                    self._usar(tipo)
                    self._usar_fim = time.monotonic()
                case Desistir(quando=quando):
                    if self._usar_inicio <= quando <= self._usar_fim:
                        continue        # o Q era para a etapa que acabou de rodar, não descarte
                    self._descartar()

    def _vigiar_pedido(self) -> None:
        """Paciência acabou com o pedido parado na mão: perdido, como para os automáticos."""
        with self._lock:
            pedido = self._pedido
        if pedido is not None and pedido.estado is EstadoPedido.EM_PREPARO and self._expirou(pedido):
            self._pontuacao.registrar_perda(pedido)
            self._largar(f"O cliente do pedido #{pedido.id} foi embora")

    def _largar(self, mensagem: str) -> None:
        self._mudar(pedido=None, indice=0, mensagem=mensagem, estado=LIVRE, etapa=None,
                    progresso=0.0, esperando=None, segurando=())

    def _pegar(self, pedido_id: int | None) -> None:
        with self._lock:
            atual = self._pedido
        if atual is not None:
            self._mudar(mensagem=f"Você já está com o pedido #{atual.id}")
            return
        agora = self._relogio.agora()
        if pedido_id is None:
            livres = [v.id for v in self._fila.views(agora) if v.reservado_para in (None, self.id)]
            if not livres:
                self._mudar(mensagem="Nenhum pedido livre no quadro")
                return
            pedido_id = livres[0]
        if not self._fila.reservar(pedido_id, self.id):
            self._mudar(mensagem=f"O pedido #{pedido_id} já saiu")
            return
        # Reservado para mim: nenhum outro o pega, e o retirar me entrega ele primeiro.
        pedido: Pedido | None = None
        while not self._parar.is_set():
            pedido = self._fila.retirar(self.id, timeout=self._config.tick)
            if pedido is not None:
                break
            if all(v.id != pedido_id for v in self._fila.views(self._relogio.agora())):
                self._mudar(mensagem=f"O pedido #{pedido_id} já saiu")   # expirou na fila
                return
        if pedido is None:
            return
        self._mudar(pedido=pedido, indice=0,
                    mensagem=f"Pegou o pedido #{pedido.id} ({pedido.receita.nome})")

    def _usar(self, tipo: TipoEstacao) -> None:
        with self._lock:
            pedido, indice = self._pedido, self._indice
        if pedido is None:
            self._mudar(mensagem="Pegue um pedido no quadro primeiro")
            return
        etapa = pedido.receita.etapas[indice]
        if tipo not in etapa.estacoes:
            self._mudar(mensagem=f"Agora o pedido #{pedido.id} precisa de {_nomes(etapa.estacoes)}")
            return
        self._desistir.clear()
        ok = self._fazer_etapa(pedido, etapa, desistir=self._desistir.is_set)
        if self._parar.is_set():
            return
        if ok:
            if indice + 1 == len(pedido.receita.etapas):
                self._largar(f"Pedido #{pedido.id} entregue!")
                return
            proxima = pedido.receita.etapas[indice + 1]
            self._mudar(indice=indice + 1, estado=LIVRE, etapa=None, progresso=0.0,
                        mensagem=f"{etapa.nome.capitalize()}: feito. Agora: {_nomes(proxima.estacoes)}")
        elif self._desistir.is_set():
            self._desistir.clear()
            self._mudar(estado=LIVRE, esperando=None,
                        mensagem=f"Você saiu da fila da {_nomes(etapa.estacoes)}")
        else:
            self._largar(f"O cliente do pedido #{pedido.id} foi embora")

    def _descartar(self) -> None:
        with self._lock:
            pedido = self._pedido
        if pedido is None:
            self._mudar(mensagem="Você não está com nenhum pedido")
            return
        if pedido.estado is EstadoPedido.EM_PREPARO:
            self._pontuacao.registrar_perda(pedido)
        self._largar(f"Pedido #{pedido.id} descartado")

    def livre(self) -> bool:
        """Sem pedido na mão: os automáticos esperam `atraso_automaticos` por ele."""
        with self._lock:
            return self._pedido is None

    # ---------- estado para a tela ----------

    def view(self) -> CozinheiroView:
        base = super().view()
        with self._lock:
            pedido, indice, mensagem, estado = self._pedido, self._indice, self._mensagem, self._estado
        proxima: tuple[TipoEstacao, ...] = ()
        if pedido is not None and estado is LIVRE and indice < len(pedido.receita.etapas):
            proxima = pedido.receita.etapas[indice].estacoes
        return replace(base, jogador=True, proxima=proxima, mensagem=mensagem)
