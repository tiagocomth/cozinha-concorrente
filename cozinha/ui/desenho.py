"""Funções puras de desenho: recebem a superfície e uma View. Sem estado, sem acesso ao Jogo."""
from __future__ import annotations

from collections.abc import Mapping

import pygame

from cozinha.modelo.retrato import CozinheiroView, PedidoView, Retrato
from cozinha.modelo.tipos import EstadoCozinheiro, EstadoPedido, TipoEstacao
from cozinha.ui import layout
from cozinha.ui.layout import Cor, Fontes, MapaEstacoes, Ponto

NOMES = layout.NOMES_ESTACAO


def _texto(sup: pygame.Surface, fonte: pygame.font.Font, texto: str, pos: tuple[int, int],
           cor: Cor = layout.TEXTO, centro: bool = False) -> pygame.Rect:
    imagem = fonte.render(texto, True, cor)
    r = imagem.get_rect(center=pos) if centro else imagem.get_rect(topleft=pos)
    sup.blit(imagem, r)
    return r


def cor_paciencia(fracao: float) -> Cor:
    if fracao <= layout.LIMIAR_PACIENCIA_BAIXA:
        return layout.PACIENCIA_BAIXA
    if fracao <= layout.LIMIAR_PACIENCIA_MEDIA:
        return layout.PACIENCIA_MEDIA
    return layout.PACIENCIA_ALTA


def _barra(sup: pygame.Surface, r: pygame.Rect, fracao: float, cor: Cor) -> None:
    pygame.draw.rect(sup, layout.LIVRE, r, border_radius=3)
    cheio = r.copy()
    cheio.width = round(r.width * max(0.0, min(1.0, fracao)))
    if cheio.width:
        pygame.draw.rect(sup, cor, cheio, border_radius=3)


def desenhar_hud(sup: pygame.Surface, r: Retrato, f: Fontes) -> None:
    pygame.draw.rect(sup, layout.PAINEL, (0, 0, layout.JANELA[0], layout.HUD_ALTURA))
    minutos, segundos = divmod(int(r.tempo_restante + 0.999), 60)
    _texto(sup, f.media, f"Tempo {minutos}:{segundos:02d}", (layout.MARGEM, 18))
    _texto(sup, f.media, f"Pontos {r.pontos} / {r.meta}", (230, 18))
    _barra(sup, layout.BARRA_PONTOS, r.pontos / r.meta if r.meta else 1.0, layout.META)
    if r.meta_batida:
        _texto(sup, f.media, "meta batida!", (layout.BARRA_PONTOS.right + 16, 18), layout.META)
    x = layout.JANELA[0] - layout.MARGEM - r.limite_perdidos * 2 * (layout.BOLINHA_RAIO + 4)
    _texto(sup, f.media, "Perdidos", (x - 100, 18))
    for i in range(r.limite_perdidos):
        centro = (x + layout.BOLINHA_RAIO + i * 2 * (layout.BOLINHA_RAIO + 4), 28)
        cheia = i < r.perdidos
        pygame.draw.circle(sup, layout.ALERTA if cheia else layout.LIVRE, centro,
                           layout.BOLINHA_RAIO, 0 if cheia else 2)


def desenhar_pedido(sup: pygame.Surface, p: PedidoView, rect: pygame.Rect, f: Fontes,
                    cursor: bool = False) -> None:
    pygame.draw.rect(sup, layout.PAINEL, rect, border_radius=6)
    if p.estado is EstadoPedido.EM_PREPARO and p.cozinheiro_id is not None:
        pygame.draw.rect(sup, layout.cor_cozinheiro(p.cozinheiro_id), rect, 3, border_radius=6)
    if cursor:
        pygame.draw.rect(sup, layout.DESTAQUE, rect.inflate(6, 6), 2, border_radius=8)
    _texto(sup, f.media, f"#{p.id} {p.receita}", (rect.x + 10, rect.y + 8))
    if p.reservado_para is not None:
        centro = (rect.right - 18, rect.y + 18)
        pygame.draw.circle(sup, layout.cor_cozinheiro(p.reservado_para), centro, 12)
        _texto(sup, f.pequena, str(p.reservado_para), centro, centro=True)
    barra = pygame.Rect(rect.x + 10, rect.bottom - 8 - layout.BARRA_PACIENCIA_ALTURA,
                        rect.width - 20, layout.BARRA_PACIENCIA_ALTURA)
    _barra(sup, barra, p.paciencia, cor_paciencia(p.paciencia))


def desenhar_pedidos(sup: pygame.Surface, r: Retrato, f: Fontes, cursor: int | None) -> None:
    na_fila = sum(1 for p in r.pedidos if p.estado is EstadoPedido.AGUARDANDO)
    _texto(sup, f.pequena, f"Pedidos ({na_fila}/{r.tamanho_max_fila} na fila)",
           (layout.MARGEM, layout.PEDIDOS_TITULO_Y), layout.TEXTO_FRACO)
    for pid, rect in layout.cartoes_pedidos(r.pedidos, r.tamanho_max_fila).items():
        desenhar_pedido(sup, next(p for p in r.pedidos if p.id == pid), rect, f, pid == cursor)


def desenhar_estacoes(sup: pygame.Surface, r: Retrato, mapa: MapaEstacoes, f: Fontes) -> None:
    _texto(sup, f.pequena, "Estações (ordem de aquisição: TÁBUA > PIA > FOGÃO > BALCÃO)",
           (layout.MARGEM, layout.ESTACOES_TITULO_Y), layout.TEXTO_FRACO)
    for e in r.estacoes:
        if e.tipo is TipoEstacao.BALCAO:
            vaga = mapa.vaga(e.indice)
            cor = layout.LIVRE if e.ocupada_por is None else layout.cor_cozinheiro(e.ocupada_por)
            pygame.draw.rect(sup, cor, vaga, border_radius=4)
            continue
        rect = mapa.estacao(e.tipo, e.indice)
        cor = layout.LIVRE if e.ocupada_por is None else layout.cor_cozinheiro(e.ocupada_por)
        pygame.draw.rect(sup, cor, rect, border_radius=8)
        _texto(sup, f.pequena, f"{NOMES[e.tipo]} {e.indice + 1}", (rect.x + 8, rect.y + 8))
    balcao = mapa.estacao(TipoEstacao.BALCAO, 0)
    pygame.draw.rect(sup, layout.TEXTO_FRACO, balcao, 2, border_radius=8)
    _texto(sup, f.pequena, NOMES[TipoEstacao.BALCAO], (balcao.x + 8, balcao.y + 8))


def desenhar_cozinheiro(sup: pygame.Surface, c: CozinheiroView, pos: Ponto, f: Fontes,
                        selecionado: bool = False) -> None:
    centro = (round(pos[0]), round(pos[1]))
    if c.estado is EstadoCozinheiro.ESPERANDO:
        pygame.draw.circle(sup, layout.ALERTA, centro, layout.ANEL_ESPERA, 3)
    # Contorno escuro: em cima da estação que ocupa, que tem a mesma cor, ele não some.
    pygame.draw.circle(sup, layout.FUNDO, centro, layout.COZINHEIRO_RAIO + layout.CONTORNO_COZINHEIRO)
    pygame.draw.circle(sup, layout.cor_cozinheiro(c.id), centro, layout.COZINHEIRO_RAIO)
    if selecionado:
        pygame.draw.circle(sup, layout.DESTAQUE, centro,
                           layout.COZINHEIRO_RAIO + layout.CONTORNO_COZINHEIRO
                           + layout.CONTORNO_SELECIONADO, layout.CONTORNO_SELECIONADO)
    _texto(sup, f.media, str(c.id), centro, (20, 20, 20), centro=True)


def linha_cozinheiro(c: CozinheiroView) -> tuple[str, Cor]:
    if c.estado is EstadoCozinheiro.ESPERANDO and c.esperando is not None:
        segura = ", ".join(f"{NOMES[t]} {i + 1}" for t, i in c.segurando)
        extra = f" (segurando {segura})" if segura else ""
        return f"C{c.id} ESPERANDO {NOMES[c.esperando]} há {c.esperando_ha:.1f} s{extra}", layout.ALERTA
    if c.estado is EstadoCozinheiro.TRABALHANDO and c.etapa:
        return f"C{c.id} {c.etapa} #{c.pedido_id} {round(c.progresso * 100)}%", layout.TEXTO
    return f"C{c.id} livre", layout.TEXTO_FRACO


def desenhar_painel(sup: pygame.Surface, r: Retrato, f: Fontes) -> None:
    pygame.draw.rect(sup, layout.PAINEL, (0, layout.PAINEL_Y, layout.JANELA[0],
                                          layout.JANELA[1] - layout.PAINEL_Y))
    for i, c in enumerate(r.cozinheiros):
        texto, cor = linha_cozinheiro(c)
        coluna, linha = divmod(i, 4)
        pos = (layout.MARGEM + coluna * layout.PAINEL_COLUNA,
               layout.PAINEL_Y + 12 + linha * layout.PAINEL_LINHA)
        pygame.draw.circle(sup, layout.cor_cozinheiro(c.id), (pos[0] + 6, pos[1] + 8), 6)
        _texto(sup, f.pequena, texto, (pos[0] + 18, pos[1]), cor)


def desenhar_veu(sup: pygame.Surface) -> None:
    veu = pygame.Surface(layout.JANELA, pygame.SRCALPHA)
    veu.fill(layout.VEU)
    sup.blit(veu, (0, 0))


def desenhar_pausa(sup: pygame.Surface, f: Fontes) -> None:
    desenhar_veu(sup)
    meio = (layout.JANELA[0] // 2, layout.JANELA[1] // 2)
    _texto(sup, f.grande, "PAUSADO — P para continuar", meio, centro=True)


def desenhar_retrato(sup: pygame.Surface, r: Retrato, posicoes: Mapping[int, Ponto],
                     f: Fontes, cursor: int | None = None) -> None:
    """Um quadro inteiro da partida a partir de um retrato (RC06)."""
    sup.fill(layout.FUNDO)
    mapa = layout.mapa_estacoes(r.grupos)
    desenhar_hud(sup, r, f)
    desenhar_pedidos(sup, r, f, cursor)
    desenhar_estacoes(sup, r, mapa, f)
    desenhar_painel(sup, r, f)
    for c in r.cozinheiros:
        pos = posicoes.get(c.id, layout.posicao_descanso(c.id))
        desenhar_cozinheiro(sup, c, pos, f, c.id == r.selecionado)


def desenhar_debug(sup: pygame.Surface, r: Retrato, f: Fontes, fps: float,
                   threads_vivas: int) -> None:
    """Modo debug (RF19): a concorrência por dentro, para a apresentação.

    Por estação na coluna à direita do balcão (as estações continuam visíveis);
    por cozinheiro no lugar do painel inferior.
    """
    caixa = layout.DEBUG_RETANGULO
    fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
    fundo.fill(layout.DEBUG_FUNDO)
    sup.blit(fundo, caixa.topleft)
    na_fila = sum(1 for p in r.pedidos if p.estado is EstadoPedido.AGUARDANDO)
    linhas: list[tuple[str, Cor]] = [
        (f"DEBUG  fila {na_fila}/{r.tamanho_max_fila} · {fps:.0f} FPS", layout.DESTAQUE),
        (f"{threads_vivas} threads vivas", layout.DESTAQUE),
        ("ordem fixa: TÁBUA > PIA > FOGÃO > BALCÃO", layout.TEXTO_FRACO),
        ("", layout.TEXTO),
    ]
    por_id = {c.id: c for c in r.cozinheiros}
    for g in r.grupos:
        dentro = [f"C{e.ocupada_por}" for e in r.estacoes
                  if e.tipo is g.tipo and e.ocupada_por is not None]
        linhas.append((f"{NOMES[g.tipo]} [{len(dentro)}/{g.capacidade}]: "
                       f"{', '.join(dentro) or '-'}", layout.TEXTO))
        for cid in g.fila_espera:
            ha = f" há {por_id[cid].esperando_ha:.1f}s" if cid in por_id else ""
            linhas.append((f"   espera: C{cid}{ha}", layout.ALERTA))
    y = caixa.y + 10
    for texto, cor in linhas:
        if texto:
            _texto(sup, f.pequena, texto, (caixa.x + 12, y), cor)
        y += layout.DEBUG_LINHA

    pygame.draw.rect(sup, layout.PAINEL, (0, layout.PAINEL_Y, layout.JANELA[0],
                                          layout.JANELA[1] - layout.PAINEL_Y))
    for i, c in enumerate(r.cozinheiros):
        segura = ", ".join(f"{NOMES[t]} {n + 1}" for t, n in c.segurando) or "-"
        espera = NOMES[c.esperando] if c.esperando is not None else "-"
        cor = layout.ALERTA if c.esperando is not None else layout.TEXTO
        coluna, linha = divmod(i, 4)
        pos = (layout.MARGEM + coluna * layout.PAINEL_COLUNA,
               layout.PAINEL_Y + 12 + linha * layout.PAINEL_LINHA)
        pygame.draw.circle(sup, layout.cor_cozinheiro(c.id), (pos[0] + 6, pos[1] + 8), 6)
        _texto(sup, f.pequena, f"C{c.id} {c.estado.name}: segura {segura} · espera {espera}"
                               f" · total {c.espera_total:.1f}s", (pos[0] + 18, pos[1]), cor)


def desenhar_confirmacao(sup: pygame.Surface, f: Fontes) -> None:
    desenhar_veu(sup)
    caixa = layout.CONFIRMACAO_RETANGULO
    pygame.draw.rect(sup, layout.PAINEL, caixa, border_radius=10)
    pygame.draw.rect(sup, layout.DESTAQUE, caixa, 2, border_radius=10)
    _texto(sup, f.grande, "Sair da partida?", (caixa.centerx, caixa.y + 45), centro=True)
    _texto(sup, f.media, "Enter = sim · Esc = não", (caixa.centerx, caixa.y + 100),
           layout.TEXTO_FRACO, centro=True)
