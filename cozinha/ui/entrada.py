"""Teclas e mouse → ações (specs 09 e single player). Funções puras: testáveis sem janela.

O movimento não é evento: a TelaJogo lê as teclas seguradas a cada quadro (`direcao`).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import pygame


@dataclass(frozen=True)
class Interagir:
    """E / Espaço: no quadro pega pedido; na estação certa, faz a etapa."""


@dataclass(frozen=True)
class Desistir:
    """Q: sai da fila de uma estação, ou descarta o pedido na mão."""


@dataclass(frozen=True)
class ClicarComanda:
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
    """Enter (ex.: confirmar a saída da partida)."""


Acao = Interagir | Desistir | ClicarComanda | AlternarPausa | AlternarDebug | PedirSaida | Confirmar

TECLAS = {pygame.K_e: Interagir(), pygame.K_SPACE: Interagir(), pygame.K_q: Desistir(),
          pygame.K_p: AlternarPausa(), pygame.K_d: AlternarDebug(),
          pygame.K_ESCAPE: PedirSaida(), pygame.K_RETURN: Confirmar(),
          pygame.K_KP_ENTER: Confirmar()}
BOTAO_ESQUERDO = 1


class Teclado(Protocol):
    def __getitem__(self, tecla: int) -> bool: ...


def traduzir(e: pygame.event.Event, cartoes: Mapping[int, pygame.Rect]) -> Acao | None:
    if e.type == pygame.MOUSEBUTTONDOWN:
        if e.button == BOTAO_ESQUERDO:
            for pedido_id, rect in cartoes.items():
                if rect.collidepoint(e.pos):
                    return ClicarComanda(pedido_id)
        return None
    if e.type == pygame.KEYDOWN:
        return TECLAS.get(e.key)
    return None


def direcao(teclas: Teclado) -> tuple[int, int]:
    """WASD ou setas → (dx, dy) em {-1, 0, 1}. O Avatar normaliza a diagonal."""
    dx = (teclas[pygame.K_d] or teclas[pygame.K_RIGHT]) - (teclas[pygame.K_a] or teclas[pygame.K_LEFT])
    dy = (teclas[pygame.K_s] or teclas[pygame.K_DOWN]) - (teclas[pygame.K_w] or teclas[pygame.K_UP])
    return int(dx), int(dy)
