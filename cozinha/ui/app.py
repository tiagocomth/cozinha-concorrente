"""Janela e loop principal (spec 08). Só esta thread chama o pygame (RC06)."""
from __future__ import annotations

import pygame

from cozinha.config import Config
from cozinha.ui import layout
from cozinha.ui.telas import SAIR, Tela, TelaInicio


def rodar(config: Config) -> None:
    pygame.init()
    pygame.display.set_caption("Cozinha Concorrente")
    superficie = pygame.display.set_mode(layout.JANELA)
    clock = pygame.time.Clock()
    atual: Tela = TelaInicio(config)
    veu = pygame.Surface(layout.JANELA)              # preto, para o fade entre telas
    fade = layout.FADE_SEGUNDOS
    try:
        while True:
            dt = clock.tick(config.fps) / 1000
            proxima = None
            for e in pygame.event.get():
                proxima = SAIR if e.type == pygame.QUIT else atual.evento(e)
                if proxima is not None:
                    break
            if proxima is None:
                atual.atualizar(dt)
                proxima = atual.proxima()          # ex.: a partida acabou → resultado
            if proxima is SAIR:
                break
            if proxima is not None:
                atual.fechar()
                atual = proxima
                fade = layout.FADE_SEGUNDOS           # a tela nova surge do escuro
                continue
            if hasattr(atual, "fps"):
                atual.fps = clock.get_fps()
            atual.desenhar(superficie)
            if fade > 0:
                veu.set_alpha(round(255 * fade / layout.FADE_SEGUNDOS))
                superficie.blit(veu, (0, 0))
                fade -= dt
            pygame.display.flip()
    finally:
        atual.fechar()                              # encerra as threads (RC07)
        pygame.quit()
