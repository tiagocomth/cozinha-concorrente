"""As telas do jogo (spec 08): início, partida e resultado.

Protocolo: `evento` e `proxima` devolvem None (continua), outra Tela, ou SAIR.
Só a thread principal chama estes métodos (RC06).
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Protocol

import pygame

from cozinha.config import NIVEIS, Config
from cozinha.jogo import Jogo
from cozinha.modelo.retrato import Retrato
from cozinha.modelo.tipos import EstadoCozinheiro, EstadoPartida
from cozinha.ui import desenho, entrada, layout
from cozinha.ui.animacao import Animacao, alvo, mover
from cozinha.ui.avatar import Avatar

log = logging.getLogger(__name__)
SAIR = object()   # sentinela: fechar o programa
ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER)
FIM = (EstadoPartida.VITORIA, EstadoPartida.DERROTA)

CONTROLES = (
    ("WASD", "anda pela cozinha"),
    ("E", "pega pedido no quadro / usa a estação"),
    ("Q", "sai da fila da estação / descarta o pedido"),
    ("P", "pausa"),
    ("D", "modo debug (as threads por dentro)"),
    ("Esc", "sai da partida"),
)
FRACOES_ESTRELA = (0.5, 0.8, 1.0)


def estrelas(pontos: int, meta: int) -> int:
    """0 a 3 estrelas pela fração da meta: 50 %, 80 % e a meta inteira."""
    fracao = pontos / meta if meta else 1.0
    return sum(1 for limite in FRACOES_ESTRELA if fracao >= limite)


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
        self.nivel = config.nivel or "Normal"
        self._fontes = layout.fontes()

    def _config_escolhida(self) -> Config:
        return Config.single_player(self.nivel) if self.config.jogador else self.config

    def evento(self, e: pygame.event.Event) -> Tela | object | None:
        if e.type != pygame.KEYDOWN:
            return None
        if e.key in ENTER:
            return TelaJogo(self._config_escolhida())
        if e.key == pygame.K_ESCAPE:
            return SAIR
        if self.config.jogador and e.key in (pygame.K_LEFT, pygame.K_RIGHT):
            passo = 1 if e.key == pygame.K_RIGHT else -1
            i = min(max(NIVEIS.index(self.nivel) + passo, 0), len(NIVEIS) - 1)
            self.nivel = NIVEIS[i]
        return None

    def proxima(self) -> None:
        return None

    def atualizar(self, dt: float) -> None:
        pass

    def desenhar(self, sup: pygame.Surface) -> None:
        f = self._fontes
        desenho.desenhar_capa(sup, f, "Cozinha Concorrente")
        c = self._config_escolhida()
        objetivo = (f"Faça {c.meta_pontos} pontos em {int(c.duracao_partida) // 60} minutos "
                    f"sem perder {c.limite_perdidos} clientes.")
        desenho._texto(sup, f.media, objetivo, _centro(232), layout.TINTA, centro=True)
        if c.jogador:
            desenho._texto(sup, f.media, "Você é o cozinheiro 1. Os outros disputam as mesmas "
                           "estações com você.", _centro(262), layout.TINTA_FRACA, centro=True)
            desenho.desenhar_seletor_nivel(sup, f, NIVEIS, self.nivel, _centro(305))
        for i, (tecla, texto) in enumerate(CONTROLES):
            desenho.desenhar_tecla_legenda(sup, f, tecla, texto, (470, 345 + i * 38))
        desenho._texto(sup, f.media, "Enter para começar · Esc para sair", _centro(604),
                       layout.TINTA, centro=True)

    def fechar(self) -> None:
        pass


class TelaJogo:
    def __init__(self, config: Config, jogo: Jogo | None = None,
                 teclas: Callable[[], entrada.Teclado] = pygame.key.get_pressed) -> None:
        self.config = config
        self.jogo = jogo if jogo is not None else Jogo(config)
        self.jogo.iniciar()
        self.fps = 0.0                      # o rodar atualiza com clock.get_fps()
        self._teclas = teclas
        self._fontes = layout.fontes()
        self._animacao = Animacao()
        self._retrato: Retrato = self.jogo.retrato()
        self._animacao.atualizar(self._retrato, 0.0)
        self.mapa = layout.mapa_estacoes(self._retrato.grupos)   # capacidades não mudam
        self.avatar: Avatar | None = Avatar(layout.INICIO_JOGADOR) if config.jogador else None
        self._fechada = False
        self.debug = False
        self.confirmando = False            # caixa "Sair da partida?" aberta
        self._pausada_antes = False         # estava pausada (P) antes de abrir a caixa
        self._t = 0.0                       # relógio da animação (brilho pulsando)
        self.aviso = ""                     # mensagem curta na linha de dica
        self._aviso_ate = 0.0
        self._ultima_mensagem: str | None = None

    # ---------- eventos ----------

    def _avisar(self, texto: str) -> None:
        self.aviso = texto
        self._aviso_ate = self._t + layout.AVISO_SEGUNDOS

    def _perto(self):
        return self.avatar.perto(self.mapa) if self.avatar is not None else None

    def evento(self, e: pygame.event.Event) -> Tela | object | None:
        if e.type == pygame.WINDOWFOCUSLOST:
            self.jogo.pausar()              # retomar é com P: o foco voltar não retoma
            return None
        if self.confirmando:
            return self._evento_confirmacao(e)
        # O retrato desenhado, não um novo: o clique vale para a comanda que o jogador viu.
        r = self._retrato
        acao = entrada.traduzir(e, layout.cartoes_pedidos(r.pedidos, r.tamanho_max_fila))
        match acao:
            case entrada.Interagir() if self.avatar is not None:
                perto = self._perto()
                if perto == "quadro":
                    self.jogo.pegar_pedido()
                elif perto is not None:
                    self.jogo.usar_estacao(perto)
                else:
                    self._avisar("Chegue perto de uma estação ou do quadro de pedidos")
            case entrada.Desistir():
                self.jogo.desistir()
            case entrada.ClicarComanda(pedido_id=pid) if self.avatar is not None:
                if self._perto() == "quadro":
                    self.jogo.pegar_pedido(pid)
                else:
                    self._avisar("Vá até o quadro de PEDIDOS para pegar uma comanda")
            case entrada.AlternarPausa():
                self._alternar_pausa()
            case entrada.AlternarDebug():
                self.debug = not self.debug
            case entrada.PedirSaida():
                self._pausada_antes = self.jogo.retrato().estado is EstadoPartida.PAUSADA
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
        self._retrato = r = self.jogo.retrato()      # um retrato por quadro (RC06)
        self._animacao.atualizar(r, dt)
        self._t += dt
        if self.avatar is None or r.estado is not EstadoPartida.RODANDO:
            return
        eu = r.cozinheiros[0]
        if eu.mensagem and eu.mensagem != self._ultima_mensagem:
            self._ultima_mensagem = eu.mensagem
            self._avisar(eu.mensagem)
        if eu.estado in (EstadoCozinheiro.ESPERANDO, EstadoCozinheiro.TRABALHANDO):
            # Ocupado numa estação (ou na fila dela): o avatar vai até lá e não obedece às teclas.
            self.avatar.pos = mover(self.avatar.pos, alvo(eu, r, self.mapa),
                                    layout.VELOCIDADE_JOGADOR, dt)
        else:
            self.avatar.andar(entrada.direcao(self._teclas()), dt, self.mapa)

    def desenhar(self, sup: pygame.Surface) -> None:
        r = self._retrato
        aviso = self.aviso if self._t < self._aviso_ate else None
        desenho.desenhar_retrato(sup, r, self._animacao.posicoes, self._fontes,
                                 jogador_pos=self.avatar.pos if self.avatar else None,
                                 perto=self._perto(), t=self._t, dica=aviso)
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
        vitoria = r.estado is EstadoPartida.VITORIA
        desenho.desenhar_capa(sup, f, "VITÓRIA!" if vitoria else "DERROTA",
                              layout.META if vitoria else layout.ALERTA)
        desenho.desenhar_estrelas(sup, estrelas(r.pontos, r.meta), _centro(260))
        linhas = (f"Pontos: {r.pontos} / {r.meta}", f"Pratos entregues: {r.entregues}",
                  f"Clientes perdidos: {r.perdidos} / {r.limite_perdidos}")
        for i, linha in enumerate(linhas):
            desenho._texto(sup, f.media, linha, _centro(340 + i * 36), layout.TINTA, centro=True)
        desenho._texto(sup, f.media, "Enter para jogar de novo · Esc para sair do jogo",
                       _centro(560), layout.TINTA, centro=True)

    def fechar(self) -> None:
        pass
