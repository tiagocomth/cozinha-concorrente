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
HUD_ALTURA = 56
BARRA_PONTOS = pygame.Rect(420, 18, 320, 20)
BOLINHA_RAIO = 8
MAX_BOLINHAS = 10             # acima disso, perdidos vira texto

# Faixa de pedidos: uma linha para a fila, outra (mais baixa) para os em preparo
PEDIDOS_TITULO_Y = HUD_ALTURA + 8
CARTAO_Y = HUD_ALTURA + 34
CARTAO_TAMANHO = (190, 74)
CARTAO_PREPARO_Y = CARTAO_Y + 82
CARTAO_PREPARO_ALTURA = 44
CARTAO_ESPACO = 12
BARRA_PACIENCIA_ALTURA = 8

# Estações
ESTACOES_TITULO_Y = 240
ESTACOES_Y = 266
ESTACAO_TAMANHO = (120, 80)
ESTACAO_ESPACO = 16
GRUPO_ESPACO = 40
VAGA_TAMANHO = (40, 40)
VAGA_ESPACO = 8
ESPERA_DISTANCIA = 32          # entre um cozinheiro e o próximo na fila de espera
ESPERA_INICIO = 30             # da base da estação ao primeiro da fila

# Cozinheiros
COZINHEIRO_RAIO = 15
CONTORNO_SELECIONADO = 4
CONTORNO_COZINHEIRO = 3
ANEL_ESPERA = COZINHEIRO_RAIO + 8   # anel de alerta em volta de quem espera
DESCANSO_Y = 548
DESCANSO_X0 = 80
DESCANSO_ESPACO = 60
VELOCIDADE = 420.0             # pixels por segundo

# Painel inferior
PAINEL_Y = 580
PAINEL_LINHA = 26
PAINEL_COLUNA = 620

# Debug e confirmação
DEBUG_RETANGULO = pygame.Rect(940, 236, 330, 336)   # à direita do balcão
DEBUG_FUNDO = (10, 10, 14, 220)
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
    """Retângulo de cada cartão: os da fila numa linha (até `tamanho_max`), os em preparo
    numa linha mais baixa logo abaixo. O retrato traz até tamanho_max + n_cozinheiros pedidos."""
    largura, altura = CARTAO_TAMANHO
    na_fila = [p for p in pedidos if p.estado is EstadoPedido.AGUARDANDO][:tamanho_max]
    em_preparo = [p for p in pedidos if p.estado is not EstadoPedido.AGUARDANDO]
    cartoes = {p.id: pygame.Rect(MARGEM + i * (largura + CARTAO_ESPACO), CARTAO_Y, largura, altura)
               for i, p in enumerate(na_fila)}
    cartoes.update({p.id: pygame.Rect(MARGEM + i * (largura + CARTAO_ESPACO), CARTAO_PREPARO_Y,
                                      largura, CARTAO_PREPARO_ALTURA)
                    for i, p in enumerate(em_preparo)})
    return cartoes


@dataclass
class MapaEstacoes:
    """Onde cada estação fica na tela. O balcão é um retângulo só, com uma vaga por lugar."""
    estacoes: dict[tuple[TipoEstacao, int], pygame.Rect] = field(default_factory=dict)
    vagas: list[pygame.Rect] = field(default_factory=list)
    grupos: dict[TipoEstacao, pygame.Rect] = field(default_factory=dict)

    def estacao(self, tipo: TipoEstacao, indice: int) -> pygame.Rect:
        if tipo is TipoEstacao.BALCAO:
            return self.estacoes[(tipo, 0)]
        return self.estacoes[(tipo, indice)]

    def vaga(self, indice: int) -> pygame.Rect:
        return self.vagas[indice]

    def centro_de(self, tipo: TipoEstacao, indice: int) -> Ponto:
        r = self.vaga(indice) if tipo is TipoEstacao.BALCAO else self.estacao(tipo, indice)
        return float(r.centerx), float(r.centery)

    def posicao_espera(self, tipo: TipoEstacao, ordem: int) -> Ponto:
        g = self.grupos[tipo]
        return float(g.centerx), float(g.bottom + ESPERA_INICIO + ordem * ESPERA_DISTANCIA)


def mapa_estacoes(grupos: Sequence[GrupoView]) -> MapaEstacoes:
    """Posições a partir das capacidades (Config normal ou a da demo de deadlock)."""
    largura, altura = ESTACAO_TAMANHO
    vaga_l, vaga_a = VAGA_TAMANHO
    mapa = MapaEstacoes()
    x = MARGEM + 20
    for g in sorted(grupos, key=lambda g: g.tipo):
        if g.tipo is TipoEstacao.BALCAO:
            w = max(largura, g.capacidade * (vaga_l + VAGA_ESPACO) + VAGA_ESPACO)
            r = pygame.Rect(x, ESTACOES_Y, w, altura)
            mapa.estacoes[(g.tipo, 0)] = r
            mapa.vagas = [pygame.Rect(x + VAGA_ESPACO + i * (vaga_l + VAGA_ESPACO),
                                      ESTACOES_Y + altura - vaga_a - VAGA_ESPACO, vaga_l, vaga_a)
                          for i in range(g.capacidade)]
            mapa.grupos[g.tipo] = r
            x += w + GRUPO_ESPACO
            continue
        inicio = x
        for i in range(g.capacidade):
            mapa.estacoes[(g.tipo, i)] = pygame.Rect(x, ESTACOES_Y, largura, altura)
            x += largura + ESTACAO_ESPACO
        x -= ESTACAO_ESPACO
        mapa.grupos[g.tipo] = pygame.Rect(inicio, ESTACOES_Y, x - inicio, altura)
        x += GRUPO_ESPACO
    return mapa


def posicao_descanso(cozinheiro_id: int) -> Ponto:
    return float(DESCANSO_X0 + (cozinheiro_id - 1) * DESCANSO_ESPACO), float(DESCANSO_Y)
