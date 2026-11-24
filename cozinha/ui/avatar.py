"""O cozinheiro do jogador na tela: anda com o teclado e colide com os móveis.

Posição e colisão são só da tela; a lógica não tem coordenadas (spec 00).
"""
from __future__ import annotations

import math

import pygame

from cozinha.ui import layout
from cozinha.ui.layout import Alvo, MapaEstacoes, Ponto

R = layout.COZINHEIRO_RAIO


def _bate(x: float, y: float, r: pygame.Rect) -> bool:
    """O quadrado de lado 2R em volta de (x, y) invade o retângulo? (encostar não conta)"""
    return x + R > r.left and x - R < r.right and y + R > r.top and y - R < r.bottom


class Avatar:
    def __init__(self, pos: Ponto) -> None:
        self.pos: Ponto = (float(pos[0]), float(pos[1]))

    def andar(self, direcao: tuple[float, float], dt: float, mapa: MapaEstacoes) -> None:
        """Anda à velocidade fixa (diagonal normalizada), preso ao piso, eixo a eixo:
        bater num móvel num eixo não impede de deslizar no outro."""
        dx, dy = direcao
        norma = math.hypot(dx, dy)
        if norma == 0:
            return
        passo = layout.VELOCIDADE_JOGADOR * dt / norma
        x, y = self.pos
        piso = layout.PISO
        nx = min(max(x + dx * passo, piso.left + R), piso.right - R)
        for r in mapa.obstaculos:
            if _bate(nx, y, r):
                nx = r.left - R if dx > 0 else r.right + R
        ny = min(max(y + dy * passo, piso.top + R), piso.bottom - R)
        for r in mapa.obstaculos:
            if _bate(nx, ny, r):
                ny = r.top - R if dy > 0 else r.bottom + R
        self.pos = (nx, ny)

    def perto(self, mapa: MapaEstacoes) -> Alvo | None:
        """A estação (ou o quadro) em cuja área de interação o avatar está; a mais próxima."""
        candidatos = [(math.dist(self.pos, area.center), alvo)
                      for alvo, areas in mapa.areas_interacao.items()
                      for area in areas if area.collidepoint(self.pos)]
        return min(candidatos, key=lambda c: c[0])[1] if candidatos else None
