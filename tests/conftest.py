"""Fixtures compartilhadas pelos testes."""
from __future__ import annotations

import pytest


class FonteFalsa:
    """Fonte de tempo controlada na mão: passe para Relogio(fonte) e chame avancar()."""

    def __init__(self, inicio: float = 1000.0) -> None:
        self.t = inicio

    def __call__(self) -> float:
        return self.t

    def avancar(self, segundos: float) -> None:
        self.t += segundos


@pytest.fixture
def fonte_falsa() -> FonteFalsa:
    return FonteFalsa()
