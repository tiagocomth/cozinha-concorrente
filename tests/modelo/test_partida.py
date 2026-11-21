from __future__ import annotations

import pytest

from cozinha.config import Config
from cozinha.modelo.partida import Partida
from cozinha.modelo.pedido import Pedido
from cozinha.modelo.pontuacao import Pontuacao
from cozinha.modelo.receita import Etapa, Receita
from cozinha.modelo.relogio import Relogio
from cozinha.modelo.tipos import EstadoPartida, TipoEstacao

# Paciência enorme e bônus 0: cada entrega vale exatamente `pontos`.
def _receita(pontos: int) -> Receita:
    return Receita("teste", (Etapa("entregar", (TipoEstacao.BALCAO,), 0),), pontos, 1e9)


class Cenario:
    def __init__(self, fonte) -> None:
        self.fonte = fonte
        self.config = Config(duracao_partida=10, meta_pontos=50, limite_perdidos=2, bonus_maximo=0)
        self.relogio = Relogio(fonte)
        self.pontuacao = Pontuacao(self.config)
        self.partida = Partida(self.config, self.relogio, self.pontuacao)
        self._ids = 0

    def _novo(self, pontos: int = 10) -> Pedido:
        self._ids += 1
        return Pedido(self._ids, _receita(pontos), criado_em=0.0)

    def pontos(self, n: int) -> None:
        self.pontuacao.registrar_entrega(self._novo(n), self.relogio.agora())

    def perder(self, n: int) -> None:
        for _ in range(n):
            self.pontuacao.registrar_perda(self._novo())


@pytest.fixture
def c(fonte_falsa) -> Cenario:
    cen = Cenario(fonte_falsa)
    cen.partida.iniciar()
    return cen


def test_transicoes_invalidas(fonte_falsa):
    cen = Cenario(fonte_falsa)
    cen.partida.pausar()
    assert cen.partida.estado is EstadoPartida.PRONTA
    cen.partida.iniciar()
    fonte_falsa.avancar(3)
    cen.partida.iniciar()
    assert cen.partida.estado is EstadoPartida.RODANDO
    assert cen.partida.tempo_restante() == 7
    cen.partida.retomar()
    assert cen.partida.estado is EstadoPartida.RODANDO


def test_vitoria(c):
    c.pontos(50)
    c.fonte.avancar(10)
    assert c.partida.verificar_fim() is EstadoPartida.VITORIA
    assert c.partida.terminou


def test_derrota_por_pontos(c):
    c.pontos(49)
    c.fonte.avancar(10)
    assert c.partida.verificar_fim() is EstadoPartida.DERROTA


def test_derrota_por_perdidos(c):
    c.fonte.avancar(3)
    c.perder(2)
    assert c.partida.verificar_fim() is EstadoPartida.DERROTA
    assert c.partida.tempo_restante() == 7


def test_perdidos_tem_prioridade(c):
    c.pontos(60)
    c.perder(2)
    c.fonte.avancar(10)
    assert c.partida.verificar_fim() is EstadoPartida.DERROTA


def test_meta_batida_nao_encerra(c):
    c.pontos(60)
    c.fonte.avancar(5)
    assert c.partida.verificar_fim() is EstadoPartida.RODANDO
    assert c.partida.meta_batida is True
    assert not c.partida.terminou


def test_congela_no_fim(c):
    c.pontos(50)
    c.fonte.avancar(10)
    c.partida.verificar_fim()
    placar = c.pontuacao.valores()
    c.fonte.avancar(30)
    c.pontos(100)
    assert c.partida.tempo_restante() == 0
    assert c.pontuacao.valores() == placar
    assert c.partida.verificar_fim() is EstadoPartida.VITORIA


def test_derrota_antecipada_congela_tempo(c):
    c.fonte.avancar(4)
    c.perder(2)
    c.partida.verificar_fim()
    c.fonte.avancar(3)
    assert c.partida.tempo_restante() == 6


def test_pausa_preserva_tempo(c):
    c.fonte.avancar(2)
    c.partida.pausar()
    assert c.partida.estado is EstadoPartida.PAUSADA
    assert c.relogio.pausado
    c.fonte.avancar(100)
    assert c.partida.tempo_restante() == 8
    assert c.partida.verificar_fim() is EstadoPartida.PAUSADA
    c.partida.retomar()
    c.fonte.avancar(1)
    assert c.partida.tempo_restante() == 7


def test_tempo_restante_nunca_negativo(c):
    c.fonte.avancar(50)
    assert c.partida.tempo_restante() == 0
