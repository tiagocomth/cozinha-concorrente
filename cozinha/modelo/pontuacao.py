"""Placar protegido contra corrida (spec 06, RC03).

É a única que marca os estados finais do pedido (ENTREGUE / PERDIDO).
"""
from __future__ import annotations

import threading

from cozinha.config import Config
from cozinha.modelo.pedido import Pedido
from cozinha.modelo.tipos import EstadoPedido


class Pontuacao:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._mutex = threading.Semaphore(1)   # semáforo binário (RC03)
        self._pontos = 0
        self._entregues = 0
        self._perdidos = 0
        self._registrados: set[int] = set()
        self._fechada = False

    def registrar_entrega(self, pedido: Pedido, agora: float) -> int:
        """Marca ENTREGUE e soma os pontos (RF14). Devolve os pontos ganhos."""
        with self._mutex:
            if not self._marcar(pedido, EstadoPedido.ENTREGUE):
                return 0
            ganhos = pedido.receita.pontos + round(
                self._config.bonus_maximo * pedido.paciencia_restante(agora))
            self._pontos += ganhos
            self._entregues += 1
            return ganhos

    def registrar_perda(self, pedido: Pedido) -> None:
        with self._mutex:
            if self._marcar(pedido, EstadoPedido.PERDIDO):
                self._perdidos += 1

    def _marcar(self, pedido: Pedido, estado: EstadoPedido) -> bool:
        """Chamado com o mutex. False se fechada; ValueError se já registrado."""
        if self._fechada:
            return False
        if pedido.id in self._registrados:
            raise ValueError(f"pedido {pedido.id} registrado duas vezes")
        self._registrados.add(pedido.id)
        pedido.estado = estado
        return True

    def fechar(self) -> None:
        """Fim da partida: registros seguintes são ignorados."""
        with self._mutex:
            self._fechada = True

    def valores(self) -> tuple[int, int, int]:
        """(pontos, entregues, perdidos)."""
        with self._mutex:
            return self._pontos, self._entregues, self._perdidos
