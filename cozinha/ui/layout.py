"""Tamanhos, posições, cores e fontes da interface. Nenhum número solto fora daqui."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import NamedTuple

import pygame

from cozinha.modelo.retrato import GrupoView, PedidoView
from cozinha.modelo.tipos import EstadoPedido, TipoEstacao

Cor = tuple[int, int, int]
Ponto = tuple[float, float]

JANELA = (1280, 720)
MARGEM = 20

# Cores
FUNDO: Cor = (30, 32, 38)
PAINEL: Cor = (44, 47, 56)
TEXTO: Cor = (235, 235, 235)
TEXTO_FRACO: Cor = (150, 152, 160)
LIVRE: Cor = (90, 93, 102)
ALERTA: Cor = (255, 90, 70)
DESTAQUE: Cor = (255, 215, 90)
META: Cor = (110, 200, 120)
PACIENCIA_ALTA: Cor = (90, 200, 110)
PACIENCIA_MEDIA: Cor = (240, 200, 70)
PACIENCIA_BAIXA: Cor = (235, 80, 70)
LIMIAR_PACIENCIA_MEDIA = 0.5
LIMIAR_PACIENCIA_BAIXA = 0.25
VEU = (0, 0, 0, 160)
CORES_COZINHEIROS: tuple[Cor, ...] = (
    (80, 160, 255), (255, 140, 60), (180, 110, 255), (60, 210, 190), (255, 105, 180),
)

# HUD
HUD_ALTURA = 52
BARRA_PONTOS = pygame.Rect(420, 16, 320, 20)
BOLINHA_RAIO = 8
MAX_BOLINHAS = 10             # acima disso, perdidos vira texto

# Comandas: uma linha para a fila; os em preparo numa linha de etiquetas logo abaixo
CARTAO_Y = HUD_ALTURA + 6
CARTAO_TAMANHO = (176, 84)
CARTAO_ESPACO = 10
CARTAO_PREPARO_Y = CARTAO_Y + CARTAO_TAMANHO[1] + 6
CARTAO_PREPARO_TAMANHO = (150, 26)
BARRA_PACIENCIA_ALTURA = 8
ICONE_ETAPA = 20              # quadradinho de cada etapa na comanda
PEDIDOS_TITULO_Y = CARTAO_PREPARO_Y      # legado: o título da fila sai das comandas

# A cozinha, vista de cima
COZINHA = pygame.Rect(16, 176, 1248, 504)
PAREDE = 12
PISO = COZINHA.inflate(-2 * PAREDE, -2 * PAREDE)
DICA_Y = COZINHA.bottom + 6

# Estações: as de bancada na parede de cima; o balcão na parede direita; o quadro na esquerda
ESTACAO_TAMANHO = (112, 72)
ESTACOES_X0 = 180
ESTACAO_ESPACO = 18
GRUPO_ESPACO = 46
BALCAO_LARGURA = 84
BALCAO_Y = 300
VAGA_TAMANHO = (44, 44)
VAGA_ESPACO = 14
QUADRO = pygame.Rect(PISO.left, 300, 70, 130)
AREA_INTERACAO = 56           # faixa em frente a cada estação onde o E funciona
FRENTE = 24                   # onde o cozinheiro fica para usar a estação
ESPERA_INICIO = 70            # da estação ao primeiro da fila de espera
ESPERA_DISTANCIA = 34

# Cozinheiros
COZINHEIRO_RAIO = 16
JOGADOR_RAIO = 19
CONTORNO_SELECIONADO = 4
CONTORNO_COZINHEIRO = 3
ANEL_ESPERA = COZINHEIRO_RAIO + 8   # anel de alerta em volta de quem espera
DESCANSO_X0 = 300
DESCANSO_ESPACO = 64
DESCANSO_Y = PISO.bottom - 40
VELOCIDADE = 420.0            # cozinheiros automáticos deslizando (pixels/s)
VELOCIDADE_JOGADOR = 260.0
INICIO_JOGADOR: tuple[float, float] = (560.0, 520.0)

# Debug e confirmação
DEBUG_RETANGULO = pygame.Rect(470, 330, 600, 300)
DEBUG_FUNDO = (10, 10, 14, 215)
DEBUG_LINHA = 20
CONFIRMACAO_RETANGULO = pygame.Rect(390, 290, 500, 140)

FONTE_TAMANHOS = (20, 26, 52)
NOMES_ESTACAO = {TipoEstacao.TABUA: "TÁBUA", TipoEstacao.PIA: "PIA",
                 TipoEstacao.FOGAO: "FOGÃO", TipoEstacao.BALCAO: "BALCÃO"}


class Fontes(NamedTuple):
    pequena: pygame.font.Font
    media: pygame.font.Font
    grande: pygame.font.Font


def fontes() -> Fontes:
    """Cria as fontes (a padrão do pygame). Chame uma vez por tela, não a cada quadro."""
    if not pygame.font.get_init():
        pygame.font.init()
    return Fontes(*(pygame.font.Font(None, t) for t in FONTE_TAMANHOS))


def cor_cozinheiro(cozinheiro_id: int) -> Cor:
    return CORES_COZINHEIROS[(cozinheiro_id - 1) % len(CORES_COZINHEIROS)]


def cartoes_pedidos(pedidos: Sequence[PedidoView], tamanho_max: int) -> dict[int, pygame.Rect]:
    """Comandas da fila numa linha (até `tamanho_max`); os em preparo como etiquetas abaixo.
    O retrato traz até tamanho_max + n_cozinheiros pedidos: todos aparecem."""
    largura, altura = CARTAO_TAMANHO
    na_fila = [p for p in pedidos if p.estado is EstadoPedido.AGUARDANDO][:tamanho_max]
    em_preparo = [p for p in pedidos if p.estado is not EstadoPedido.AGUARDANDO]
    cartoes = {p.id: pygame.Rect(MARGEM + i * (largura + CARTAO_ESPACO), CARTAO_Y, largura, altura)
               for i, p in enumerate(na_fila)}
    pl, pa = CARTAO_PREPARO_TAMANHO
    cartoes.update({p.id: pygame.Rect(MARGEM + i * (pl + CARTAO_ESPACO), CARTAO_PREPARO_Y, pl, pa)
                    for i, p in enumerate(em_preparo)})
    return cartoes


Alvo = TipoEstacao | str     # "quadro" é o quadro de pedidos


@dataclass
class MapaEstacoes:
    """Onde cada coisa fica na cozinha. O balcão é um móvel só, com uma vaga por lugar."""
    estacoes: dict[tuple[TipoEstacao, int], pygame.Rect] = field(default_factory=dict)
    vagas: list[pygame.Rect] = field(default_factory=list)
    grupos: dict[TipoEstacao, pygame.Rect] = field(default_factory=dict)
    areas_interacao: dict[Alvo, list[pygame.Rect]] = field(default_factory=dict)
    obstaculos: list[pygame.Rect] = field(default_factory=list)

    def estacao(self, tipo: TipoEstacao, indice: int) -> pygame.Rect:
        if tipo is TipoEstacao.BALCAO:
            return self.estacoes[(tipo, 0)]
        return self.estacoes[(tipo, indice)]

    def vaga(self, indice: int) -> pygame.Rect:
        return self.vagas[indice]

    def centro_de(self, tipo: TipoEstacao, indice: int) -> Ponto:
        """Onde o cozinheiro fica para usar a estação (na frente dela)."""
        if tipo is TipoEstacao.BALCAO:
            v, b = self.vaga(indice), self.estacao(tipo, 0)
            return float(b.left - FRENTE), float(v.centery)
        r = self.estacao(tipo, indice)
        return float(r.centerx), float(r.bottom + FRENTE)

    def posicao_espera(self, tipo: TipoEstacao, ordem: int) -> Ponto:
        g = self.grupos[tipo]
        if tipo is TipoEstacao.BALCAO:
            return float(g.left - ESPERA_INICIO - ordem * ESPERA_DISTANCIA), float(g.centery)
        return float(g.centerx), float(g.bottom + ESPERA_INICIO + ordem * ESPERA_DISTANCIA)


def mapa_estacoes(grupos: Sequence[GrupoView]) -> MapaEstacoes:
    """Posições a partir das capacidades (Config normal ou a da demo de deadlock)."""
    largura, altura = ESTACAO_TAMANHO
    vaga_l, vaga_a = VAGA_TAMANHO
    mapa = MapaEstacoes()
    x = ESTACOES_X0
    for g in sorted(grupos, key=lambda g: g.tipo):
        if g.tipo is TipoEstacao.BALCAO:
            h = g.capacidade * (vaga_a + VAGA_ESPACO) + VAGA_ESPACO
            r = pygame.Rect(PISO.right - BALCAO_LARGURA, BALCAO_Y, BALCAO_LARGURA, h)
            mapa.estacoes[(g.tipo, 0)] = r
            mapa.grupos[g.tipo] = r
            mapa.vagas = [pygame.Rect(r.centerx - vaga_l // 2,
                                      r.top + VAGA_ESPACO + i * (vaga_a + VAGA_ESPACO), vaga_l, vaga_a)
                          for i in range(g.capacidade)]
            mapa.areas_interacao[g.tipo] = [pygame.Rect(r.left - AREA_INTERACAO, r.top,
                                                        AREA_INTERACAO, r.height)]
            mapa.obstaculos.append(r)
            continue
        inicio = x
        areas = []
        for i in range(g.capacidade):
            r = pygame.Rect(x, PISO.top, largura, altura)
            mapa.estacoes[(g.tipo, i)] = r
            mapa.obstaculos.append(r)
            areas.append(pygame.Rect(r.left, r.bottom, r.width, AREA_INTERACAO))
            x += largura + ESTACAO_ESPACO
        x -= ESTACAO_ESPACO
        mapa.grupos[g.tipo] = pygame.Rect(inicio, PISO.top, x - inicio, altura)
        mapa.areas_interacao[g.tipo] = areas
        x += GRUPO_ESPACO
    mapa.obstaculos.append(QUADRO)
    mapa.areas_interacao["quadro"] = [pygame.Rect(QUADRO.right, QUADRO.top,
                                                  AREA_INTERACAO, QUADRO.height)]
    return mapa


def posicao_descanso(cozinheiro_id: int) -> Ponto:
    return float(DESCANSO_X0 + (cozinheiro_id - 1) * DESCANSO_ESPACO), float(DESCANSO_Y)
