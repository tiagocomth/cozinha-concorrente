from __future__ import annotations

import itertools
import math

import pygame
import pytest

from cozinha.config import Config
from cozinha.modelo.retrato import GrupoView
from cozinha.modelo.tipos import TipoEstacao
from cozinha.ui import layout
from cozinha.ui.avatar import Avatar

TABUA, PIA, FOGAO, BALCAO = TipoEstacao


def _mapa(config: Config = Config()) -> layout.MapaEstacoes:
    return layout.mapa_estacoes(tuple(GrupoView(t, config.quantidade[t], ()) for t in TipoEstacao))


MAPA = _mapa()


def _circulo_toca(pos, r: pygame.Rect) -> bool:
    x = min(max(pos[0], r.left), r.right)
    y = min(max(pos[1], r.top), r.bottom)
    return math.hypot(pos[0] - x, pos[1] - y) < layout.COZINHEIRO_RAIO - 0.01


def test_anda():
    a = Avatar(layout.INICIO_JOGADOR)
    x0 = a.pos[0]
    a.andar((1, 0), 0.5, MAPA)
    assert a.pos[0] == pytest.approx(x0 + layout.VELOCIDADE_JOGADOR * 0.5)


def test_diagonal_normalizada():
    a = Avatar(layout.INICIO_JOGADOR)
    x0, y0 = a.pos
    a.andar((1, 1), 0.1, MAPA)
    assert math.hypot(a.pos[0] - x0, a.pos[1] - y0) == pytest.approx(layout.VELOCIDADE_JOGADOR * 0.1)


def test_parado():
    a = Avatar(layout.INICIO_JOGADOR)
    a.andar((0, 0), 1.0, MAPA)
    assert a.pos == layout.INICIO_JOGADOR


def test_nao_sai_do_piso():
    a = Avatar(layout.INICIO_JOGADOR)
    for direcao in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for _ in range(200):
            a.andar(direcao, 0.05, MAPA)
        assert layout.PISO.inflate(1, 1).collidepoint(a.pos)


def test_nao_atravessa_estacao():
    fogao = MAPA.estacao(FOGAO, 0)
    a = Avatar((fogao.centerx, fogao.bottom + 100))
    for _ in range(100):
        a.andar((0, -1), 0.02, MAPA)
        assert not any(_circulo_toca(a.pos, r) for r in MAPA.obstaculos)
    assert a.pos[1] < fogao.bottom + layout.COZINHEIRO_RAIO + 2     # chegou encostado


def test_desliza_na_parede():
    a = Avatar((MAPA.estacao(TABUA, 0).centerx, MAPA.estacao(TABUA, 0).bottom + layout.COZINHEIRO_RAIO))
    x0 = a.pos[0]
    a.andar((1, -1), 0.1, MAPA)
    assert a.pos[0] > x0                       # o eixo livre continua andando


def test_perto():
    a = Avatar(MAPA.areas_interacao[TABUA][0].center)
    assert a.perto(MAPA) is TABUA
    a = Avatar(MAPA.areas_interacao["quadro"][0].center)
    assert a.perto(MAPA) == "quadro"
    a = Avatar(MAPA.areas_interacao[BALCAO][0].center)
    assert a.perto(MAPA) is BALCAO
    a = Avatar(layout.INICIO_JOGADOR)
    assert a.perto(MAPA) is None


@pytest.mark.parametrize("config", [Config(), Config.demo_deadlock()])
def test_mapa_cabe(config):
    mapa = _mapa(config)
    for r in mapa.obstaculos:
        assert layout.PISO.contains(r)
    for a, b in itertools.combinations(mapa.obstaculos, 2):
        assert not a.colliderect(b)
    for areas in mapa.areas_interacao.values():
        for area in areas:
            assert layout.PISO.collidepoint(area.center)
            assert not any(r.collidepoint(area.center) for r in mapa.obstaculos)
    assert layout.PISO.collidepoint(layout.INICIO_JOGADOR)
    assert not any(_circulo_toca(layout.INICIO_JOGADOR, r) for r in mapa.obstaculos)
