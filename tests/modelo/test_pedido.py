from __future__ import annotations

from cozinha.modelo.pedido import Pedido
from cozinha.modelo.receita import Etapa, Receita
from cozinha.modelo.tipos import EstadoPedido, TipoEstacao

RECEITA = Receita("teste", (Etapa("entregar", (TipoEstacao.BALCAO,), 0),), 20, 10)


def _pedido() -> Pedido:
    return Pedido(1, RECEITA, criado_em=100.0)


def test_padroes():
    p = _pedido()
    assert p.estado is EstadoPedido.AGUARDANDO
    assert p.cozinheiro_id is None
    assert p.prazo() == 110.0


def test_paciencia_vai_de_1_a_0():
    p = _pedido()
    assert p.paciencia_restante(100) == 1.0
    assert p.paciencia_restante(105) == 0.5
    assert p.paciencia_restante(110) == 0.0
    assert p.paciencia_restante(200) == 0.0


def test_paciencia_antes_da_criacao():
    assert _pedido().paciencia_restante(90) == 1.0


def test_expirou():
    p = _pedido()
    assert p.expirou(109.99) is False
    assert p.expirou(110) is True


def test_identidade():
    a, b = _pedido(), _pedido()
    assert a != b
    assert len({a, b}) == 2
