"""Teclas e mouse → ações (spec 09). Função pura: testável sem janela.

A TelaJogo executa a ação no Jogo e cuida da caixa de confirmação de saída.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pygame

from cozinha.modelo.retrato import Retrato
from cozinha.modelo.tipos import EstadoPedido


@dataclass(frozen=True)
class Selecionar:
    cozinheiro_id: int


@dataclass(frozen=True)
class Atribuir:
    pedido_id: int


@dataclass(frozen=True)
class AlternarPausa:
    pass


@dataclass(frozen=True)
class AlternarDebug:
    pass


@dataclass(frozen=True)
class PedirSaida:
    pass


@dataclass(frozen=True)
class Confirmar:
    """Enter sem pedido no cursor (ex.: confirmar a saída da partida)."""


Acao = Selecionar | Atribuir | AlternarPausa | AlternarDebug | PedirSaida | Confirmar

TECLAS_COZINHEIRO = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3, pygame.K_4: 4}
ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER)
BOTAO_ESQUERDO = 1


def _ajustar(cursor: int | None, ids: list[int]) -> int | None:
    """O cursor é um pedido_id: se o pedido sumiu, vai para o mais próximo (ou None)."""
    if not ids:
        return None
    if cursor is None or cursor in ids:
        return cursor
    return min(ids, key=lambda i: (abs(i - cursor), i))


def traduzir(e: pygame.event.Event, retrato: Retrato, cursor: int | None,
             cartoes: Mapping[int, pygame.Rect]) -> tuple[Acao | None, int | None]:
    """Devolve (ação, novo cursor)."""
    if e.type == pygame.MOUSEBUTTONDOWN:
        if e.button == BOTAO_ESQUERDO:
            for pedido_id, rect in cartoes.items():
                if rect.collidepoint(e.pos):
                    return Atribuir(pedido_id), cursor
        return None, cursor
    if e.type != pygame.KEYDOWN:
        return None, cursor
    if e.key in TECLAS_COZINHEIRO:
        return Selecionar(TECLAS_COZINHEIRO[e.key]), cursor
    if e.key == pygame.K_p:
        return AlternarPausa(), cursor
    if e.key == pygame.K_d:
        return AlternarDebug(), cursor
    if e.key == pygame.K_ESCAPE:
        return PedirSaida(), cursor
    # Só os pedidos da fila podem receber ordem: o cursor anda por eles, na ordem da tela.
    ids = [p.id for p in retrato.pedidos if p.estado is EstadoPedido.AGUARDANDO]
    if e.key in (pygame.K_LEFT, pygame.K_RIGHT):
        atual = _ajustar(cursor, ids)
        if atual is None:
            return None, (ids[0] if ids else None)
        passo = 1 if e.key == pygame.K_RIGHT else -1
        i = min(max(ids.index(atual) + passo, 0), len(ids) - 1)
        return None, ids[i]
    if e.key in ENTER:
        if cursor is not None and cursor in ids:
            return Atribuir(cursor), cursor
        return Confirmar(), _ajustar(cursor, ids)
    return None, cursor
