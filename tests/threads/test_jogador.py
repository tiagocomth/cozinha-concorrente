from __future__ import annotations

import itertools
import threading
import time
from dataclasses import replace

import pytest

from cozinha.config import Config
from cozinha.modelo.estacoes import Cozinha
from cozinha.modelo.fila import FilaDePedidos
from cozinha.modelo.pedido import Pedido
from cozinha.modelo.pontuacao import Pontuacao
from cozinha.modelo.receita import Etapa, Receita
from cozinha.modelo.relogio import Relogio
from cozinha.modelo.tipos import EstadoCozinheiro, EstadoPedido, TipoEstacao
from cozinha.threads.cozinheiro import Cozinheiro
from cozinha.threads.jogador import CozinheiroJogador, Desistir, PegarPedido, UsarEstacao

TABUA, PIA, FOGAO, BALCAO = TipoEstacao
NUNCA = lambda: False  # noqa: E731
DUR = 0.05


def salada(paciencia: float = 60) -> Receita:
    return Receita("Salada", (Etapa("cortar", (TABUA,), DUR), Etapa("entregar", (BALCAO,), DUR)),
                   20, paciencia)


def sopa() -> Receita:
    return Receita("Sopa", (Etapa("cortar", (TABUA,), DUR), Etapa("cozinhar", (FOGAO,), DUR),
                            Etapa("empratar", (FOGAO, BALCAO), DUR)), 35, 60)


def esperar(cond, prazo: float = 2.0) -> None:
    fim = time.monotonic() + prazo
    while not cond():
        assert time.monotonic() < fim, "condição não ficou verdadeira a tempo"
        time.sleep(0.003)


class M:
    def __init__(self, **cfg) -> None:
        base = {"tick": 0.005, "tempo_retirada": 0,
                "quantidade": {TABUA: 1, PIA: 1, FOGAO: 1, BALCAO: 1}}
        self.config = replace(Config(), **{**base, **cfg})
        self.relogio = Relogio()
        self.relogio.iniciar()
        self.pontuacao = Pontuacao(self.config)
        self.cozinha = Cozinha(self.config)
        self.fila = FilaDePedidos(self.config.tamanho_max_fila)
        self.parar = threading.Event()
        self._ids = itertools.count(1)
        self.j = CozinheiroJogador(1, self.fila, self.cozinha, self.pontuacao, self.relogio,
                                   self.config, self.parar)
        self.outros: list[Cozinheiro] = []

    def pedir(self, receita: Receita) -> Pedido:
        return self.fila.colocar(lambda: Pedido(next(self._ids), receita, self.relogio.agora()), 0.1)

    def ocupadas(self) -> dict:
        return {(e.tipo, e.indice): e.ocupada_por
                for e in self.cozinha.views()[0] if e.ocupada_por is not None}

    def grupo(self, tipo):
        return next(g for g in self.cozinha.views()[1] if g.tipo is tipo)

    def fazer(self, tipo) -> None:
        """Manda usar a estação e espera a etapa terminar (o índice da etapa avançar)."""
        antes = self.j.view().proxima
        self.j.comandar(UsarEstacao(tipo))
        esperar(lambda: self.j.view().estado is EstadoCozinheiro.LIVRE
                and self.j.view().proxima != antes)

    def encerrar(self) -> None:
        self.parar.set()
        self.relogio.congelar()
        for c in [self.j, *self.outros]:
            if c.ident is not None:
                c.join(timeout=1)
                assert not c.is_alive()


@pytest.fixture
def m():
    criadas: list[M] = []

    def f(**cfg) -> M:
        x = M(**cfg)
        criadas.append(x)
        return x

    yield f
    for x in criadas:
        x.encerrar()


def test_parado_sem_comando(m):
    x = m()
    x.pedir(salada())
    x.j.start()
    time.sleep(0.2)
    assert len(x.fila) == 1
    assert x.j.view().jogador is True


def test_pegar_e_fazer_salada(m):
    x = m()
    p = x.pedir(salada())
    x.j.start()
    x.j.comandar(PegarPedido())
    esperar(lambda: x.j.view().pedido_id == p.id)
    x.fazer(TABUA)
    x.j.comandar(UsarEstacao(BALCAO))
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)
    assert x.pontuacao.valores()[0] > 0
    esperar(lambda: x.j.view().pedido_id is None)
    assert x.ocupadas() == {}


def test_estacao_errada(m):
    x = m()
    x.pedir(salada())
    x.j.start()
    x.j.comandar(PegarPedido())
    esperar(lambda: x.j.view().pedido_id is not None)
    x.j.comandar(UsarEstacao(FOGAO))
    esperar(lambda: "TÁBUA" in (x.j.view().mensagem or ""))
    assert x.ocupadas() == {}


def test_empratar_pega_as_duas(m):
    x = m()
    p = x.pedir(sopa())
    x.j.start()
    x.j.comandar(PegarPedido())
    esperar(lambda: x.j.view().pedido_id == p.id)
    x.fazer(TABUA)
    x.fazer(FOGAO)
    assert x.j.view().proxima == (FOGAO, BALCAO)
    x.j.comandar(UsarEstacao(BALCAO))
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)


def test_proxima(m):
    x = m()
    x.pedir(salada())
    x.j.start()
    assert x.j.view().proxima == ()
    x.j.comandar(PegarPedido())
    esperar(lambda: x.j.view().proxima == (TABUA,))
    x.fazer(TABUA)
    assert x.j.view().proxima == (BALCAO,)


def test_espera_e_desiste(m):
    x = m()
    p = x.pedir(salada())
    x.cozinha.ocupar_todas(99, (TABUA,), NUNCA)
    x.j.start()
    x.j.comandar(PegarPedido())
    esperar(lambda: x.j.view().pedido_id == p.id)
    x.j.comandar(UsarEstacao(TABUA))
    esperar(lambda: x.j.view().estado is EstadoCozinheiro.ESPERANDO)
    assert x.grupo(TABUA).fila_espera == (1,)
    x.j.comandar(Desistir())
    esperar(lambda: x.grupo(TABUA).fila_espera == ())
    esperar(lambda: x.j.view().estado is EstadoCozinheiro.LIVRE)
    assert x.j.view().pedido_id == p.id
    assert x.pontuacao.valores()[2] == 0
    assert p.estado is EstadoPedido.EM_PREPARO


def test_descartar(m):
    x = m()
    p = x.pedir(salada())
    x.j.start()
    x.j.comandar(PegarPedido())
    esperar(lambda: x.j.view().pedido_id == p.id)
    x.j.comandar(Desistir())
    esperar(lambda: p.estado is EstadoPedido.PERDIDO)
    assert x.pontuacao.valores()[2] == 1
    esperar(lambda: x.j.view().pedido_id is None)


def test_pedido_ja_saiu(m):
    x = m()
    x.pedir(salada())
    x.j.start()
    x.j.comandar(PegarPedido(99))
    esperar(lambda: "já saiu" in (x.j.view().mensagem or ""))
    outro = Cozinheiro(2, x.fila, x.cozinha, x.pontuacao, x.relogio, x.config, x.parar)
    x.outros.append(outro)
    outro.start()
    esperar(lambda: x.pontuacao.valores()[1] == 1)


def test_expira_na_mao(m):
    x = m()
    p = x.pedir(salada(paciencia=0.2))
    x.j.start()
    x.j.comandar(PegarPedido())
    esperar(lambda: x.j.view().pedido_id == p.id)
    esperar(lambda: p.estado is EstadoPedido.PERDIDO, prazo=1)
    assert x.pontuacao.valores()[2] == 1
    esperar(lambda: x.j.view().pedido_id is None)
    assert x.j.view().mensagem


def test_comando_na_pausa(m):
    x = m()
    p = x.pedir(salada())
    x.relogio.pausar()
    x.j.start()
    x.j.comandar(PegarPedido())
    time.sleep(0.2)
    assert x.j.view().pedido_id is None
    x.relogio.retomar()
    esperar(lambda: x.j.view().pedido_id == p.id)


def test_parar_com_pedido_e_esperando(m):
    x = m()
    x.pedir(salada())
    x.cozinha.ocupar_todas(99, (TABUA,), NUNCA)
    x.j.start()
    x.j.comandar(PegarPedido())
    x.j.comandar(UsarEstacao(TABUA))
    esperar(lambda: x.j.view().estado is EstadoCozinheiro.ESPERANDO)
    x.parar.set()
    x.j.join(timeout=1)
    assert not x.j.is_alive()
    assert x.ocupadas() == {(TABUA, 0): 99}
    assert x.j.erro is None


def test_automatico_nao_pega_o_do_jogador(m):
    x = m()
    p1, p2 = x.pedir(salada()), x.pedir(salada())
    x.j.start()
    x.j.comandar(PegarPedido(p1.id))
    esperar(lambda: x.j.view().pedido_id == p1.id)
    outro = Cozinheiro(2, x.fila, x.cozinha, x.pontuacao, x.relogio, x.config, x.parar)
    x.outros.append(outro)
    outro.start()
    esperar(lambda: p2.estado is EstadoPedido.ENTREGUE)
    assert p1.cozinheiro_id == 1 and p1.estado is EstadoPedido.EM_PREPARO


def test_pedido_view_etapa_atual(m):
    x = m()
    p = x.pedir(sopa())
    x.j.start()
    x.j.comandar(PegarPedido())
    esperar(lambda: x.j.view().pedido_id == p.id)
    assert x.j.pedido_view(x.relogio.agora()).etapa_atual == 0
    x.fazer(TABUA)
    v = x.j.pedido_view(x.relogio.agora())
    assert v.etapa_atual == 1 and len(v.etapas) == 3
