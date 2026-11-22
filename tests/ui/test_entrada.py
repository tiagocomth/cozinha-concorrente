from __future__ import annotations

from dataclasses import replace

import pygame

from cozinha.modelo.retrato import Retrato
from cozinha.ui import layout
from cozinha.ui.entrada import (AlternarDebug, AlternarPausa, Atribuir, Confirmar, PedirSaida,
                                Selecionar, traduzir)

from .conftest import tecla

R = Retrato.exemplo()                       # pedidos 1..6
CARTOES = layout.cartoes_pedidos(R.pedidos, R.tamanho_max_fila)


def _t(key: int, cursor: int | None = None, retrato: Retrato = R):
    return traduzir(tecla(key), retrato, cursor, CARTOES)


def _clique(pos: tuple[int, int], botao: int = 1):
    e = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=botao)
    return traduzir(e, R, None, CARTOES)


def test_teclas():
    for n in range(1, 5):
        assert _t(getattr(pygame, f"K_{n}")) == (Selecionar(n), None)
    assert _t(pygame.K_p) == (AlternarPausa(), None)
    assert _t(pygame.K_d) == (AlternarDebug(), None)
    assert _t(pygame.K_ESCAPE) == (PedirSaida(), None)
    assert _t(pygame.K_z, cursor=3) == (None, 3)


def test_clique():
    assert _clique(CARTOES[6].center) == (Atribuir(6), None)
    assert _clique((5, 700)) == (None, None)
    assert _clique(CARTOES[6].center, botao=3) == (None, None)


def test_cursor_setas():
    assert _t(pygame.K_RIGHT) == (None, 1)
    assert _t(pygame.K_RIGHT, cursor=1) == (None, 2)
    assert _t(pygame.K_LEFT, cursor=2) == (None, 1)
    assert _t(pygame.K_LEFT, cursor=1) == (None, 1)
    assert _t(pygame.K_RIGHT, cursor=6) == (None, 6)


def test_enter_atribui():
    assert _t(pygame.K_RETURN, cursor=5) == (Atribuir(5), 5)
    assert _t(pygame.K_KP_ENTER, cursor=5) == (Atribuir(5), 5)
    assert _t(pygame.K_RETURN) == (Confirmar(), None)


def test_cursor_some():
    sem_9 = replace(R, pedidos=tuple(p for p in R.pedidos if p.id != 4))
    acao, cursor = _t(pygame.K_RIGHT, cursor=4, retrato=sem_9)
    assert acao is None and cursor in {p.id for p in sem_9.pedidos}
    acao, cursor = _t(pygame.K_RIGHT, cursor=9)
    assert cursor in {p.id for p in R.pedidos}
    vazio = replace(R, pedidos=())
    assert _t(pygame.K_RIGHT, cursor=3, retrato=vazio) == (None, None)
    assert _t(pygame.K_RETURN, cursor=3, retrato=vazio) == (Confirmar(), None)
