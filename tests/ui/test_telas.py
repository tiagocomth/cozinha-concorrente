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


# ---------- controles (spec 09) ----------

from cozinha.modelo.tipos import EstadoPedido  # noqa: E402
from cozinha.ui import layout  # noqa: E402
from cozinha.ui.telas import TelaInicio as _Inicio  # noqa: E402

from .conftest import receitas_teste  # noqa: E402


def _esperar(cond, prazo: float = 3.0, tela=None) -> None:
    fim = time.monotonic() + prazo
    while not cond():
        assert time.monotonic() < fim, "condição não ficou verdadeira a tempo"
        if tela is not None:
            tela.atualizar(1 / 60)
        time.sleep(0.005)


def _clique_no_pedido(t: TelaJogo, pedido_id: int) -> None:
    r = t.jogo.retrato()
    rect = layout.cartoes_pedidos(r.pedidos, r.tamanho_max_fila)[pedido_id]
    t.evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1))


def test_ordem_do_jogador(telas_abertas):
    t = _tela_jogo(telas_abertas, duracao_partida=30, receitas=receitas_teste(dur=0.4, paciencia=20))
    c2_ocupado = lambda: t.jogo.retrato().cozinheiros[1].pedido_id is not None  # noqa: E731

    def aguardando():
        return [p.id for p in t.jogo.retrato().pedidos if p.estado is EstadoPedido.AGUARDANDO]

    _esperar(lambda: c2_ocupado() and aguardando(), tela=t)
    alvo = aguardando()[-1]
    t.evento(tecla(pygame.K_2))
    _clique_no_pedido(t, alvo)
    v = next(p for p in t.jogo.retrato().pedidos if p.id == alvo)
    assert v.reservado_para == 2
    _esperar(lambda: any(c.pedido_id == alvo for c in t.jogo.retrato().cozinheiros),
             prazo=5, tela=t)
    quem = next(c for c in t.jogo.retrato().cozinheiros if c.pedido_id == alvo)
    assert quem.id == 2


def test_esc_pergunta_e_cancela(telas_abertas):
    t = _tela_jogo(telas_abertas, duracao_partida=30)
    t.evento(tecla(pygame.K_ESCAPE))
    assert t.confirmando and t.jogo.retrato().estado is EstadoPartida.PAUSADA
    t.evento(tecla(pygame.K_ESCAPE))
    assert not t.confirmando and t.jogo.retrato().estado is EstadoPartida.RODANDO


def test_esc_com_pausa_manual(telas_abertas):
    t = _tela_jogo(telas_abertas, duracao_partida=30)
    t.evento(tecla(pygame.K_p))
    t.evento(tecla(pygame.K_ESCAPE))
    t.evento(tecla(pygame.K_ESCAPE))
    assert t.jogo.retrato().estado is EstadoPartida.PAUSADA


def test_esc_enter_volta_ao_inicio(telas_abertas):
    t = _tela_jogo(telas_abertas, duracao_partida=30)
    t.evento(tecla(pygame.K_ESCAPE))
    proxima = t.evento(tecla(pygame.K_RETURN))
    assert isinstance(proxima, _Inicio)
    assert t.jogo.encerrar() == []
    assert all(not th.is_alive() for th in [t.jogo._gerador, *t.jogo._cozinheiros])


def test_confirmando_ignora_outras_teclas(telas_abertas):
    t = _tela_jogo(telas_abertas, duracao_partida=30)
    t.evento(tecla(pygame.K_ESCAPE))
    t.evento(tecla(pygame.K_p))
    t.evento(tecla(pygame.K_1))
    assert t.confirmando and t.jogo.retrato().selecionado is None


def test_debug_alterna(telas_abertas, tela):
    t = _tela_jogo(telas_abertas, duracao_partida=30)
    t.evento(tecla(pygame.K_d))
    assert t.debug
    t.atualizar(1 / 60)
    t.desenhar(tela)
    assert t.jogo.retrato().estado is EstadoPartida.RODANDO
    t.evento(tecla(pygame.K_d))
    assert not t.debug


def test_desenhar_debug_e_confirmacao_exemplo(tela):
    from cozinha.modelo.retrato import Retrato
    from cozinha.ui import desenho
    f = layout.fontes()
    desenho.desenhar_debug(tela, Retrato.exemplo(), f, fps=59.7, threads_vivas=6)
    desenho.desenhar_confirmacao(tela, f)
