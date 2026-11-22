"""Thread do cozinheiro (spec 04): pega um pedido, faz as etapas nas estações e entrega."""
from __future__ import annotations

import logging
import threading
from threading import Event

from cozinha.config import Config
from cozinha.modelo.estacoes import Cozinha, Reserva
from cozinha.modelo.fila import FilaDePedidos
from cozinha.modelo.pedido import Pedido
from cozinha.modelo.pontuacao import Pontuacao
from cozinha.modelo.receita import Etapa
from cozinha.modelo.relogio import Relogio
from cozinha.modelo.retrato import CozinheiroView, PedidoView
from cozinha.modelo.tipos import EstadoCozinheiro, EstadoPedido, TipoEstacao

LIVRE, ESPERANDO, TRABALHANDO = EstadoCozinheiro
log = logging.getLogger(__name__)


class Cozinheiro(threading.Thread):
    def __init__(self, id: int, fila: FilaDePedidos, cozinha: Cozinha,
                 pontuacao: Pontuacao, relogio: Relogio, config: Config,
                 parar: Event) -> None:
        super().__init__(name=f"cozinheiro-{id}", daemon=True)
        self.id = id
        self._fila = fila
        self._cozinha = cozinha
        self._pontuacao = pontuacao
        self._relogio = relogio
        self._config = config
        self._parar = parar
        self.erro: BaseException | None = None
        # Estado para a tela: só esta thread escreve; view() copia sob o lock.
        self._lock = threading.Lock()
        self._estado = LIVRE
        self._pedido: Pedido | None = None
        self._etapa: str | None = None
        self._progresso = 0.0
        self._segurando: tuple[tuple[TipoEstacao, int], ...] = ()
        self._esperando: TipoEstacao | None = None
        self._esperando_desde = 0.0
        self._espera_total = 0.0

    # ---------- loop ----------

    def run(self) -> None:
        """Uma thread nunca morre em silêncio: a exceção fica em `erro` (spec 07 confere)."""
        try:
            self._loop()
        except BaseException as exc:
            # As estações já foram soltas pelos finally de _fazer_etapa / ocupar_todas.
            with self._lock:
                pedido = self._pedido
            if pedido is not None and pedido.estado is EstadoPedido.EM_PREPARO:
                self._pontuacao.registrar_perda(pedido)
            self.erro = exc
            log.exception("%s morreu com uma exceção", self.name)
        finally:
            self._mudar(estado=LIVRE, segurando=(), esperando=None)

    def _loop(self) -> None:
        tick = self._config.tick
        while not self._parar.is_set():
            self._relogio.esperar_rodando(self._parar, tick)
            if self._parar.is_set():
                break
            pedido = self._fila.retirar(self.id, timeout=tick)
            if pedido is None:
                self._parar.wait(tick)
                continue
            with self._lock:
                self._pedido = pedido
            for etapa in pedido.receita.etapas:
                if not self._fazer_etapa(pedido, etapa):
                    break
            self._mudar(estado=LIVRE, pedido=None, etapa=None, progresso=0.0)

    def _expirou(self, pedido: Pedido) -> bool:
        return self._config.expiracao and pedido.expirou(self._relogio.agora())

    def _fazer_etapa(self, pedido: Pedido, etapa: Etapa) -> bool:
        """Faz uma etapa. False se o pedido acabou (expirou ou parar)."""
        if self._expirou(pedido):
            self._pontuacao.registrar_perda(pedido)
            return False
        reservas = self._cozinha.ocupar_todas(
            self.id, etapa.estacoes,
            cancelar=lambda: self._parar.is_set() or self._expirou(pedido),
            ao_mudar=self._ao_mudar)
        if reservas is None:
            if not self._parar.is_set():
                self._pontuacao.registrar_perda(pedido)      # desistiu porque expirou
            return False
        expirou = False
        try:
            self._relogio.esperar_rodando(self._parar, self._config.tick)  # pegou na pausa: espera
            self._mudar(estado=TRABALHANDO, etapa=etapa.nome, progresso=0.0)
            # Na entrega, com o balcão na mão, o prato já está saindo: não expira mais.
            vigiar = None if etapa.entrega else pedido
            resultado = self._trabalhar(etapa.duracao, vigiar)
            if resultado == "expirou":
                expirou = True
                return False
            if resultado == "parar":
                return False
            if etapa.entrega:
                # Solta o fogão (empratar) e deixa o prato no balcão enquanto o cliente
                # retira: é isso que faz o balcão de capacidade limitada encher (RF13).
                outras = tuple(r for r in reservas if r.tipo is not TipoEstacao.BALCAO)
                self._cozinha.liberar(outras)
                reservas = tuple(r for r in reservas if r.tipo is TipoEstacao.BALCAO)
                self._mudar(segurando=tuple((r.tipo, r.indice) for r in reservas))
                if self._trabalhar(self._config.tempo_retirada, None, progresso=False) == "parar":
                    return False
                self._pontuacao.registrar_entrega(pedido, self._relogio.agora())
            return True
        finally:
            self._cozinha.liberar(reservas)
            self._mudar(segurando=())
            if expirou:
                self._pontuacao.registrar_perda(pedido)

    def _trabalhar(self, duracao: float, vigiar: Pedido | None, progresso: bool = True) -> str:
        """Espera `duracao` de tempo de jogo em ticks pausáveis.

        Devolve "ok", "parar" ou "expirou" (só se `vigiar` não for None).
        """
        tick = self._config.tick
        feito = 0.0
        anterior = self._relogio.agora()
        while feito < duracao:
            self._relogio.esperar_rodando(self._parar, tick)
            if self._parar.wait(tick):
                return "parar"
            agora = self._relogio.agora()
            feito += agora - anterior
            anterior = agora
            if progresso:
                self._mudar(progresso=min(1.0, feito / duracao))
            if vigiar is not None and self._expirou(vigiar):
                return "expirou"
        if progresso:
            self._mudar(progresso=1.0)
        return "ok"

    # ---------- estado para a tela ----------

    def _mudar(self, **campos) -> None:
        with self._lock:
            for nome, valor in campos.items():
                setattr(self, f"_{nome}", valor)

    def _ao_mudar(self, segurando: tuple[Reserva, ...], esperando: TipoEstacao | None) -> None:
        """Chamado pela Cozinha durante a aquisição. Converte Reserva em (tipo, indice)."""
        agora = self._relogio.agora()
        with self._lock:
            self._segurando = tuple((r.tipo, r.indice) for r in segurando)
            if esperando is not None and self._esperando is None:
                self._esperando_desde = agora
                self._estado = ESPERANDO
            elif esperando is None and self._esperando is not None:
                self._espera_total += agora - self._esperando_desde
            self._esperando = esperando

    def view(self) -> CozinheiroView:
        agora = self._relogio.agora()
        with self._lock:
            esperando_ha = 0.0
            if self._esperando is not None:
                esperando_ha = max(0.0, agora - self._esperando_desde)
            return CozinheiroView(
                id=self.id, estado=self._estado,
                pedido_id=self._pedido.id if self._pedido else None,
                etapa=self._etapa, progresso=self._progresso,
                segurando=self._segurando, esperando=self._esperando,
                esperando_ha=esperando_ha,
                espera_total=self._espera_total + esperando_ha)

    def pedido_view(self, agora: float) -> PedidoView | None:
        with self._lock:
            p = self._pedido
        if p is None or p.estado in (EstadoPedido.ENTREGUE, EstadoPedido.PERDIDO):
            return None
        return PedidoView(p.id, p.receita.nome, EstadoPedido.EM_PREPARO,
                          p.paciencia_restante(agora), self.id, None)
