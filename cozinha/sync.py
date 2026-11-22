"""Semáforo justo: atende na ordem de chegada (spec 01, RC05).

O threading.Semaphore do Python não garante ordem: uma thread pode perder a vez
para sempre. Aqui cada acquire pega uma senha e só passa quando é a primeira da
fila e há vaga. A espera acontece em fatias curtas SEM sair da fila.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(eq=False)          # identidade: o mesmo dono pode ter duas senhas
class _Senha:
    dono: int


class SemaforoJusto:
    def __init__(self, valor: int) -> None:
        if valor < 1:
            raise ValueError("valor precisa ser >= 1")
        self._capacidade = valor
        self._valor = valor
        self._fila: deque[_Senha] = deque()
        self._cond = threading.Condition()

    def acquire(self, dono: int, timeout: float | None = None,
                cancelar: Callable[[], bool] | None = None,
                fatia: float = 0.05) -> bool:
        """Entra no fim da fila e espera a vez. False se `timeout` acabar ou `cancelar()`."""
        limite = None if timeout is None else time.monotonic() + timeout
        with self._cond:
            senha = _Senha(dono)
            self._fila.append(senha)
            while not (self._fila[0] is senha and self._valor > 0):
                restante = None if limite is None else limite - time.monotonic()
                if (restante is not None and restante <= 0) or (cancelar and cancelar()):
                    self._fila.remove(senha)          # por identidade
                    self._cond.notify_all()           # quem estava atrás pode passar agora
                    return False
                self._cond.wait(fatia if restante is None else min(fatia, restante))
            self._fila.popleft()
            self._valor -= 1
            self._cond.notify_all()                   # a próxima pode passar se ainda houver vaga
            return True

    def release(self) -> None:
        with self._cond:
            if self._valor >= self._capacidade:
                raise ValueError("release sem acquire correspondente")
            self._valor += 1
            self._cond.notify_all()

    @property
    def disponivel(self) -> int:
        with self._cond:
            return self._valor

    @property
    def capacidade(self) -> int:
        return self._capacidade

    def esperando(self) -> tuple[int, ...]:
        """Donos na fila, na ordem de chegada."""
        with self._cond:
            return tuple(s.dono for s in self._fila)
