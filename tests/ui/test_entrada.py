from __future__ import annotations

import pygame
import pytest

from cozinha.modelo.retrato import Retrato
from cozinha.ui import layout
from cozinha.ui.entrada import (AlternarDebug, AlternarPausa, ClicarComanda, Confirmar, Desistir,
                                Interagir, PedirSaida, direcao, traduzir)

from .conftest import tecla

R = Retrato.exemplo()
CARTOES = layout.cartoes_pedidos(R.pedidos, R.tamanho_max_fila)


class Teclas:
    def __init__(self, *apertadas: int) -> None:
        self.apertadas = set(apertadas)

    def __getitem__(self, k: int) -> bool:
        return k in self.apertadas


def _clique(pos, botao: int = 1):
    return traduzir(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=botao), CARTOES)


def test_traduzir_teclas():
    assert traduzir(tecla(pygame.K_e), CARTOES) == Interagir()
    assert traduzir(tecla(pygame.K_SPACE), CARTOES) == Interagir()
    assert traduzir(tecla(pygame.K_q), CARTOES) == Desistir()
    assert traduzir(tecla(pygame.K_p), CARTOES) == AlternarPausa()
    assert traduzir(tecla(pygame.K_d), CARTOES) == AlternarDebug()
    assert traduzir(tecla(pygame.K_ESCAPE), CARTOES) == PedirSaida()
    assert traduzir(tecla(pygame.K_RETURN), CARTOES) == Confirmar()
    assert traduzir(tecla(pygame.K_z), CARTOES) is None


def test_traduzir_clique():
    assert _clique(CARTOES[6].center) == ClicarComanda(6)
    assert _clique((5, 700)) is None
    assert _clique(CARTOES[6].center, botao=3) is None


@pytest.mark.parametrize("teclas,esperado", [
    ((), (0, 0)),
    ((pygame.K_d,), (1, 0)),
    ((pygame.K_RIGHT,), (1, 0)),
    ((pygame.K_a,), (-1, 0)),
    ((pygame.K_LEFT,), (-1, 0)),
    ((pygame.K_w,), (0, -1)),
    ((pygame.K_UP,), (0, -1)),
    ((pygame.K_s,), (0, 1)),
    ((pygame.K_DOWN,), (0, 1)),
    ((pygame.K_w, pygame.K_d), (1, -1)),
    ((pygame.K_a, pygame.K_d), (0, 0)),
])
def test_direcao(teclas, esperado):
    assert direcao(Teclas(*teclas)) == esperado
