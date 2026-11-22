"""Cozinheiros se movendo: a posição de tela anda em direção a um alvo tirado do retrato.

A lógica não tem coordenadas; toda a animação é só da tela (spec 08).
"""
from __future__ import annotations

import math

from cozinha.modelo.retrato import CozinheiroView, Retrato
from cozinha.modelo.tipos import EstadoCozinheiro
from cozinha.ui import layout
from cozinha.ui.layout import MapaEstacoes, Ponto


def alvo(c: CozinheiroView, retrato: Retrato, mapa: MapaEstacoes) -> Ponto:
    """Estação que usa, lugar na fila de espera da estação que espera, ou o descanso."""
    if c.estado is EstadoCozinheiro.ESPERANDO and c.esperando is not None:
        grupo = next((g for g in retrato.grupos if g.tipo is c.esperando), None)
        ordem = grupo.fila_espera.index(c.id) if grupo and c.id in grupo.fila_espera else 0
        return mapa.posicao_espera(c.esperando, ordem)
    if c.segurando and c.estado is not EstadoCozinheiro.LIVRE:
        tipo, indice = max(c.segurando)          # a de maior tipo: no empratar, o balcão
        return mapa.centro_de(tipo, indice)
    return layout.posicao_descanso(c.id)


def mover(atual: Ponto, destino: Ponto, velocidade: float, dt: float) -> Ponto:
    """Anda em linha reta no máximo `velocidade * dt`, sem passar do destino."""
    dx, dy = destino[0] - atual[0], destino[1] - atual[1]
    distancia = math.hypot(dx, dy)
    passo = velocidade * dt
    if distancia <= passo or distancia == 0:
        return destino
    return atual[0] + dx * passo / distancia, atual[1] + dy * passo / distancia


class Animacao:
    def __init__(self, velocidade: float = layout.VELOCIDADE) -> None:
        self._velocidade = velocidade
        self.posicoes: dict[int, Ponto] = {}

    def atualizar(self, retrato: Retrato, dt: float) -> None:
        mapa = layout.mapa_estacoes(retrato.grupos)
        for c in retrato.cozinheiros:
            atual = self.posicoes.get(c.id, layout.posicao_descanso(c.id))
            self.posicoes[c.id] = mover(atual, alvo(c, retrato, mapa), self._velocidade, dt)
