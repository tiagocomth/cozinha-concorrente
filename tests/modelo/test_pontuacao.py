from __future__ import annotations

import threading

import pytest

from cozinha.config import Config
from cozinha.modelo.pedido import Pedido
from cozinha.modelo.pontuacao import Pontuacao
from cozinha.modelo.receita import Etapa, Receita
from cozinha.modelo.tipos import EstadoPedido, TipoEstacao

RECEITA = Receita("teste", (Etapa("entregar", (TipoEstacao.BALCAO,), 0),), 20, 10)


def _pedido(i: int = 1) -> Pedido:
    return Pedido(i, RECEITA, criado_em=0.0)


@pytest.fixture
def pont() -> Pontuacao:
    return Pontuacao(Config(bonus_maximo=15))


def test_bonus(pont):
    a, b = _pedido(1), _pedido(2)
    assert pont.registrar_entrega(a, 0.0) == 35
    assert pont.registrar_entrega(b, 10.0) == 20
    assert pont.valores() == (55, 2, 0)
    assert a.estado is b.estado is EstadoPedido.ENTREGUE


def test_perda(pont):
    p = _pedido()
    pont.registrar_perda(p)
    assert p.estado is EstadoPedido.PERDIDO
    assert pont.valores() == (0, 0, 1)


def test_duplicado(pont):
    p = _pedido()
    pont.registrar_entrega(p, 0.0)
    with pytest.raises(ValueError):
        pont.registrar_entrega(p, 0.0)
    assert pont.valores() == (35, 1, 0)


def test_perda_depois_de_entrega(pont):
    p = _pedido(1)
    pont.registrar_entrega(p, 0.0)
    with pytest.raises(ValueError):
        pont.registrar_perda(p)
    assert p.estado is EstadoPedido.ENTREGUE
    q = _pedido(2)
    pont.registrar_perda(q)
    with pytest.raises(ValueError):
        pont.registrar_entrega(q, 0.0)
    assert q.estado is EstadoPedido.PERDIDO
    assert pont.valores() == (35, 1, 1)


def test_fechar(pont):
    pont.registrar_entrega(_pedido(1), 0.0)
    pont.fechar()
    depois, perdido = _pedido(2), _pedido(3)
    assert pont.registrar_entrega(depois, 0.0) == 0
    pont.registrar_perda(perdido)
    assert pont.valores() == (35, 1, 0)
    assert depois.estado is perdido.estado is EstadoPedido.AGUARDANDO


def test_sem_corrida(pont):
    n_threads, por_thread = 8, 500
    barreira = threading.Barrier(n_threads)

    def entregar(base: int) -> None:
        barreira.wait()
        for i in range(por_thread):
            pont.registrar_entrega(_pedido(base + i), 0.0)

    threads = [threading.Thread(target=entregar, args=(k * por_thread,), daemon=True)
               for k in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive()
    total = n_threads * por_thread
    assert pont.valores() == (total * 35, total, 0)
