"""Funções de desenho: recebem a superfície e Views. Sem estado, sem acesso ao Jogo.

A cozinha é vista de cima: piso de ladrilhos, bancadas na parede de cima, balcão na
parede direita, quadro de pedidos na esquerda e os cozinheiros com chapéu de chef.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

import pygame

from cozinha.modelo.retrato import CozinheiroView, PedidoView, Retrato
from cozinha.modelo.tipos import EstadoCozinheiro, EstadoPedido, TipoEstacao
from cozinha.ui import layout
from cozinha.ui.layout import Alvo, Cor, Fontes, MapaEstacoes, Ponto

NOMES = layout.NOMES_ESTACAO
TABUA, PIA, FOGAO, BALCAO = TipoEstacao


# ---------- utilidades ----------

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


def _barra(sup: pygame.Surface, r: pygame.Rect, fracao: float, cor: Cor,
           fundo: Cor = layout.LIVRE) -> None:
    pygame.draw.rect(sup, fundo, r, border_radius=3)
    cheio = r.copy()
    cheio.width = round(r.width * max(0.0, min(1.0, fracao)))
    if cheio.width:
        pygame.draw.rect(sup, cor, cheio, border_radius=3)


def _nomes(tipos: tuple[TipoEstacao, ...]) -> str:
    return " + ".join(NOMES[t] for t in tipos)


def _icone_estacao(sup: pygame.Surface, f: Fontes, tipo: TipoEstacao, rect: pygame.Rect,
                   feito: bool = False, atual: bool = False) -> None:
    cor = layout.CORES_ESTACAO[tipo]
    if feito:
        cor = tuple(c // 2 + 100 for c in cor)
    pygame.draw.rect(sup, cor, rect, border_radius=4)
    if atual:
        pygame.draw.rect(sup, layout.TINTA, rect.inflate(4, 4), 2, border_radius=5)
    _texto(sup, f.pequena, layout.LETRAS_ESTACAO[tipo], rect.center, layout.BALAO, centro=True)


# ---------- HUD e comandas ----------

def desenhar_hud(sup: pygame.Surface, r: Retrato, f: Fontes) -> None:
    pygame.draw.rect(sup, layout.PAINEL, (0, 0, layout.JANELA[0], layout.HUD_ALTURA))
    minutos, segundos = divmod(int(r.tempo_restante + 0.999), 60)
    cor_tempo = layout.ALERTA if r.tempo_restante < 30 else layout.TEXTO
    _texto(sup, f.media, f"Tempo {minutos}:{segundos:02d}", (layout.MARGEM, 16), cor_tempo)
    _texto(sup, f.media, f"Pontos {r.pontos} / {r.meta}", (230, 16))
    _barra(sup, layout.BARRA_PONTOS, r.pontos / r.meta if r.meta else 1.0, layout.META)
    if r.meta_batida:
        _texto(sup, f.media, "meta batida!", (layout.BARRA_PONTOS.right + 16, 16), layout.META)
    if r.limite_perdidos > layout.MAX_BOLINHAS:      # ex.: a demo de deadlock (limite 1000)
        texto = f"Perdidos {r.perdidos} / {r.limite_perdidos}"
        largura = f.media.size(texto)[0]
        _texto(sup, f.media, texto, (layout.JANELA[0] - layout.MARGEM - largura, 16))
        return
    x = layout.JANELA[0] - layout.MARGEM - r.limite_perdidos * 2 * (layout.BOLINHA_RAIO + 4)
    _texto(sup, f.media, "Perdidos", (x - 100, 16))
    for i in range(r.limite_perdidos):
        centro = (x + layout.BOLINHA_RAIO + i * 2 * (layout.BOLINHA_RAIO + 4), 26)
        cheia = i < r.perdidos
        pygame.draw.circle(sup, layout.ALERTA if cheia else layout.LIVRE, centro,
                           layout.BOLINHA_RAIO, 0 if cheia else 2)


def desenhar_comanda(sup: pygame.Surface, p: PedidoView, rect: pygame.Rect, f: Fontes,
                     do_jogador: bool = False, cursor: bool = False) -> None:
    """Comanda de papel: número, prato, trilha de etapas e paciência do cliente."""
    pygame.draw.rect(sup, layout.PAPEL_JOGADOR if do_jogador else layout.PAPEL, rect,
                     border_radius=6)
    if p.reservado_para is not None or do_jogador:
        dono = p.reservado_para if p.reservado_para is not None else p.cozinheiro_id
        pygame.draw.rect(sup, layout.cor_cozinheiro(dono or 1), rect, 3, border_radius=6)
    if cursor:
        pygame.draw.rect(sup, layout.DESTAQUE, rect.inflate(6, 6), 2, border_radius=8)
    _texto(sup, f.media, f"#{p.id} {p.receita}", (rect.x + 10, rect.y + 8), layout.TINTA)
    for i, (tipos, icone) in enumerate(zip(p.etapas, layout.icones_comanda(rect, len(p.etapas)))):
        _icone_estacao(sup, f, max(tipos), icone, feito=i < p.etapa_atual,
                       atual=i == p.etapa_atual and do_jogador)
    barra = pygame.Rect(rect.x + 10, rect.bottom - 8 - layout.BARRA_PACIENCIA_ALTURA,
                        rect.width - 20, layout.BARRA_PACIENCIA_ALTURA)
    _barra(sup, barra, p.paciencia, cor_paciencia(p.paciencia), (210, 200, 185))


def desenhar_etiqueta_preparo(sup: pygame.Surface, p: PedidoView, rect: pygame.Rect,
                              f: Fontes) -> None:
    cor = layout.cor_cozinheiro(p.cozinheiro_id or 1)
    pygame.draw.rect(sup, layout.PAINEL, rect, border_radius=5)
    pygame.draw.rect(sup, cor, rect, 2, border_radius=5)
    _texto(sup, f.pequena, f"#{p.id} {p.receita} · C{p.cozinheiro_id}", (rect.x + 8, rect.y + 6))
    barra = pygame.Rect(rect.x + 4, rect.bottom - 5, rect.width - 8, 3)
    _barra(sup, barra, p.paciencia, cor_paciencia(p.paciencia))


def desenhar_pedidos(sup: pygame.Surface, r: Retrato, f: Fontes, cursor: int | None = None,
                     pedido_jogador: int | None = None) -> None:
    for pid, rect in layout.cartoes_pedidos(r.pedidos, r.tamanho_max_fila).items():
        p = next(x for x in r.pedidos if x.id == pid)
        if p.estado is EstadoPedido.AGUARDANDO:
            desenhar_comanda(sup, p, rect, f, cursor=pid == cursor)
        elif pid == pedido_jogador:
            desenhar_etiqueta_preparo(sup, p, rect, f)
            pygame.draw.rect(sup, layout.BRILHO, rect.inflate(4, 4), 2, border_radius=6)
        else:
            desenhar_etiqueta_preparo(sup, p, rect, f)


# ---------- a cozinha ----------

def desenhar_piso(sup: pygame.Surface) -> None:
    pygame.draw.rect(sup, layout.PAREDE_COR, layout.COZINHA, border_radius=10)
    piso = layout.PISO
    sup.fill(layout.PISO_A, piso)
    lado = layout.LADRILHO
    for i, x in enumerate(range(piso.left, piso.right, lado)):
        for j, y in enumerate(range(piso.top, piso.bottom, lado)):
            if (i + j) % 2:
                sup.fill(layout.PISO_B, pygame.Rect(x, y, lado, lado).clip(piso))


def _bancada(sup: pygame.Surface, rect: pygame.Rect, cor: Cor = layout.ACO_ESCURO) -> pygame.Rect:
    """Fundo da estação e faixa do nome; devolve o corpo, onde o objeto é desenhado."""
    pygame.draw.rect(sup, layout.TINTA, rect, border_radius=8)
    corpo = layout.corpo_estacao(rect)
    pygame.draw.rect(sup, cor, corpo, border_radius=8)
    pygame.draw.rect(sup, layout.TINTA, rect, 2, border_radius=8)
    return corpo


def desenhar_tabua(sup: pygame.Surface, rect: pygame.Rect) -> None:
    corpo = _bancada(sup, rect)
    tabua = corpo.inflate(-26, -20)
    pygame.draw.rect(sup, layout.MADEIRA_CLARA, tabua, border_radius=6)
    pygame.draw.rect(sup, layout.MADEIRA, tabua, 2, border_radius=6)
    # faca: lâmina e cabo
    pygame.draw.line(sup, layout.ACO, (tabua.left + 14, tabua.bottom - 10),
                     (tabua.right - 26, tabua.top + 10), 4)
    pygame.draw.line(sup, layout.TINTA, (tabua.right - 26, tabua.top + 10),
                     (tabua.right - 12, tabua.top + 3), 6)


def desenhar_pia(sup: pygame.Surface, rect: pygame.Rect) -> None:
    corpo = _bancada(sup, rect, layout.ACO)
    cuba = corpo.inflate(-30, -22)
    pygame.draw.rect(sup, layout.ACO_ESCURO, cuba, border_radius=10)
    pygame.draw.rect(sup, layout.AGUA, cuba.inflate(-8, -8), border_radius=8)
    torneira = (corpo.centerx, corpo.top + 6)
    pygame.draw.line(sup, layout.ACO_ESCURO, torneira, (corpo.centerx, cuba.top + 4), 5)
    pygame.draw.circle(sup, layout.ACO_ESCURO, torneira, 5)


def desenhar_fogao(sup: pygame.Surface, rect: pygame.Rect, aceso: bool) -> None:
    _bancada(sup, rect, layout.FOGAO_COR)
    for centro, raio in layout.bocas_fogao(rect):
        pygame.draw.circle(sup, layout.BOCA, centro, raio + 3)
        if aceso:
            pygame.draw.circle(sup, layout.BOCA_ACESA, centro, raio)
            pygame.draw.circle(sup, layout.BRILHO, centro, max(2, raio // 2))
        else:
            pygame.draw.circle(sup, layout.ACO_ESCURO, centro, raio, 2)


def desenhar_balcao(sup: pygame.Surface, rect: pygame.Rect, vagas: list[pygame.Rect],
                    ocupacoes: list[int | None]) -> None:
    pygame.draw.rect(sup, layout.MADEIRA, rect, border_radius=8)
    pygame.draw.rect(sup, layout.TINTA, rect, 2, border_radius=8)
    for vaga, dono in zip(vagas, ocupacoes):
        pygame.draw.circle(sup, layout.PRATO, vaga.center, vaga.width // 2)
        pygame.draw.circle(sup, layout.ACO, vaga.center, vaga.width // 2, 2)
        if dono is not None:
            pygame.draw.circle(sup, layout.cor_cozinheiro(dono), vaga.center, vaga.width // 3)


def desenhar_quadro(sup: pygame.Surface, f: Fontes, n_pedidos: int) -> None:
    q = layout.QUADRO
    pygame.draw.rect(sup, layout.MADEIRA, q, border_radius=6)
    pygame.draw.rect(sup, layout.CORTICA, q.inflate(-10, -10), border_radius=4)
    for i in range(min(n_pedidos, 6)):
        papel = pygame.Rect(q.left + 12 + (i % 2) * 24, q.top + 16 + (i // 2) * 34, 20, 26)
        pygame.draw.rect(sup, layout.PAPEL, papel)
        pygame.draw.circle(sup, layout.ALERTA, (papel.centerx, papel.top + 3), 3)
    _texto(sup, f.pequena, "PEDIDOS", (q.centerx, q.bottom + 10), layout.TINTA, centro=True)


def _brilho(sup: pygame.Surface, rect: pygame.Rect, t: float) -> None:
    """Contorno pulsando: a próxima estação do jogador."""
    largura = 3 + round(2 * (1 + math.sin(t * 6)))
    pygame.draw.rect(sup, layout.BRILHO, rect.inflate(10, 10), largura, border_radius=12)


def _tecla(sup: pygame.Surface, f: Fontes, letra: str, centro: tuple[int, int]) -> None:
    caixa = pygame.Rect(0, 0, 26, 26)
    caixa.center = centro
    pygame.draw.rect(sup, layout.BALAO, caixa, border_radius=5)
    pygame.draw.rect(sup, layout.TINTA, caixa, 2, border_radius=5)
    _texto(sup, f.media, letra, caixa.center, layout.TINTA, centro=True)


def desenhar_estacoes(sup: pygame.Surface, r: Retrato, mapa: MapaEstacoes, f: Fontes,
                      destaque: tuple[TipoEstacao, ...] = (), perto: Alvo | None = None,
                      t: float = 0.0) -> None:
    usando: dict[tuple[TipoEstacao, int], CozinheiroView] = {}
    for c in r.cozinheiros:
        if c.estado is EstadoCozinheiro.TRABALHANDO:
            for chave in c.segurando:
                usando[chave] = c
    na_fila = sum(1 for p in r.pedidos if p.estado is EstadoPedido.AGUARDANDO)
    desenhar_quadro(sup, f, na_fila)
    ocupacoes_balcao: list[int | None] = []
    for e in r.estacoes:
        if e.tipo is BALCAO:
            ocupacoes_balcao.append(e.ocupada_por)
            continue
        rect = mapa.estacao(e.tipo, e.indice)
        if e.tipo is TABUA:
            desenhar_tabua(sup, rect)
        elif e.tipo is PIA:
            desenhar_pia(sup, rect)
        else:
            desenhar_fogao(sup, rect, aceso=e.ocupada_por is not None)
        _texto(sup, f.pequena, f"{NOMES[e.tipo]} {e.indice + 1}",
               (rect.centerx, rect.bottom - layout.FAIXA_NOME // 2), layout.BALAO, centro=True)
    balcao = mapa.estacao(BALCAO, 0)
    desenhar_balcao(sup, balcao, mapa.vagas, ocupacoes_balcao)
    _texto(sup, f.pequena, NOMES[BALCAO], (balcao.centerx, balcao.top - 10), layout.TINTA,
           centro=True)
    # progresso de quem está trabalhando, em cima da estação
    for (tipo, indice), c in usando.items():
        rect = mapa.vaga(indice) if tipo is BALCAO else mapa.estacao(tipo, indice)
        barra = pygame.Rect(rect.left, rect.bottom + 2, rect.width, 6)
        _barra(sup, barra, c.progresso, layout.cor_cozinheiro(c.id))
    for tipo in destaque:
        for rect in ([balcao] if tipo is BALCAO else
                     [rect for (t2, _), rect in mapa.estacoes.items() if t2 is tipo]):
            _brilho(sup, rect, t)
    if perto is not None:
        areas = mapa.areas_interacao.get(perto, [])
        if areas:
            alvo = layout.QUADRO if perto == "quadro" else (
                balcao if perto is BALCAO else min(
                    (rect for (t2, _), rect in mapa.estacoes.items() if t2 is perto),
                    key=lambda rect: abs(rect.centerx - areas[0].centerx)))
            _tecla(sup, f, "E", (alvo.right - 4, alvo.top + 4))


def desenhar_rotulo(sup: pygame.Surface, f: Fontes, texto: str, pos: tuple[int, int],
                    cor: Cor = layout.TINTA) -> None:
    imagem = f.pequena.render(texto, True, cor)
    caixa = imagem.get_rect(midbottom=pos).inflate(10, 6)
    pygame.draw.rect(sup, layout.BALAO, caixa, border_radius=6)
    pygame.draw.rect(sup, cor, caixa, 1, border_radius=6)
    sup.blit(imagem, imagem.get_rect(center=caixa.center))


def rotulo_cozinheiro(c: CozinheiroView) -> tuple[str, Cor] | None:
    if c.estado is EstadoCozinheiro.ESPERANDO and c.esperando is not None:
        return f"esperando {NOMES[c.esperando]} {c.esperando_ha:.1f}s", layout.ALERTA
    if c.estado is EstadoCozinheiro.TRABALHANDO and c.etapa:
        return f"{c.etapa} {round(c.progresso * 100)}%", layout.TINTA
    return None


def desenhar_chef(sup: pygame.Surface, c: CozinheiroView, pos: Ponto, f: Fontes,
                  jogador: bool = False, selecionado: bool = False) -> None:
    """Corpo na cor do cozinheiro, chapéu de chef e o número. O do jogador é maior."""
    raio = layout.JOGADOR_RAIO if jogador else layout.COZINHEIRO_RAIO
    centro = (round(pos[0]), round(pos[1]))
    pygame.draw.ellipse(sup, layout.SOMBRA,                            # sombra no chão
                        pygame.Rect(centro[0] - raio, centro[1] + raio - 6, 2 * raio, 12))
    if c.estado is EstadoCozinheiro.ESPERANDO:
        pygame.draw.circle(sup, layout.ALERTA, centro, raio + 8, 3)
    if jogador or selecionado:
        pygame.draw.circle(sup, layout.BRILHO, centro, raio + layout.CONTORNO_COZINHEIRO + 3)
    pygame.draw.circle(sup, layout.TINTA, centro, raio + layout.CONTORNO_COZINHEIRO)
    pygame.draw.circle(sup, layout.cor_cozinheiro(c.id), centro, raio)
    # chapéu: copa arredondada em cima de uma faixa
    copa = pygame.Rect(0, 0, raio + 8, raio)
    copa.midbottom = (centro[0], centro[1] - raio + 6)
    faixa = pygame.Rect(0, 0, raio + 2, 7)
    faixa.midtop = (centro[0], copa.bottom - 3)
    pygame.draw.ellipse(sup, layout.CHAPEU, copa)
    pygame.draw.ellipse(sup, layout.TINTA, copa, 1)
    pygame.draw.rect(sup, layout.CHAPEU, faixa, border_radius=2)
    pygame.draw.rect(sup, layout.TINTA, faixa, 1, border_radius=2)
    _texto(sup, f.media, str(c.id), (centro[0], centro[1] + 2), (20, 20, 20), centro=True)
    if jogador:
        _texto(sup, f.pequena, "VOCÊ", (centro[0], centro[1] + raio + 14), layout.TINTA, centro=True)


# legado (testes e chamadas antigas)
def desenhar_cozinheiro(sup: pygame.Surface, c: CozinheiroView, pos: Ponto, f: Fontes,
                        selecionado: bool = False) -> None:
    desenhar_chef(sup, c, pos, f, jogador=c.jogador, selecionado=selecionado)


def desenhar_dica(sup: pygame.Surface, texto: str, f: Fontes, alerta: bool = False) -> None:
    barra = pygame.Rect(layout.COZINHA.left, layout.DICA_Y, layout.COZINHA.width,
                        layout.JANELA[1] - layout.DICA_Y - 4)
    pygame.draw.rect(sup, layout.PAINEL, barra, border_radius=8)
    _texto(sup, f.media, texto, barra.center, layout.ALERTA if alerta else layout.DESTAQUE,
           centro=True)


def dica_jogador(c: CozinheiroView | None, perto: Alvo | None) -> str:
    """O que o jogador deve fazer agora, em uma linha."""
    if c is None:
        return ""
    if c.estado is EstadoCozinheiro.ESPERANDO and c.esperando is not None:
        return f"Na fila da {NOMES[c.esperando]}: espere a vez · Q para desistir"
    if c.estado is EstadoCozinheiro.TRABALHANDO:
        return f"{(c.etapa or '').capitalize()}... {round(c.progresso * 100)}%"
    if c.pedido_id is None:
        if perto == "quadro":
            return "Aperte E para pegar o pedido mais antigo (ou clique numa comanda)"
        return "Vá ao quadro de PEDIDOS (à esquerda) e aperte E"
    if c.proxima:
        alvo = _nomes(c.proxima)
        if perto in c.proxima:
            return f"Aperte E para usar: {alvo}"
        return f"Pedido #{c.pedido_id}: leve à {alvo} e aperte E · Q descarta"
    return ""


# ---------- quadro inteiro ----------

def desenhar_veu(sup: pygame.Surface) -> None:
    veu = pygame.Surface(layout.JANELA, pygame.SRCALPHA)
    veu.fill(layout.VEU)
    sup.blit(veu, (0, 0))


def desenhar_pausa(sup: pygame.Surface, f: Fontes) -> None:
    desenhar_veu(sup)
    meio = (layout.JANELA[0] // 2, layout.JANELA[1] // 2)
    _texto(sup, f.grande, "PAUSADO — P para continuar", meio, centro=True)


def desenhar_retrato(sup: pygame.Surface, r: Retrato, posicoes: Mapping[int, Ponto],
                     f: Fontes, cursor: int | None = None, jogador_pos: Ponto | None = None,
                     perto: Alvo | None = None, t: float = 0.0, dica: str | None = None,
                     dica_alerta: bool = False) -> None:
    """Um quadro inteiro da partida a partir de um retrato (RC06)."""
    sup.fill(layout.FUNDO)
    mapa = layout.mapa_estacoes(r.grupos)
    jogador = next((c for c in r.cozinheiros if c.jogador), None)
    desenhar_hud(sup, r, f)
    desenhar_pedidos(sup, r, f, cursor, jogador.pedido_id if jogador else None)
    desenhar_piso(sup)
    destaque = jogador.proxima if jogador else ()
    desenhar_estacoes(sup, r, mapa, f, destaque, perto, t)
    for c in sorted(r.cozinheiros, key=lambda c: c.jogador):        # o jogador por cima
        if c.jogador and jogador_pos is not None:
            pos = jogador_pos
        else:
            pos = posicoes.get(c.id, layout.posicao_descanso(c.id))
        desenhar_chef(sup, c, pos, f, jogador=c.jogador, selecionado=c.id == r.selecionado)
        rotulo = rotulo_cozinheiro(c)
        if rotulo:
            raio = layout.JOGADOR_RAIO if c.jogador else layout.COZINHEIRO_RAIO
            desenhar_rotulo(sup, f, rotulo[0], (round(pos[0]), round(pos[1]) - raio - 16), rotulo[1])
    if dica is None and jogador is not None:
        dica = dica_jogador(jogador, perto)
    if dica:
        desenhar_dica(sup, dica, f, dica_alerta)


# ---------- debug e confirmação ----------

def desenhar_debug(sup: pygame.Surface, r: Retrato, f: Fontes, fps: float,
                   threads_vivas: int) -> None:
    """Modo debug (RF19): a concorrência por dentro, para a apresentação."""
    caixa = layout.DEBUG_RETANGULO
    fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
    fundo.fill(layout.DEBUG_FUNDO)
    sup.blit(fundo, caixa.topleft)
    na_fila = sum(1 for p in r.pedidos if p.estado is EstadoPedido.AGUARDANDO)
    linhas: list[tuple[str, Cor]] = [
        (f"DEBUG  fila {na_fila}/{r.tamanho_max_fila} · {fps:.0f} FPS · "
         f"{threads_vivas} threads vivas", layout.DESTAQUE),
        ("ordem fixa: TÁBUA > PIA > FOGÃO > BALCÃO", layout.TEXTO_FRACO),
    ]
    por_id = {c.id: c for c in r.cozinheiros}
    for g in r.grupos:
        dentro = [f"C{e.ocupada_por}" for e in r.estacoes
                  if e.tipo is g.tipo and e.ocupada_por is not None]
        espera = [f"C{cid} {por_id[cid].esperando_ha:.1f}s" if cid in por_id else f"C{cid}"
                  for cid in g.fila_espera]
        cor = layout.ALERTA if espera else layout.TEXTO
        texto = f"{NOMES[g.tipo]} [{len(dentro)}/{g.capacidade}]: {', '.join(dentro) or '-'}"
        if espera:
            texto += f"   espera: {', '.join(espera)}"
        linhas.append((texto, cor))
    for c in r.cozinheiros:
        segura = ", ".join(f"{NOMES[t]} {n + 1}" for t, n in c.segurando) or "-"
        espera = NOMES[c.esperando] if c.esperando is not None else "-"
        quem = "VOCÊ" if c.jogador else f"C{c.id}"
        linhas.append((f"{quem} {c.estado.name}: segura {segura} · espera {espera} · "
                       f"total {c.espera_total:.1f}s",
                       layout.ALERTA if c.esperando is not None else layout.TEXTO))
    y = caixa.y + 10
    for texto, cor in linhas:
        _texto(sup, f.pequena, texto, (caixa.x + 12, y), cor)
        y += layout.DEBUG_LINHA


def desenhar_confirmacao(sup: pygame.Surface, f: Fontes) -> None:
    desenhar_veu(sup)
    caixa = layout.CONFIRMACAO_RETANGULO
    pygame.draw.rect(sup, layout.PAINEL, caixa, border_radius=10)
    pygame.draw.rect(sup, layout.DESTAQUE, caixa, 2, border_radius=10)
    _texto(sup, f.grande, "Sair da partida?", (caixa.centerx, caixa.y + 45), centro=True)
    _texto(sup, f.media, "Enter = sim · Esc = não", (caixa.centerx, caixa.y + 100),
           layout.TEXTO_FRACO, centro=True)


# ---------- telas de início e resultado ----------

def desenhar_capa(sup: pygame.Surface, f: Fontes, titulo: str, cor: Cor = layout.TINTA) -> None:
    """Fundo de ladrilhos, um cartão de papel no meio, título e um chef desenhado."""
    sup.fill(layout.FUNDO)
    desenhar_piso(sup)
    cartao = layout.CAPA_CARTAO
    pygame.draw.rect(sup, layout.SOMBRA, cartao.move(6, 6), border_radius=16)
    pygame.draw.rect(sup, layout.PAPEL, cartao, border_radius=16)
    pygame.draw.rect(sup, layout.TINTA, cartao, 3, border_radius=16)
    _texto(sup, f.grande, titulo, (cartao.centerx, cartao.top + 60), cor, centro=True)
    chef = CozinheiroView(1, EstadoCozinheiro.LIVRE, None, None, 0.0, (), None, 0.0, 0.0)
    for dx in (-260, 260):
        desenhar_chef(sup, chef, (cartao.centerx + dx, cartao.top + 64), f)


def desenhar_tecla_legenda(sup: pygame.Surface, f: Fontes, tecla: str, texto: str,
                           pos: tuple[int, int]) -> None:
    largura = max(34, f.media.size(tecla)[0] + 16)
    caixa = pygame.Rect(pos[0], pos[1], largura, 30)
    pygame.draw.rect(sup, layout.BALAO, caixa, border_radius=6)
    pygame.draw.rect(sup, layout.TINTA, caixa, 2, border_radius=6)
    _texto(sup, f.media, tecla, caixa.center, layout.TINTA, centro=True)
    _texto(sup, f.media, texto, (pos[0] + 110, pos[1] + 6), layout.TINTA)


def desenhar_estrelas(sup: pygame.Surface, n: int, centro: tuple[int, int]) -> None:
    raio = layout.ESTRELA_RAIO
    for i in range(3):
        cx = centro[0] + (i - 1) * raio * 3
        pontos = [(cx + raio * (1 if k % 2 == 0 else 0.45) * math.cos(math.pi / 2 + k * math.pi / 5),
                   centro[1] - raio * (1 if k % 2 == 0 else 0.45) * math.sin(math.pi / 2 + k * math.pi / 5))
                  for k in range(10)]
        pygame.draw.polygon(sup, layout.BRILHO if i < n else layout.LIVRE, pontos)
        pygame.draw.polygon(sup, layout.TINTA, pontos, 2)
