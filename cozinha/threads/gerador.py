"""Thread produtora (spec 05): cria clientes em intervalos cada vez menores."""
from __future__ import annotations

import logging
import random
import threading
from threading import Event

from cozinha.config import Config
from cozinha.modelo.fila import FilaDePedidos
from cozinha.modelo.pedido import Pedido
from cozinha.modelo.receita import Receita
from cozinha.modelo.relogio import Relogio

log = logging.getLogger(__name__)


class GeradorDePedidos(threading.Thread):
    def __init__(self, fila: FilaDePedidos, relogio: Relogio, config: Config,
                 parar: Event) -> None:
        super().__init__(name="gerador", daemon=True)
        self._fila = fila
        self._relogio = relogio
        self._config = config
        self._parar = parar
        self._rng = random.Random(config.semente)   # próprio da thread: testes reproduzíveis
        self.erro: BaseException | None = None
        self._ultimo_id = 0      # só esta thread cria pedidos: sem lock

    def run(self) -> None:
        """Uma thread nunca morre em silêncio: a exceção fica em `erro` (spec 07 confere)."""
        try:
            self._loop()
        except BaseException as exc:
            self.erro = exc
            log.exception("gerador morreu com uma exceção")

    def _loop(self) -> None:
        primeiro = True
        while not self._parar.is_set():
            if not primeiro and not self._esperar(self.intervalo(self._relogio.agora())):
                return
            primeiro = False
            receita = self.sortear()
            while not self._parar.is_set():
                self._relogio.esperar_rodando(self._parar, self._config.tick)  # pausado: nada
                if self._parar.is_set():
                    return
                criar = lambda: Pedido(self._proximo_id(), receita, self._relogio.agora())  # noqa: E731
                if self._fila.colocar(criar, timeout=self._config.tick) is not None:
                    break                                   # fila cheia: tenta de novo (RF10)

    def _proximo_id(self) -> int:
        """Chamado pela fila só quando há vaga: ids sobem de 1 em 1, sem pular."""
        self._ultimo_id += 1
        return self._ultimo_id

    def _esperar(self, segundos: float) -> bool:
        """Espera `segundos` de tempo de jogo em ticks pausáveis. False se `parar`."""
        tick = self._config.tick
        feito = 0.0
        anterior = self._relogio.agora()
        while feito < segundos:
            self._relogio.esperar_rodando(self._parar, tick)
            if self._parar.wait(tick):
                return False
            agora = self._relogio.agora()
            feito += agora - anterior
            anterior = agora
        return True

    def intervalo(self, decorrido: float) -> float:
        """Linear do intervalo inicial ao mínimo ao longo da partida (RF06)."""
        c = self._config
        fracao = min(decorrido / c.duracao_partida, 1.0)
        return max(c.intervalo_minimo,
                   c.intervalo_inicial - (c.intervalo_inicial - c.intervalo_minimo) * fracao)

    def sortear(self) -> Receita:
        return self._rng.choice(self._config.receitas)
