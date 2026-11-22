from __future__ import annotations

import dataclasses

import pytest

from cozinha.modelo.retrato import Retrato
from cozinha.modelo.tipos import EstadoCozinheiro, TipoEstacao


@pytest.fixture
def r() -> Retrato:
    return Retrato.exemplo()


def test_exemplo_estados(r):
    assert {c.estado for c in r.cozinheiros} == set(EstadoCozinheiro)


def test_exemplo_coerente(r):
    ids = [p.id for p in r.pedidos]
    assert ids == sorted(set(ids))
    por_id = {c.id: c for c in r.cozinheiros}
    for c in r.cozinheiros:
        if c.pedido_id is not None:
            assert c.pedido_id in ids
        if c.estado is EstadoCozinheiro.LIVRE:
            assert c.pedido_id is None and not c.segurando and c.esperando is None
    for e in r.estacoes:
        if e.ocupada_por is not None:
            assert (e.tipo, e.indice) in por_id[e.ocupada_por].segurando
    for c in r.cozinheiros:
        for tipo, indice in c.segurando:
            assert any(e.tipo == tipo and e.indice == indice and e.ocupada_por == c.id
                       for e in r.estacoes)
    for g in r.grupos:
        assert sorted(e.indice for e in r.estacoes if e.tipo == g.tipo) == list(range(g.capacidade))
        for cid in g.fila_espera:
            assert por_id[cid].estado is EstadoCozinheiro.ESPERANDO
            assert por_id[cid].esperando == g.tipo
    if r.selecionado is not None:
        assert r.selecionado in por_id


def test_exemplo_casos_visuais(r):
    assert any(c.segurando == ((TipoEstacao.FOGAO, 0),) and c.esperando is TipoEstacao.BALCAO
               for c in r.cozinheiros)
    assert any(p.reservado_para is not None for p in r.pedidos)
    assert all(0 <= p.paciencia <= 1 for p in r.pedidos)
    assert all(0 <= c.progresso <= 1 for c in r.cozinheiros)
    assert r.tempo_restante >= 0


def test_imutavel(r):
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.pontos = 1
