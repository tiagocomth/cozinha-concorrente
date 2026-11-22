from __future__ import annotations

import threading
import time
from dataclasses import replace

import pytest

from cozinha.config import Config
from cozinha.jogo import Jogo
from cozinha.modelo.receita import Etapa, Receita
from cozinha.modelo.tipos import EstadoPartida, TipoEstacao

TABUA, PIA, FOGAO, BALCAO = TipoEstacao


def receitas(dur: float = 0.01, paciencia: float = 2.0) -> tuple[Receita, ...]:
    return (
        Receita("Salada", (Etapa("cortar", (TABUA,), dur), Etapa("entregar", (BALCAO,), dur)),
                20, paciencia),
        Receita("Sopa", (Etapa("cortar", (TABUA,), dur), Etapa("cozinhar", (FOGAO,), dur),
                         Etapa("empratar", (FOGAO, BALCAO), dur)), 35, paciencia),
    )


def config_rapida(**kw) -> Config:
    base = dict(duracao_partida=3, n_cozinheiros=2, tick=0.005, tempo_retirada=0,
                intervalo_inicial=0.1, intervalo_minimo=0.05, semente=1, receitas=receitas())
    return replace(Config(), **{**base, **kw})


def esperar(condicao, prazo: float = 2.0) -> None:
    fim = time.monotonic() + prazo
    while not condicao():
        assert time.monotonic() < fim, "condição não ficou verdadeira a tempo"
        time.sleep(0.005)


@pytest.fixture
def novo_jogo():
    criados: list[Jogo] = []

    def fabrica(config: Config | None = None, **kw) -> Jogo:
        j = Jogo(config or config_rapida(), **kw)
        criados.append(j)
        return j

    yield fabrica
    for j in criados:
        assert j.encerrar(timeout=2) == []


def _nomes_vivos() -> set[str]:
    return {t.name for t in threading.enumerate()}


# ---------- Task 3 ----------

def test_construir_nao_inicia_threads(novo_jogo):
    antes = threading.active_count()
    novo_jogo()
    assert threading.active_count() == antes


def test_iniciar_sobe_threads(novo_jogo):
    j = novo_jogo()
    antes = threading.active_count()
    j.iniciar()
    assert threading.active_count() == antes + 3
    assert {"gerador", "cozinheiro-1", "cozinheiro-2"} <= _nomes_vivos()


def test_iniciar_duas_vezes(novo_jogo):
    j = novo_jogo()
    j.iniciar()
    depois = threading.active_count()
    j.iniciar()
    assert threading.active_count() == depois


def test_iniciar_depois_de_encerrar(novo_jogo):
    j = novo_jogo()
    j.iniciar()
    assert j.encerrar() == []
    antes = threading.active_count()
    j.iniciar()
    assert threading.active_count() == antes


def test_pedido_vencido_vira_perdido(novo_jogo):
    j = novo_jogo(config_rapida(n_cozinheiros=1, receitas=receitas(dur=5, paciencia=0.1)))
    j.iniciar()
    fim = time.monotonic() + 0.5
    while time.monotonic() < fim:
        j.atualizar()
        time.sleep(0.01)
    assert j._pontuacao.valores()[2] > 0
    agora = j._relogio.agora()
    assert all(v.paciencia > 0 for v in j._fila.views(agora))


def test_atualizar_parado_nao_faz_nada(novo_jogo, fonte_falsa):
    j = novo_jogo(config_rapida(receitas=receitas(paciencia=0.1)), fonte_tempo=fonte_falsa)
    j.atualizar()                                   # antes de iniciar
    assert j._pontuacao.valores() == (0, 0, 0)
    j.iniciar()
    esperar(lambda: len(j._fila) > 0 or any(c.view().pedido_id for c in j._cozinheiros))
    j.pausar()
    fonte_falsa.avancar(10)
    antes = (j._pontuacao.valores(), len(j._fila))
    j.atualizar()
    assert (j._pontuacao.valores(), len(j._fila)) == antes


def test_erro_de_thread_levanta(novo_jogo):
    j = novo_jogo()
    j.iniciar()
    original = ValueError("x")
    j._cozinheiros[0].erro = original
    with pytest.raises(RuntimeError) as info:
        j.atualizar()
    assert info.value.__cause__ is original
    assert j._parar.is_set()


def test_fim_sinaliza_parada(novo_jogo, fonte_falsa):
    j = novo_jogo(fonte_tempo=fonte_falsa)
    j.iniciar()
    fonte_falsa.avancar(3)
    j.atualizar()
    assert j._partida.terminou
    assert j._parar.is_set()
