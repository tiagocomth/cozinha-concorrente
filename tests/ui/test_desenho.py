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
    cartoes = layout.cartoes_pedidos(_pedidos(6), 6)
    janela = pygame.Rect((0, 0), layout.JANELA)
    assert len(cartoes) == 6
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
