from __future__ import annotations

import time
from dataclasses import replace

import pytest

from cozinha.config import Config
from cozinha.jogo import Jogo
from cozinha.modelo.receita import Etapa, Receita
from cozinha.modelo.tipos import TipoEstacao

FOGAO, BALCAO = TipoEstacao.FOGAO, TipoEstacao.BALCAO


def _travado(jogo: Jogo) -> bool:
    c1, c2 = jogo.retrato().cozinheiros
    return (c1.segurando == ((FOGAO, 0),) and c1.esperando is BALCAO
            and c2.segurando == ((BALCAO, 0),) and c2.esperando is FOGAO)


def _rodar_ate(jogo: Jogo, cond, prazo: float) -> bool:
    fim = time.monotonic() + prazo
    while time.monotonic() < fim:
        jogo.atualizar()
        if cond():
            return True
        time.sleep(0.01)
    return False


@pytest.mark.demo
def test_deadlock_aparece_no_retrato():
    jogo = Jogo(replace(Config.demo_deadlock(), tick=0.005))
    jogo.iniciar()
    try:
        assert _rodar_ate(jogo, lambda: _travado(jogo), prazo=30), "a cozinha não travou"
        assert not _rodar_ate(jogo, lambda: not _travado(jogo), prazo=2), "a trava se desfez"
    finally:
        assert jogo.encerrar(timeout=2) == []


def _sopa_rapida() -> tuple[Receita, ...]:
    """A Sopa da demo com tempos 10x menores: mesma forma (empratar = FOGÃO + BALCÃO)."""
    return (Receita("Sopa", (Etapa("cortar", (TipoEstacao.TABUA,), 0.2),
                             Etapa("cozinhar", (FOGAO,), 0.4),
                             Etapa("empratar", (FOGAO, BALCAO), 0.1)), 35, 60),)


def _demo_rapida(**kw) -> Config:
    return replace(Config.demo_deadlock(), tick=0.005, tempo_retirada=0.1,
                   intervalo_inicial=0.1, intervalo_minimo=0.1, receitas=_sopa_rapida(), **kw)


@pytest.mark.demo
def test_ordem_invertida_trava_rapido():
    jogo = Jogo(_demo_rapida())
    jogo.iniciar()
    try:
        assert _rodar_ate(jogo, lambda: _travado(jogo), prazo=10), "a cozinha não travou"
    finally:
        assert jogo.encerrar(timeout=2) == []


def test_ordem_fixa_nao_trava():
    """O mesmo cenário com a ordem fixa ligada: entrega pratos e nunca fica preso."""
    jogo = Jogo(_demo_rapida(ordem_fixa=True))
    jogo.iniciar()
    try:
        assert not _rodar_ate(jogo, lambda: _travado(jogo), prazo=3)
        assert jogo.retrato().entregues > 0
    finally:
        assert jogo.encerrar(timeout=2) == []
