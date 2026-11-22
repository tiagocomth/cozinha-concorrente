"""As telas do jogo (spec 08): início, partida e resultado.

Protocolo: `evento` e `proxima` devolvem None (continua), outra Tela, ou SAIR.
Só a thread principal chama estes métodos (RC06).
"""
from __future__ import annotations

import logging
import threading
from typing import Protocol

import pygame

from cozinha.config import Config
from cozinha.jogo import Jogo
from cozinha.modelo.retrato import Retrato
from cozinha.modelo.tipos import EstadoPartida
from cozinha.ui import desenho, entrada, layout
from cozinha.ui.animacao import Animacao

log = logging.getLogger(__name__)
SAIR = object()   # sentinela: fechar o programa
ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER)
FIM = (EstadoPartida.VITORIA, EstadoPartida.DERROTA)

CONTROLES = (
    "1-4  seleciona o cozinheiro",
    "clique num pedido (ou setas + Enter)  manda o selecionado fazer",
    "P  pausa · D  modo debug · Esc  sair da partida",
)


class Tela(Protocol):
    def evento(self, e: pygame.event.Event) -> Tela | object | None: ...
    def proxima(self) -> Tela | object | None: ...
    def atualizar(self, dt: float) -> None: ...
    def desenhar(self, superficie: pygame.Surface) -> None: ...
    def fechar(self) -> None: ...


def _centro(y: int) -> tuple[int, int]:
    return layout.JANELA[0] // 2, y


class TelaInicio:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._fontes = layout.fontes()

    def evento(self, e: pygame.event.Event) -> Tela | object | None:
        if e.type == pygame.KEYDOWN and e.key in ENTER:
            return TelaJogo(self.config)
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            return SAIR
        return None

    def proxima(self) -> None:
        return None

    def atualizar(self, dt: float) -> None:
        pass

    def desenhar(self, sup: pygame.Surface) -> None:
        f = self._fontes
        sup.fill(layout.FUNDO)
        desenho._texto(sup, f.grande, "Cozinha Concorrente", _centro(160), centro=True)
        desenho._texto(sup, f.media,
                       f"Faça {self.config.meta_pontos} pontos antes do tempo acabar, "
                       f"sem perder {self.config.limite_perdidos} clientes.",
                       _centro(230), centro=True)
        for i, linha in enumerate(CONTROLES):
            desenho._texto(sup, f.media, linha, _centro(320 + i * 36), layout.TEXTO_FRACO,
                           centro=True)
        desenho._texto(sup, f.media, "Enter para começar · Esc para sair", _centro(520),
                       layout.DESTAQUE, centro=True)

    def fechar(self) -> None:
        pass


class TelaJogo:
    def __init__(self, config: Config, jogo: Jogo | None = None) -> None:
        self.config = config
        self.jogo = jogo if jogo is not None else Jogo(config)
        self.jogo.iniciar()
        self.fps = 0.0                      # o rodar atualiza com clock.get_fps()
        self._fontes = layout.fontes()
        self._animacao = Animacao()
        self._retrato: Retrato = self.jogo.retrato()
        self._animacao.atualizar(self._retrato, 0.0)
        self._fechada = False
        self.debug = False
        self.confirmando = False            # caixa "Sair da partida?" aberta
        self._pausada_antes = False         # estava pausada (P) antes de abrir a caixa
        self.cursor: int | None = None      # pedido_id escolhido pelas setas

    # ---------- eventos ----------

    def evento(self, e: pygame.event.Event) -> Tela | object | None:
        if e.type == pygame.WINDOWFOCUSLOST:
            self.jogo.pausar()              # retomar é com P: o foco voltar não retoma
            return None
        if self.confirmando:
            return self._evento_confirmacao(e)
        r = self.jogo.retrato()
        cartoes = layout.cartoes_pedidos(r.pedidos, r.tamanho_max_fila)
        acao, self.cursor = entrada.traduzir(e, r, self.cursor, cartoes)
        match acao:
            case entrada.Selecionar(cozinheiro_id=cid):
                self.jogo.selecionar(cid)
            case entrada.Atribuir(pedido_id=pid):
                self.jogo.atribuir(pid)
            case entrada.AlternarPausa():
                self._alternar_pausa()
            case entrada.AlternarDebug():
                self.debug = not self.debug
            case entrada.PedirSaida():
                self._pausada_antes = r.estado is EstadoPartida.PAUSADA
                self.jogo.pausar()
                self.confirmando = True
        return None

    def _evento_confirmacao(self, e: pygame.event.Event) -> Tela | object | None:
        """Com a caixa aberta, só Enter (sai) e Esc (volta) contam."""
        if e.type != pygame.KEYDOWN:
            return None
        if e.key in ENTER:
            self.fechar()
            return TelaInicio(self.config)
        if e.key == pygame.K_ESCAPE:
            self.confirmando = False
            if not self._pausada_antes:
                self.jogo.retomar()
        return None

    def _alternar_pausa(self) -> None:
        if self.jogo.retrato().estado is EstadoPartida.PAUSADA:
            self.jogo.retomar()
        else:
            self.jogo.pausar()

    def proxima(self) -> Tela | object | None:
        if self._retrato.estado in FIM:
            return TelaResultado(self.config, self._retrato)
        return None

    # ---------- quadro ----------

    def atualizar(self, dt: float) -> None:
        # Um RuntimeError aqui (thread morreu) sobe até o rodar, que encerra tudo (spec 07).
        self.jogo.atualizar()
        self._retrato = self.jogo.retrato()          # um retrato por quadro (RC06)
        self._animacao.atualizar(self._retrato, dt)

    def desenhar(self, sup: pygame.Surface) -> None:
        r = self._retrato
        desenho.desenhar_retrato(sup, r, self._animacao.posicoes, self._fontes, self.cursor)
        if self.debug:
            desenho.desenhar_debug(sup, r, self._fontes, self.fps, threading.active_count())
        if self.confirmando:
            desenho.desenhar_confirmacao(sup, self._fontes)
        elif r.estado is EstadoPartida.PAUSADA:
            desenho.desenhar_pausa(sup, self._fontes)

    def fechar(self) -> None:
        presas = self.jogo.encerrar()
        if presas and not self._fechada:
            log.warning("threads que não terminaram ao fechar a partida: %s", presas)
        self._fechada = True


class TelaResultado:
    def __init__(self, config: Config, retrato: Retrato) -> None:
        self.config = config
        self.retrato = retrato
        self._fontes = layout.fontes()

    def evento(self, e: pygame.event.Event) -> Tela | object | None:
        if e.type == pygame.KEYDOWN and e.key in ENTER:
            return TelaJogo(self.config)            # jogar de novo: Jogo novo
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            return SAIR
        return None

    def proxima(self) -> None:
        return None

    def atualizar(self, dt: float) -> None:
        pass

    def desenhar(self, sup: pygame.Surface) -> None:
        f, r = self._fontes, self.retrato
        sup.fill(layout.FUNDO)
        vitoria = r.estado is EstadoPartida.VITORIA
        desenho._texto(sup, f.grande, "VITÓRIA" if vitoria else "DERROTA", _centro(170),
                       layout.META if vitoria else layout.ALERTA, centro=True)
        linhas = (f"Pontos: {r.pontos} / {r.meta}", f"Pratos entregues: {r.entregues}",
                  f"Clientes perdidos: {r.perdidos} / {r.limite_perdidos}")
        for i, linha in enumerate(linhas):
            desenho._texto(sup, f.media, linha, _centro(260 + i * 40), centro=True)
        desenho._texto(sup, f.media, "Enter para jogar de novo · Esc para sair do jogo",
                       _centro(480), layout.DESTAQUE, centro=True)

    def fechar(self) -> None:
        pass
