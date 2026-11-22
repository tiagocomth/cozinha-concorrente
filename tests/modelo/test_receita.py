from __future__ import annotations

import pytest

from cozinha.modelo.receita import RECEITAS, Etapa, Receita
from cozinha.modelo.tipos import TipoEstacao

TABUA, PIA, FOGAO, BALCAO = TipoEstacao


def test_ordem_das_estacoes():
    assert [t.value for t in TipoEstacao] == [1, 2, 3, 4]


def test_etapa_ordena():
    assert Etapa("empratar", (BALCAO, FOGAO), 1).estacoes == (FOGAO, BALCAO)


def test_etapa_repetida():
    with pytest.raises(ValueError):
        Etapa("x", (FOGAO, FOGAO), 1)


def test_etapa_entrega():
    assert Etapa("empratar", (FOGAO, BALCAO), 1).entrega is True
    assert Etapa("cortar", (TABUA,), 2).entrega is False


def test_balcao_fora_da_ultima():
    with pytest.raises(ValueError):
        Receita("r", (Etapa("e", (BALCAO,), 0), Etapa("c", (TABUA,), 1)), 10, 10)


def test_receitas_iniciais():
    resumo = [(r.nome, r.pontos, r.paciencia) for r in RECEITAS]
    assert resumo == [("Salada", 20, 25), ("Sopa", 35, 35), ("Prato do dia", 50, 45)]
    for r in RECEITAS:
        assert r.etapas[-1].entrega
        assert not any(e.entrega for e in r.etapas[:-1])
    sopa = RECEITAS[1]
    assert sopa.etapas[-1] == Etapa("empratar", (FOGAO, BALCAO), 1)
    prato = RECEITAS[2]
    assert [(e.nome, e.estacoes, e.duracao) for e in prato.etapas] == [
        ("lavar", (PIA,), 2), ("cortar", (TABUA,), 2),
        ("cozinhar", (FOGAO,), 5), ("empratar", (FOGAO, BALCAO), 1)]
