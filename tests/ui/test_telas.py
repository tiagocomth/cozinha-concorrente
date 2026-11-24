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


# ---------- single player ----------

from cozinha.modelo.tipos import EstadoCozinheiro, TipoEstacao  # noqa: E402

from .test_entrada import Teclas  # noqa: E402


def _tela_jogador(abertas, teclas: Teclas, **kw) -> TelaJogo:
    kw = {"duracao_partida": 30, "n_cozinheiros": 1, "receitas": receitas_teste(paciencia=30),
          **kw}
    t = TelaJogo(config_rapida(jogador=True, **kw), teclas=lambda: teclas)
    abertas.append(t)
    return t


def _no_alvo(t: TelaJogo, alvo) -> None:
    t.avatar.pos = t.mapa.areas_interacao[alvo][0].center


def test_andar_com_teclas(telas_abertas):
    teclas = Teclas(pygame.K_d)
    t = _tela_jogador(telas_abertas, teclas)
    x0 = t.avatar.pos[0]
    for _ in range(10):
        t.atualizar(1 / 60)
    assert t.avatar.pos[0] > x0


def test_nao_anda_pausado(telas_abertas):
    teclas = Teclas(pygame.K_d)
    t = _tela_jogador(telas_abertas, teclas)
    t.evento(tecla(pygame.K_p))
    x0 = t.avatar.pos
    for _ in range(10):
        t.atualizar(1 / 60)
    assert t.avatar.pos == x0


def test_nao_anda_ocupado(telas_abertas):
    teclas = Teclas()
    t = _tela_jogador(telas_abertas, teclas,
                      quantidade={TipoEstacao.TABUA: 1, TipoEstacao.PIA: 1,
                                  TipoEstacao.FOGAO: 1, TipoEstacao.BALCAO: 1})
    t.jogo._cozinha.ocupar_todas(99, (TipoEstacao.TABUA,), lambda: False)
    _esperar(lambda: any(p.estado is EstadoPedido.AGUARDANDO for p in t.jogo.retrato().pedidos),
             tela=t)
    _no_alvo(t, "quadro")
    t.evento(tecla(pygame.K_e))
    _esperar(lambda: t.jogo.retrato().cozinheiros[0].pedido_id is not None, tela=t)
    _no_alvo(t, TipoEstacao.TABUA)
    t.evento(tecla(pygame.K_e))
    _esperar(lambda: t.jogo.retrato().cozinheiros[0].estado is EstadoCozinheiro.ESPERANDO, tela=t)
    for _ in range(120):                    # chega ao lugar da fila
        t.atualizar(1 / 60)
    parado = t.avatar.pos
    teclas.apertadas.add(pygame.K_d)
    for _ in range(10):
        t.atualizar(1 / 60)
    assert t.avatar.pos == parado
    t.evento(tecla(pygame.K_q))             # desiste da fila: volta a andar
    _esperar(lambda: t.jogo.retrato().cozinheiros[0].estado is EstadoCozinheiro.LIVRE, tela=t)
    for _ in range(10):
        t.atualizar(1 / 60)
    assert t.avatar.pos[0] > parado[0]


def test_interagir_no_quadro_e_na_estacao(telas_abertas):
    t = _tela_jogador(telas_abertas, Teclas())
    _esperar(lambda: any(p.estado is EstadoPedido.AGUARDANDO for p in t.jogo.retrato().pedidos),
             tela=t)
    _no_alvo(t, "quadro")
    t.evento(tecla(pygame.K_e))
    _esperar(lambda: t.jogo.retrato().cozinheiros[0].pedido_id is not None, tela=t)
    assert t.jogo.retrato().cozinheiros[0].proxima == (TipoEstacao.TABUA,)
    _no_alvo(t, TipoEstacao.TABUA)
    t.evento(tecla(pygame.K_e))
    _esperar(lambda: t.jogo.retrato().cozinheiros[0].proxima == (TipoEstacao.BALCAO,), tela=t)


def test_interagir_longe_avisa(telas_abertas, tela):
    t = _tela_jogador(telas_abertas, Teclas())
    t.evento(tecla(pygame.K_e))
    assert "perto" in t.aviso
    t.desenhar(tela)


def test_clicar_comanda_so_no_quadro(telas_abertas):
    t = _tela_jogador(telas_abertas, Teclas())
    _esperar(lambda: any(p.estado is EstadoPedido.AGUARDANDO for p in t._retrato.pedidos), tela=t)
    alvo = next(p.id for p in t._retrato.pedidos if p.estado is EstadoPedido.AGUARDANDO)
    rect = layout.cartoes_pedidos(t._retrato.pedidos, t._retrato.tamanho_max_fila)[alvo]
    clique = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1)
    t.evento(clique)
    assert "quadro" in t.aviso.lower()
    _no_alvo(t, "quadro")
    t.jogo.pausar()                         # ninguém tira o pedido da fila enquanto isso
    t.evento(clique)
    t.jogo.retomar()
    _esperar(lambda: t.jogo.retrato().cozinheiros[0].pedido_id == alvo, tela=t)


def test_sem_jogador_e_q_nao_quebram(telas_abertas, tela):
    t = _tela_jogo(telas_abertas, duracao_partida=30)
    t.evento(tecla(pygame.K_e))
    t.evento(tecla(pygame.K_q))
    t.atualizar(1 / 60)
    t.desenhar(tela)
    assert t.avatar is None


def test_estrelas():
    from cozinha.ui.telas import estrelas
    assert estrelas(0, 200) == 0
    assert estrelas(99, 200) == 0
    assert estrelas(100, 200) == 1
    assert estrelas(160, 200) == 2
    assert estrelas(200, 200) == 3
    assert estrelas(500, 200) == 3


def test_inicio_e_resultado_desenham(tela):
    from cozinha.config import Config
    from cozinha.modelo.retrato import Retrato
    TelaInicio(Config.single_player()).desenhar(tela)
    TelaResultado(Config.single_player(), Retrato.exemplo()).desenhar(tela)


def test_inicio_troca_nivel(telas_abertas):
    from cozinha.config import Config
    t = TelaInicio(Config.single_player())
    assert t.nivel == "Normal"
    t.evento(tecla(pygame.K_RIGHT))
    assert t.nivel == "Difícil"
    t.evento(tecla(pygame.K_RIGHT))
    assert t.nivel == "Difícil"
    t.evento(tecla(pygame.K_LEFT))
    t.evento(tecla(pygame.K_LEFT))
    assert t.nivel == "Fácil"
    jogo = t.evento(tecla(pygame.K_RETURN))
    telas_abertas.append(jogo)
    assert jogo.config.meta_pontos == 200


def test_jogar_de_novo_mantem_nivel(telas_abertas):
    from cozinha.config import Config
    cfg = Config.single_player("Difícil")
    nova = TelaResultado(cfg, Retrato_exemplo()).evento(tecla(pygame.K_RETURN))
    telas_abertas.append(nova)
    assert nova.config.nivel == "Difícil"


def Retrato_exemplo():
    from cozinha.modelo.retrato import Retrato
    return Retrato.exemplo()
