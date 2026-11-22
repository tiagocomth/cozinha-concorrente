from __future__ import annotations

import itertools
import time
from dataclasses import replace

import pygame

from cozinha.config import Config
from cozinha.modelo.retrato import GrupoView, PedidoView, Retrato
from cozinha.modelo.tipos import EstadoPedido, TipoEstacao
from cozinha.ui import desenho, layout


def _descanso(retrato: Retrato) -> dict[int, tuple[float, float]]:
    return {c.id: layout.posicao_descanso(c.id) for c in retrato.cozinheiros}


def test_desenhar_exemplo(tela):
    tela.fill(layout.FUNDO)
    r = Retrato.exemplo()
    desenho.desenhar_retrato(tela, r, _descanso(r), layout.fontes(), cursor=5)
    cores = {tela.get_at((x, y))[:3] for x in range(0, 1280, 40) for y in range(0, 720, 40)}
    assert cores != {layout.FUNDO}


def test_cor_cozinheiro_cicla():
    assert layout.cor_cozinheiro(1) != layout.cor_cozinheiro(2)
    for n in range(1, 21):
        assert len(layout.cor_cozinheiro(n)) == 3


def test_cor_paciencia():
    assert desenho.cor_paciencia(1.0) == layout.PACIENCIA_ALTA
    assert desenho.cor_paciencia(0.4) == layout.PACIENCIA_MEDIA
    assert desenho.cor_paciencia(0.1) == layout.PACIENCIA_BAIXA


def _pedidos(n: int) -> tuple[PedidoView, ...]:
    return tuple(PedidoView(i, "Sopa", EstadoPedido.AGUARDANDO, 0.5, None, None)
                 for i in range(1, n + 1))


def test_cartoes_cabem():
    """Fila cheia (6) e mais 4 em preparo: todos os 10 cartões aparecem."""
    em_preparo = tuple(PedidoView(i, "Prato do dia", EstadoPedido.EM_PREPARO, 0.5, i - 6, None)
                       for i in range(7, 11))
    cartoes = layout.cartoes_pedidos(_pedidos(6) + em_preparo, 6)
    janela = pygame.Rect((0, 0), layout.JANELA)
    assert len(cartoes) == 10
    assert all(janela.contains(r) for r in cartoes.values())
    for a, b in itertools.combinations(cartoes.values(), 2):
        assert not a.colliderect(b)


def _grupos(config: Config) -> tuple[GrupoView, ...]:
    return tuple(GrupoView(t, config.quantidade[t], ()) for t in TipoEstacao)


def test_estacoes_nao_se_sobrepoem():
    for config in (Config(), Config.demo_deadlock()):
        mapa = layout.mapa_estacoes(_grupos(config))
        janela = pygame.Rect((0, 0), layout.JANELA)
        retangulos = list(mapa.estacoes.values())
        assert len(retangulos) == sum(config.quantidade[t] for t in TipoEstacao
                                      if t is not TipoEstacao.BALCAO) + 1
        assert all(janela.contains(r) for r in retangulos)
        for a, b in itertools.combinations(retangulos, 2):
            assert not a.colliderect(b)
        balcao = mapa.estacao(TipoEstacao.BALCAO, 0)
        for i in range(config.quantidade[TipoEstacao.BALCAO]):
            assert balcao.contains(mapa.vaga(i))


def test_desempenho(tela):
    base = Retrato.exemplo()
    r = replace(base, cozinheiros=base.cozinheiros[:4])
    fontes = layout.fontes()
    posicoes = _descanso(r)
    inicio = time.monotonic()
    for _ in range(600):
        tela.fill(layout.FUNDO)
        desenho.desenhar_retrato(tela, r, posicoes, fontes)
        pygame.display.flip()
    assert time.monotonic() - inicio < 10


def test_cozinheiro_visivel_sobre_a_propria_estacao(tela):
    """O círculo tem a cor do cozinheiro, igual à da estação que ele ocupa: precisa de contorno."""
    c = Retrato.exemplo().cozinheiros[0]
    cor = layout.cor_cozinheiro(c.id)
    tela.fill(cor)
    desenho.desenhar_cozinheiro(tela, c, (200, 200), layout.fontes())
    borda = tela.get_at((200 + layout.COZINHEIRO_RAIO + 1, 200))[:3]
    assert borda != cor


def test_hud_com_limite_de_perdidos_alto(tela):
    """A demo de deadlock usa limite_perdidos=1000: as bolinhas não podem invadir o HUD."""
    r = replace(Retrato.exemplo(), limite_perdidos=1000, perdidos=0)
    tela.fill(layout.FUNDO)
    desenho.desenhar_hud(tela, r, layout.fontes())
    esquerda = {tela.get_at((x, y))[:3] for x in range(0, 400) for y in range(10, 46)}
    assert layout.LIVRE not in esquerda
