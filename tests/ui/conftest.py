"""Testes de interface sem janela: driver de vídeo "dummy" antes de importar o pygame."""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from cozinha.ui import layout  # noqa: E402


@pytest.fixture
def tela():
    pygame.init()
    superficie = pygame.display.set_mode(layout.JANELA)
    yield superficie
    pygame.quit()
