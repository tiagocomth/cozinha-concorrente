"""Thread produtora (spec 05): cria clientes em intervalos cada vez menores."""
from __future__ import annotations

import logging
import random
import threading
from threading import Event

from cozinha.config import Config
from cozinha.modelo.fila import FilaDePedidos
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

    def intervalo(self, decorrido: float) -> float:
        """Linear do intervalo inicial ao mínimo ao longo da partida (RF06)."""
        c = self._config
        fracao = min(decorrido / c.duracao_partida, 1.0)
        return max(c.intervalo_minimo,
                   c.intervalo_inicial - (c.intervalo_inicial - c.intervalo_minimo) * fracao)

    def sortear(self) -> Receita:
        return self._rng.choice(self._config.receitas)
