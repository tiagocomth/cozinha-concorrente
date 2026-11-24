from __future__ import annotations

import dataclasses

import pytest

from cozinha.config import Config
from cozinha.modelo.tipos import TipoEstacao

TABUA, PIA, FOGAO, BALCAO = TipoEstacao


def test_padrao_e_replace():
    c = Config()
    assert c.n_cozinheiros == 3
    assert dict(c.quantidade) == {TABUA: 2, PIA: 1, FOGAO: 2, BALCAO: 2}
    assert dataclasses.replace(c, n_cozinheiros=1).n_cozinheiros == 1


def test_quantidade_imutavel():
    with pytest.raises(TypeError):
        Config().quantidade[TABUA] = 3


def test_dict_recebido_vira_imutavel():
    c = Config(quantidade={TABUA: 1, PIA: 1, FOGAO: 1, BALCAO: 1})
    with pytest.raises(TypeError):
        c.quantidade[TABUA] = 3


@pytest.mark.parametrize("kwargs", [
    {"tick": 0},
    {"duracao_partida": 0},
    {"intervalo_inicial": -1},
    {"tempo_retirada": -0.1},
    {"n_cozinheiros": 0},
    {"intervalo_minimo": 9.0},
    {"quantidade": {TABUA: 0, PIA: 1, FOGAO: 1, BALCAO: 1}},
    {"quantidade": {TABUA: 1, PIA: 1, FOGAO: 1}},
])
def test_validacao_basica(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)


def test_tempo_retirada_zero_aceito():
    assert Config(tempo_retirada=0).tempo_retirada == 0


def test_validar_para_jogo():
    with pytest.raises(ValueError):
        Config(duracao_partida=60).validar_para_jogo()
    with pytest.raises(ValueError):
        Config(n_cozinheiros=5).validar_para_jogo()
    Config().validar_para_jogo()
    Config(duracao_partida=3, n_cozinheiros=1)  # testes usam isso


def test_demo_deadlock():
    c = Config.demo_deadlock()
    assert c.ordem_fixa is False
    assert c.expiracao is False
    assert c.quantidade[FOGAO] == 1
    assert c.quantidade[BALCAO] == 1
    assert c.n_cozinheiros == 2
    assert [r.nome for r in c.receitas] == ["Sopa"]
    assert c.limite_perdidos >= 1000
    # Pedidos chegando rápido: os dois cozinheiros ficam sempre ocupados e se cruzam no empratar.
    assert c.intervalo_inicial <= 2 and c.intervalo_minimo <= 2


def test_single_player():
    c = Config.single_player("Fácil")
    assert c.jogador is True
    assert c.meta_pontos == 200
    c.validar_para_jogo()
    assert Config().jogador is False
    assert Config.demo_deadlock().jogador is False


def test_atraso_automaticos():
    assert Config().atraso_automaticos == 0
    assert Config.single_player().atraso_automaticos > 0
    import pytest as _pytest
    with _pytest.raises(ValueError):
        Config(atraso_automaticos=-1)


def test_niveis():
    from cozinha.config import NIVEIS
    from cozinha.modelo.receita import RECEITAS
    assert NIVEIS == ("Fácil", "Normal", "Difícil")
    esperado = {"Fácil": (200, 1.0, 8.0, 3.0, 6.0), "Normal": (300, 0.75, 6.0, 2.0, 4.0),
                "Difícil": (400, 0.6, 5.0, 1.5, 2.0)}
    for nivel, (meta, fator, ini, mini, atraso) in esperado.items():
        c = Config.single_player(nivel)
        assert (c.meta_pontos, c.intervalo_inicial, c.intervalo_minimo, c.atraso_automaticos) == (
            meta, ini, mini, atraso)
        assert [r.paciencia for r in c.receitas] == pytest.approx(
            [r.paciencia * fator for r in RECEITAS])
        assert c.jogador and c.receitas_progressivas and c.nivel == nivel
        c.validar_para_jogo()
    assert Config.single_player().nivel == "Normal"
    assert Config().receitas_progressivas is False
    with pytest.raises(ValueError):
        Config.single_player("Impossível")
