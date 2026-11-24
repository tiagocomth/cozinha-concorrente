from __future__ import annotations

from dataclasses import replace

from cozinha.modelo.retrato import Retrato
from cozinha.modelo.tipos import EstadoPedido, TipoEstacao
from cozinha.ui import layout
from cozinha.ui.efeitos import Efeitos

R0 = Retrato.exemplo()
MAPA = layout.mapa_estacoes(R0.grupos)


def test_primeiro_retrato_nao_gera():
    e = Efeitos()
    e.observar(None, R0, MAPA)
    assert e.ativos == []


def test_entrega_gera_mais():
    e = Efeitos()
    r1 = replace(R0, pontos=R0.pontos + 35, entregues=R0.entregues + 1)
    e.observar(R0, r1, MAPA)
    (ef,) = e.ativos
    assert ef.texto == "+35"
    balcao = MAPA.estacao(TipoEstacao.BALCAO, 0)
    assert abs(ef.pos[0] - balcao.centerx) < 120
    assert e.pulso_pontos == 1.0


def test_duas_entregas_um_efeito():
    e = Efeitos()
    r1 = replace(R0, pontos=R0.pontos + 55, entregues=R0.entregues + 2)
    e.observar(R0, r1, MAPA)
    assert [x.texto for x in e.ativos] == ["+55"]


def test_perda_gera_x():
    e = Efeitos()
    sem_5 = tuple(p for p in R0.pedidos if p.id != 5)        # #5 estava AGUARDANDO
    r1 = replace(R0, pedidos=sem_5, perdidos=R0.perdidos + 1)
    e.observar(R0, r1, MAPA)
    (ef,) = e.ativos
    assert ef.texto == "✗" or ef.texto == "X"
    cartao = layout.cartoes_pedidos(R0.pedidos, R0.tamanho_max_fila)[5]
    assert cartao.collidepoint(ef.pos)


def test_efeitos_somem_e_sobem():
    e = Efeitos()
    e.observar(R0, replace(R0, pontos=R0.pontos + 20, entregues=R0.entregues + 1), MAPA)
    y0 = e.ativos[0].pos[1]
    e.atualizar(0.3)
    assert e.ativos[0].pos[1] < y0
    assert e.pulso_pontos < 1.0
    e.atualizar(5.0)
    assert e.ativos == []
    assert e.pulso_pontos == 0.0
