"""Jogo: a fachada que a interface usa (spec 07). Única porta entre a tela e a lógica.

A interface não conhece fila, semáforo nem thread: só o Jogo. Fora o `encerrar`,
nenhum método bloqueia mais que um lock curto, porque todos rodam na thread da tela.
"""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from cozinha.config import Config
from cozinha.modelo.estacoes import Cozinha
from cozinha.modelo.fila import FilaDePedidos
from cozinha.modelo.partida import Partida
from cozinha.modelo.pontuacao import Pontuacao
from cozinha.modelo.relogio import Relogio
from cozinha.modelo.retrato import Retrato
from cozinha.modelo.tipos import EstadoPartida, TipoEstacao
from cozinha.threads.cozinheiro import Cozinheiro
from cozinha.threads.gerador import GeradorDePedidos
from cozinha.threads.jogador import CozinheiroJogador, Desistir, PegarPedido, UsarEstacao

log = logging.getLogger(__name__)


class Jogo:
    def __init__(self, config: Config, fonte_tempo: Callable[[], float] = time.monotonic) -> None:
        # Monta tudo, nesta ordem, sem iniciar thread nenhuma (os testes inspecionam parado).
        self._config = config
        self._parar = threading.Event()
        self._relogio = Relogio(fonte_tempo)
        self._pontuacao = Pontuacao(config)
        self._partida = Partida(config, self._relogio, self._pontuacao)
        self._cozinha = Cozinha(config)
        self._fila = FilaDePedidos(config.tamanho_max_fila)
        self._gerador = GeradorDePedidos(self._fila, self._relogio, config, self._parar)
        # Single player: o cozinheiro 1 é do jogador (executa comandos da tela);
        # os outros são automáticos e disputam as mesmas estações com ele.
        self._cozinheiros: list[Cozinheiro] = [
            (CozinheiroJogador if config.jogador and i == 1 else Cozinheiro)(
                i, self._fila, self._cozinha, self._pontuacao, self._relogio, config, self._parar)
            for i in range(1, config.n_cozinheiros + 1)
        ]
        self._jogador: CozinheiroJogador | None = (
            self._cozinheiros[0] if config.jogador else None)  # type: ignore[assignment]
        self._lock = threading.Lock()          # protege as flags e o selecionado
        self._iniciado = False
        self._encerrado = False
        self._selecionado: int | None = None

    def _threads(self) -> list[threading.Thread]:
        return [self._gerador, *self._cozinheiros]

    def iniciar(self) -> None:
        """Chamar duas vezes, ou depois de encerrar, não faz nada."""
        with self._lock:
            if self._iniciado or self._encerrado:
                return
            self._iniciado = True
        self._partida.iniciar()                # também inicia o relógio
        for t in self._threads():
            t.start()

    def atualizar(self) -> None:
        """1x por quadro: confere as threads, expira pedidos e checa o fim."""
        if self._partida.estado is not EstadoPartida.RODANDO:
            return
        for t in self._threads():
            if t.erro is not None:
                self._sinalizar_parada()
                raise RuntimeError(f"a thread {t.name} morreu: {t.erro!r}") from t.erro
        if self._config.expiracao:
            for pedido in self._fila.remover_expirados(self._relogio.agora()):
                self._pontuacao.registrar_perda(pedido)          # RF09
        self._partida.verificar_fim()
        if self._partida.terminou:
            self._sinalizar_parada()

    def retrato(self) -> Retrato:
        """Cópia imutável do jogo (RC06). Cada parte copiada sob o próprio lock, uma de cada vez.

        Pode ficar desalinhado por milissegundos (um pedido na fila e no cozinheiro ao
        mesmo tempo): o do cozinheiro vence e o resto some no quadro seguinte.
        """
        agora = self._relogio.agora()
        pontos, entregues, perdidos = self._pontuacao.valores()
        na_fila = self._fila.views(agora)
        em_preparo = [v for c in self._cozinheiros if (v := c.pedido_view(agora))]
        pedidos = {v.id: v for v in na_fila} | {v.id: v for v in em_preparo}
        estacoes, grupos = self._cozinha.views()
        with self._lock:
            selecionado = self._selecionado
        return Retrato(
            estado=self._partida.estado,
            tempo_restante=self._partida.tempo_restante(),
            pontos=pontos,
            meta=self._config.meta_pontos,
            meta_batida=self._partida.meta_batida,
            perdidos=perdidos,
            limite_perdidos=self._config.limite_perdidos,
            entregues=entregues,
            tamanho_max_fila=self._fila.tamanho_max,
            pedidos=tuple(pedidos[i] for i in sorted(pedidos)),
            cozinheiros=tuple(c.view() for c in self._cozinheiros),
            estacoes=estacoes,
            grupos=grupos,
            selecionado=selecionado,
        )

    def selecionar(self, cozinheiro_id: int) -> None:
        """Id fora de 1..n_cozinheiros é ignorado."""
        if 1 <= cozinheiro_id <= self._config.n_cozinheiros:
            with self._lock:
                self._selecionado = cozinheiro_id

    def atribuir(self, pedido_id: int) -> None:
        """Ordem do jogador ao selecionado. A reserva na fila já é a mensagem (spec 03)."""
        with self._lock:
            selecionado = self._selecionado
        if selecionado is not None:
            self._fila.reservar(pedido_id, selecionado)

    # ---------- comandos do jogador (single player): só enfileiram, nunca bloqueiam ----------

    def pegar_pedido(self, pedido_id: int | None = None) -> None:
        """Pega o pedido (ou o mais antigo livre). Sem jogador, não faz nada."""
        if self._jogador is not None:
            self._jogador.comandar(PegarPedido(pedido_id))

    def usar_estacao(self, tipo: TipoEstacao) -> None:
        if self._jogador is not None:
            self._jogador.comandar(UsarEstacao(tipo))

    def desistir(self) -> None:
        """Na fila de uma estação: sai da fila. Parado com pedido: descarta o pedido."""
        if self._jogador is not None:
            self._jogador.comandar(Desistir())

    def pausar(self) -> None:
        self._partida.pausar()                 # a Partida já pausa o relógio

    def retomar(self) -> None:
        self._partida.retomar()

    def _sinalizar_parada(self) -> None:
        """Não bloqueia: as threads saem sozinhas em poucos ticks."""
        self._parar.set()
        self._relogio.congelar()               # também solta quem esperava a pausa

    def encerrar(self, timeout: float = 2.0) -> list[str]:
        """Para e espera as threads. Devolve os nomes das que não terminaram."""
        with self._lock:
            self._encerrado = True
        self._sinalizar_parada()
        iniciadas = [t for t in self._threads() if t.ident is not None]
        for t in iniciadas:
            t.join(timeout=timeout / len(iniciadas))
        presas = [t.name for t in iniciadas if t.is_alive()]
        if presas:
            log.warning("threads que não terminaram: %s", presas)
        return presas
