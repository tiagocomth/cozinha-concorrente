"""Regras da partida: estados, vitória e derrota (spec 06).

Só a thread da interface (via Jogo) escreve no estado; as outras leem.
"""
from __future__ import annotations

import threading

from cozinha.config import Config
from cozinha.modelo.pontuacao import Pontuacao
from cozinha.modelo.relogio import Relogio
from cozinha.modelo.tipos import EstadoPartida

RODANDO, PAUSADA = EstadoPartida.RODANDO, EstadoPartida.PAUSADA


class Partida:
    def __init__(self, config: Config, relogio: Relogio, pontuacao: Pontuacao) -> None:
        self._config = config
        self._relogio = relogio
        self._pontuacao = pontuacao
        self._lock = threading.Lock()
        self._estado = EstadoPartida.PRONTA

    def _trocar(self, de: EstadoPartida, para: EstadoPartida) -> bool:
        with self._lock:
            if self._estado is not de:
                return False
            self._estado = para
            return True

    def iniciar(self) -> None:
        """PRONTA → RODANDO."""
        if self._trocar(EstadoPartida.PRONTA, RODANDO):
            self._relogio.iniciar()

    def pausar(self) -> None:
        """RODANDO → PAUSADA."""
        if self._trocar(RODANDO, PAUSADA):
            self._relogio.pausar()

    def retomar(self) -> None:
        """PAUSADA → RODANDO."""
        if self._trocar(PAUSADA, RODANDO):
            self._relogio.retomar()

    def verificar_fim(self) -> EstadoPartida:
        """Chamado 1x por quadro. Só age em RODANDO; perdidos têm prioridade sobre o tempo."""
        if self.estado is not RODANDO:
            return self.estado
        _, _, perdidos = self._pontuacao.valores()
        if perdidos < self._config.limite_perdidos and self.tempo_restante() > 0:
            return RODANDO
        # Nesta ordem: placar fecha, tempo congela, estado muda. Um lock de cada vez.
        self._pontuacao.fechar()
        self._relogio.congelar()
        # O resultado sai do placar já fechado: uma entrega que entrou entre a leitura
        # acima e o fechar() conta, e nada depois muda o que a tela mostra.
        pontos, _, perdidos = self._pontuacao.valores()
        if perdidos >= self._config.limite_perdidos:
            final = EstadoPartida.DERROTA                     # RF04
        elif pontos >= self._config.meta_pontos:
            final = EstadoPartida.VITORIA
        else:
            final = EstadoPartida.DERROTA
        with self._lock:
            self._estado = final
        return final

    def tempo_restante(self) -> float:
        return max(0.0, self._config.duracao_partida - self._relogio.agora())

    @property
    def estado(self) -> EstadoPartida:
        with self._lock:
            return self._estado

    @property
    def terminou(self) -> bool:
        return self.estado in (EstadoPartida.VITORIA, EstadoPartida.DERROTA)

    @property
    def meta_batida(self) -> bool:
        return self._pontuacao.valores()[0] >= self._config.meta_pontos
