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


from dataclasses import replace  # noqa: E402

from cozinha.config import Config  # noqa: E402
from cozinha.modelo.receita import Etapa, Receita  # noqa: E402
from cozinha.modelo.tipos import TipoEstacao  # noqa: E402

TABUA, PIA, FOGAO, BALCAO = TipoEstacao


def receitas_teste(dur: float = 0.01, paciencia: float = 2.0) -> tuple[Receita, ...]:
    return (
        Receita("Salada", (Etapa("cortar", (TABUA,), dur), Etapa("entregar", (BALCAO,), dur)),
                20, paciencia),
        Receita("Sopa", (Etapa("cortar", (TABUA,), dur), Etapa("cozinhar", (FOGAO,), dur),
                         Etapa("empratar", (FOGAO, BALCAO), dur)), 35, paciencia),
    )


def config_rapida(**kw) -> Config:
    base = dict(duracao_partida=3, n_cozinheiros=2, tick=0.005, tempo_retirada=0,
                intervalo_inicial=0.1, intervalo_minimo=0.05, semente=1,
                receitas=receitas_teste())
    return replace(Config(), **{**base, **kw})


def tecla(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0)
