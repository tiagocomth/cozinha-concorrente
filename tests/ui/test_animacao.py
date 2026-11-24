from __future__ import annotations

from dataclasses import replace

from cozinha.modelo.retrato import CozinheiroView, Retrato
from cozinha.modelo.tipos import EstadoCozinheiro, TipoEstacao
from cozinha.ui import layout
from cozinha.ui.animacao import Animacao, alvo, mover

TABUA, PIA, FOGAO, BALCAO = TipoEstacao
R = Retrato.exemplo()
MAPA = layout.mapa_estacoes(R.grupos)


def _c(cid: int) -> CozinheiroView:
    return next(c for c in R.cozinheiros if c.id == cid)


def test_alvo_livre():
    assert alvo(_c(5), R, MAPA) == layout.posicao_descanso(5)


def test_alvo_trabalhando():
    assert alvo(_c(1), R, MAPA) == MAPA.centro_de(TABUA, 0)
    # C2 empratando segura FOGÃO 1 e a vaga 0 do balcão: vai para a de maior tipo.
    assert alvo(_c(2), R, MAPA) == MAPA.centro_de(BALCAO, 0)


def test_alvo_esperando():
    assert alvo(_c(4), R, MAPA) == MAPA.posicao_espera(BALCAO, 0)


def test_alvo_estado_desalinhado():
    sem_estacao = replace(_c(1), estado=EstadoCozinheiro.TRABALHANDO, segurando=())
    assert alvo(sem_estacao, R, MAPA) == layout.posicao_descanso(1)
    esperando_nada = replace(_c(4), esperando=None)
    assert alvo(esperando_nada, R, MAPA) == MAPA.centro_de(FOGAO, 0)


def test_mover_velocidade():
    assert mover((0, 0), (100, 0), 50, 1) == (50, 0)


def test_mover_nao_passa():
    assert mover((0, 0), (100, 0), 500, 2) == (100, 0)


def test_animacao_chega():
    a = Animacao()
    a.atualizar(R, 0.0)
    assert a.posicoes[1] == layout.posicao_descanso(1)     # nasce no descanso
    for _ in range(200):
        a.atualizar(R, 1 / 60)
    for c in R.cozinheiros:
        assert a.posicoes[c.id] == alvo(c, R, MAPA)
