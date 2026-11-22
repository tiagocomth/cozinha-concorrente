"""Estações da cozinha (spec 02): exclusão mútua, espera justa e ordem fixa contra deadlock."""
from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from cozinha.config import Config
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

    def _ocupada(self, reserva: Reserva) -> bool:
        """Chamado com o lock."""
        return (reserva.tipo is self.tipo
                and 0 <= reserva.indice < len(self._ocupada_por)
                and self._ocupada_por[reserva.indice] is not None)

    def esta_ocupada(self, reserva: Reserva) -> bool:
        with self._lock:
            return self._ocupada(reserva)

    def liberar(self, reserva: Reserva) -> None:
        with self._lock:
            if not self._ocupada(reserva):
                raise ValueError(f"reserva {reserva} não está ocupada neste grupo")
            self._ocupada_por[reserva.indice] = None
        self._semaforo.release()                          # só depois de marcar livre

    def views(self) -> tuple[EstacaoView, ...]:
        with self._lock:
            return tuple(EstacaoView(self.tipo, i, dono)
                         for i, dono in enumerate(self._ocupada_por))

    def view(self) -> GrupoView:
        return GrupoView(self.tipo, self._semaforo.capacidade, self._semaforo.esperando())


class Cozinha:
    """Todos os grupos. É por aqui que o cozinheiro pega e solta estações."""

    def __init__(self, config: Config) -> None:
        self._ordem_fixa = config.ordem_fixa
        self._grupos = {tipo: GrupoDeEstacoes(tipo, config.quantidade[tipo], config.tick)
                        for tipo in TipoEstacao}

    def ocupar_todas(self, dono: int, tipos: tuple[TipoEstacao, ...],
                     cancelar: Callable[[], bool],
                     ao_mudar: AoMudar = lambda s, e: None) -> tuple[Reserva, ...] | None:
        """Pega um tipo por vez, em ordem crescente (RC04). None se cancelado no meio.

        Quem segura Y > X nunca espera X, então não há ciclo de espera: sem deadlock.
        """
        if self._ordem_fixa and list(tipos) != sorted(tipos):
            raise ValueError(f"tipos fora da ordem fixa: {tipos}")
        ordem = tipos
        if not self._ordem_fixa and dono % 2 == 0:
            # Só na demonstração (spec 09): os pares pegam ao contrário e a cozinha trava.
            ordem = tuple(reversed(tipos))
        segurando: tuple[Reserva, ...] = ()
        try:
            for tipo in ordem:
                ao_mudar(segurando, tipo)                   # já segura X e espera este
                reserva = self._grupos[tipo].ocupar(dono, cancelar)
                if reserva is None:
                    self.liberar(segurando)
                    segurando = ()
                    ao_mudar((), None)
                    return None
                segurando += (reserva,)
                ao_mudar(segurando, None)
        except BaseException:
            self.liberar(segurando)                         # nunca deixa estação presa
            raise
        return segurando

    def liberar(self, reservas: Iterable[Reserva]) -> None:
        """Solta na ordem inversa da aquisição. Aceita só uma parte das reservas."""
        reservas = tuple(reservas)
        if len(set(reservas)) != len(reservas):
            raise ValueError(f"reserva repetida: {reservas}")
        for r in reservas:                                  # valida tudo antes de soltar
            grupo = self._grupos.get(r.tipo)
            if grupo is None or not grupo.esta_ocupada(r):
                raise ValueError(f"reserva {r} não está ocupada")
        for r in reversed(reservas):
            self._grupos[r.tipo].liberar(r)

    def views(self) -> tuple[tuple[EstacaoView, ...], tuple[GrupoView, ...]]:
        """Estações e grupos em ordem de TipoEstacao, cada grupo copiado sob o próprio lock."""
        estacoes = tuple(e for g in self._grupos.values() for e in g.views())
        grupos = tuple(g.view() for g in self._grupos.values())
        return estacoes, grupos
