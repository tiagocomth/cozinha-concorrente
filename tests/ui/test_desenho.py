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
    desenho.desenhar_retrato(tela, r, _descanso(r), layout.fontes(),
                             jogador_pos=layout.INICIO_JOGADOR, perto=TipoEstacao.TABUA, t=0.4,
                             dica="Leve o pedido para a TÁBUA")
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


def test_cozinheiro_visivel_sobre_a_propria_cor(tela):
    """O corpo tem a cor do cozinheiro: precisa de contorno para não sumir num fundo igual."""
    c = Retrato.exemplo().cozinheiros[1]
    cor = layout.cor_cozinheiro(c.id)
    tela.fill(cor)
    desenho.desenhar_chef(tela, c, (200, 200), layout.fontes(), jogador=False)
    borda = tela.get_at((200 + layout.COZINHEIRO_RAIO + 1, 200))[:3]
    assert borda != cor


def test_hud_com_limite_de_perdidos_alto(tela):
    """A demo de deadlock usa limite_perdidos=1000: as bolinhas não podem invadir o HUD."""
    r = replace(Retrato.exemplo(), limite_perdidos=1000, perdidos=0)
    tela.fill(layout.FUNDO)
    desenho.desenhar_hud(tela, r, layout.fontes())
    esquerda = {tela.get_at((x, y))[:3] for x in range(0, 400) for y in range(10, 46)}
    assert layout.LIVRE not in esquerda


def _pintados(tela, caixa: pygame.Rect, fundo) -> int:
    return sum(1 for x in range(caixa.left, caixa.right) for y in range(caixa.top, caixa.bottom)
               if tela.get_at((x, y))[:3] != fundo)


def test_fogao_aceso(tela):
    rect = pygame.Rect(100, 100, *layout.ESTACAO_TAMANHO)
    centro, _ = layout.bocas_fogao(rect)[0]
    desenho.desenhar_fogao(tela, rect, aceso=False)
    apagado = tela.get_at(centro)[:3]
    desenho.desenhar_fogao(tela, rect, aceso=True)
    assert tela.get_at(centro)[:3] != apagado


def test_chef_jogador_maior(tela):
    r = Retrato.exemplo()
    fundo = (0, 0, 0)
    caixa = pygame.Rect(150, 130, 100, 100)
    tela.fill(fundo)
    desenho.desenhar_chef(tela, r.cozinheiros[1], (200, 190), layout.fontes(), jogador=False)
    automatico = _pintados(tela, caixa, fundo)
    tela.fill(fundo)
    desenho.desenhar_chef(tela, r.cozinheiros[0], (200, 190), layout.fontes(), jogador=True)
    assert _pintados(tela, caixa, fundo) > automatico


def test_comanda_mostra_etapas(tela):
    T, P, F, B = TipoEstacao
    sopa = PedidoView(7, "Sopa", EstadoPedido.AGUARDANDO, 0.8, None, None, ((T,), (F,), (F, B)), 0)
    rect = pygame.Rect(40, 60, *layout.CARTAO_TAMANHO)
    tela.fill((0, 0, 0))
    desenho.desenhar_comanda(tela, sopa, rect, layout.fontes(), do_jogador=False)
    icones = layout.icones_comanda(rect, 3)
    assert len(icones) == 3
    for icone in icones:
        assert rect.contains(icone)
        assert tela.get_at(icone.center)[:3] != layout.PAPEL


def test_fonte_cai_para_padrao(tela, monkeypatch):
    def falhar(*a, **k):
        raise OSError("sem fonte")
    monkeypatch.setattr(pygame.font, "SysFont", falhar)
    f = layout.fontes()
    assert f.media.size("abc")[0] > 0


def _foto(tela, caixa):
    return [tela.get_at((x, y))[:3] for x in range(caixa.left, caixa.right, 2)
            for y in range(caixa.top, caixa.bottom, 2)]


def test_icones_etapa_distintos(tela):
    caixa = pygame.Rect(10, 10, 24, 24)
    fotos = []
    for tipo in TipoEstacao:
        tela.fill((0, 0, 0))
        desenho.desenhar_icone_etapa(tela, tipo, caixa)
        fotos.append(_foto(tela, caixa))
    for a, b in itertools.combinations(fotos, 2):
        assert a != b


def test_vapor_anima(tela):
    rect = pygame.Rect(300, 300, *layout.ESTACAO_TAMANHO)
    area = rect.inflate(0, 40).move(0, -20)
    tela.fill((0, 0, 0))
    desenho.desenhar_fogao(tela, rect, aceso=True)
    desenho.desenhar_vapor(tela, rect, 0.1)
    a = _foto(tela, area)
    tela.fill((0, 0, 0))
    desenho.desenhar_fogao(tela, rect, aceso=True)
    desenho.desenhar_vapor(tela, rect, 0.6)
    assert _foto(tela, area) != a


def test_chef_balanca(tela):
    c = Retrato.exemplo().cozinheiros[1]
    caixa = pygame.Rect(170, 150, 60, 80)
    fotos = []
    for t in (0.0, 0.15):
        tela.fill((0, 0, 0))
        desenho.desenhar_chef(tela, c, (200, 200), layout.fontes(), andando=True, t=t)
        fotos.append(_foto(tela, caixa))
    assert fotos[0] != fotos[1]


def test_desenhar_com_efeitos(tela):
    from cozinha.ui.efeitos import Efeitos
    r = Retrato.exemplo()
    e = Efeitos()
    e.observar(r, replace(r, pontos=r.pontos + 35, entregues=r.entregues + 1),
               layout.mapa_estacoes(r.grupos))
    desenho.desenhar_retrato(tela, r, _descanso(r), layout.fontes(), efeitos=e.ativos,
                             pulso=e.pulso_pontos, andando=frozenset({2}), t=0.3)
