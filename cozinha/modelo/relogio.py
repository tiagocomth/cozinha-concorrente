"""Tempo de jogo: para na pausa e congela no fim (spec 06)."""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import fields

from cozinha.config import Config

# Mesmo valor do Config().tick, sem número mágico duplicado.
TICK_PADRAO: float = next(f.default for f in fields(Config) if f.name == "tick")


class Relogio:
    def __init__(self, fonte: Callable[[], float] = time.monotonic) -> None:
        self._fonte = fonte
        self._lock = threading.Lock()
        self._inicio: float | None = None
        self._total_pausado = 0.0
        self._pausado_em: float | None = None
        self._congelado_em: float | None = None   # agora() fixado no fim
        self.rodando = threading.Event()          # setado quando o tempo anda

    def iniciar(self) -> None:
        with self._lock:
            if self._inicio is not None:
                return
            self._inicio = self._fonte()
            self.rodando.set()

    def agora(self) -> float:
        """Segundos de jogo; 0 antes de iniciar."""
        with self._lock:
            return self._agora_sem_lock()

    def _agora_sem_lock(self) -> float:
        if self._congelado_em is not None:
            return self._congelado_em
        if self._inicio is None:
            return 0.0
        referencia = self._pausado_em if self._pausado_em is not None else self._fonte()
        return referencia - self._inicio - self._total_pausado

    def pausar(self) -> None:
        with self._lock:
            if self._inicio is None or self._congelado_em is not None or self._pausado_em is not None:
                return
            self._pausado_em = self._fonte()
            self.rodando.clear()

    def retomar(self) -> None:
        with self._lock:
            if self._pausado_em is None or self._congelado_em is not None:
                return
            self._total_pausado += self._fonte() - self._pausado_em
            self._pausado_em = None
            self.rodando.set()

    def congelar(self) -> None:
        """Fim da partida: agora() para de andar para sempre."""
        with self._lock:
            if self._congelado_em is not None:
                return
            self._congelado_em = self._agora_sem_lock()
            self._pausado_em = None
            self.rodando.set()   # ninguém fica preso na pausa depois do fim

    @property
    def pausado(self) -> bool:
        with self._lock:
            return self._pausado_em is not None

    def esperar_rodando(self, parar: threading.Event, fatia: float = TICK_PADRAO) -> None:
        """Bloqueia enquanto pausado, acordando a cada `fatia` para olhar `parar`.

        `fatia` padrão é o `Config().tick`; quem tem a config passa `config.tick`.
        """
        while not parar.is_set() and not self.rodando.wait(fatia):
            pass
