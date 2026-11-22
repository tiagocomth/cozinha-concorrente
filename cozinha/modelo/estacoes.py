"""Estações da cozinha (spec 02): exclusão mútua, espera justa e ordem fixa contra deadlock."""
from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass

from cozinha.modelo.retrato import EstacaoView, GrupoView
from cozinha.modelo.tipos import TipoEstacao
from cozinha.sync import SemaforoJusto


@dataclass(frozen=True)
class Reserva:
    tipo: TipoEstacao
    indice: int


AoMudar = Callable[[tuple[Reserva, ...], TipoEstacao | None], None]   # (segurando, esperando)


class GrupoDeEstacoes:
    """Todas as estações de um tipo (ex.: os 2 fogões, ou as vagas do balcão)."""

    def __init__(self, tipo: TipoEstacao, quantidade: int, fatia: float) -> None:
        self.tipo = tipo
        self._fatia = fatia
        self._semaforo = SemaforoJusto(quantidade)       # quantos podem estar dentro
        self._lock = threading.Lock()                     # curto: só para escolher/marcar
        self._ocupada_por: list[int | None] = [None] * quantidade

    def ocupar(self, dono: int, cancelar: Callable[[], bool]) -> Reserva | None:
        """Espera a vez sem sair da fila. None se `cancelar()` ficar verdadeiro."""
        if not self._semaforo.acquire(dono, cancelar=cancelar, fatia=self._fatia):
            return None
        with self._lock:
            # O semáforo garante vaga: sempre há uma livre.
            indice = self._ocupada_por.index(None)
            self._ocupada_por[indice] = dono
        return Reserva(self.tipo, indice)

    def liberar(self, reserva: Reserva) -> None:
        with self._lock:
            if (reserva.tipo is not self.tipo
                    or not 0 <= reserva.indice < len(self._ocupada_por)
                    or self._ocupada_por[reserva.indice] is None):
                raise ValueError(f"reserva {reserva} não está ocupada neste grupo")
            self._ocupada_por[reserva.indice] = None
        self._semaforo.release()                          # só depois de marcar livre

    def views(self) -> tuple[EstacaoView, ...]:
        with self._lock:
            return tuple(EstacaoView(self.tipo, i, dono)
                         for i, dono in enumerate(self._ocupada_por))

    def view(self) -> GrupoView:
        return GrupoView(self.tipo, self._semaforo.capacidade, self._semaforo.esperando())
