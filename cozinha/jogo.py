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
from cozinha.modelo.tipos import EstadoPartida
from cozinha.threads.cozinheiro import Cozinheiro
from cozinha.threads.gerador import GeradorDePedidos

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
        self._cozinheiros = [
            Cozinheiro(i, self._fila, self._cozinha, self._pontuacao, self._relogio,
                       config, self._parar)
            for i in range(1, config.n_cozinheiros + 1)
        ]
        self._lock = threading.Lock()          # protege as flags e o selecionado
        self._iniciado = False
        self._encerrado = False

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
