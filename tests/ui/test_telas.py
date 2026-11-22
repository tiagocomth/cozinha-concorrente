from __future__ import annotations

import time

import pygame
import pytest

from cozinha.modelo.tipos import EstadoPartida
from cozinha.ui.telas import SAIR, TelaInicio, TelaJogo, TelaResultado

from .conftest import config_rapida, tecla


@pytest.fixture
def telas_abertas(tela):
    abertas: list = []
    yield abertas
    for t in abertas:
        t.fechar()


def _tela_jogo(abertas, **kw) -> TelaJogo:
    t = TelaJogo(config_rapida(**kw))
    abertas.append(t)
    return t


def test_inicio_enter_comeca(telas_abertas):
    proxima = TelaInicio(config_rapida()).evento(tecla(pygame.K_RETURN))
    assert isinstance(proxima, TelaJogo)
    telas_abertas.append(proxima)
    assert proxima.jogo.retrato().estado is EstadoPartida.RODANDO


def test_inicio_esc_sai(tela):
    assert TelaInicio(config_rapida()).evento(tecla(pygame.K_ESCAPE)) is SAIR


def test_inicio_desenha(tela):
    TelaInicio(config_rapida()).desenhar(tela)


def test_jogo_primeiro_quadro(telas_abertas, tela):
    t = _tela_jogo(telas_abertas)
    t.desenhar(tela)


def test_jogo_p_pausa(telas_abertas):
    t = _tela_jogo(telas_abertas, duracao_partida=30)
    t.evento(tecla(pygame.K_p))
    assert t.jogo.retrato().estado is EstadoPartida.PAUSADA
    t.evento(tecla(pygame.K_p))
    assert t.jogo.retrato().estado is EstadoPartida.RODANDO


def test_foco_pausa(telas_abertas):
    t = _tela_jogo(telas_abertas, duracao_partida=30)
    t.evento(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    assert t.jogo.retrato().estado is EstadoPartida.PAUSADA
    t.evento(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    t.evento(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
    assert t.jogo.retrato().estado is EstadoPartida.PAUSADA


def test_jogo_termina_no_resultado(telas_abertas, tela):
    t = _tela_jogo(telas_abertas)
    fim = time.monotonic() + 6
    proxima = None
    while proxima is None:
        assert time.monotonic() < fim, "a partida não terminou"
        t.atualizar(1 / 60)
        t.desenhar(tela)
        proxima = t.proxima()
        time.sleep(0.01)
    assert isinstance(proxima, TelaResultado)
    assert proxima.retrato.estado in (EstadoPartida.VITORIA, EstadoPartida.DERROTA)
    proxima.desenhar(tela)


def test_resultado(telas_abertas):
    t = _tela_jogo(telas_abertas)
    resultado = TelaResultado(t.config, t.jogo.retrato())
    nova = resultado.evento(tecla(pygame.K_RETURN))
    assert isinstance(nova, TelaJogo) and nova.jogo is not t.jogo
    telas_abertas.append(nova)
    assert resultado.evento(tecla(pygame.K_ESCAPE)) is SAIR


def test_erro_de_thread_sobe(telas_abertas):
    t = _tela_jogo(telas_abertas)
    t.jogo._cozinheiros[0].erro = ValueError("boom")
    with pytest.raises(RuntimeError):
        t.atualizar(1 / 60)
    t.fechar()
    assert t.jogo.encerrar() == []


def test_fechar_encerra(telas_abertas):
    t = _tela_jogo(telas_abertas)
    t.fechar()
    assert all(not th.is_alive() for th in [t.jogo._gerador, *t.jogo._cozinheiros])
