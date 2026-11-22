from __future__ import annotations

import threading
import time

import pytest

from cozinha.modelo.estacoes import GrupoDeEstacoes, Reserva
from cozinha.modelo.retrato import EstacaoView, GrupoView
from cozinha.modelo.tipos import TipoEstacao

TABUA, PIA, FOGAO, BALCAO = TipoEstacao
NUNCA = lambda: False  # noqa: E731


def _esperar(condicao, prazo: float = 1.0) -> None:
    fim = time.monotonic() + prazo
    while not condicao():
        assert time.monotonic() < fim, "condição não ficou verdadeira a tempo"
        time.sleep(0.005)


def test_indices_validos():
    g = GrupoDeEstacoes(FOGAO, 2, fatia=0.01)
    assert g.ocupar(1, NUNCA) == Reserva(FOGAO, 0)
    assert g.ocupar(2, NUNCA) == Reserva(FOGAO, 1)


def test_menor_indice_livre():
    g = GrupoDeEstacoes(FOGAO, 2, fatia=0.01)
    r0, _ = g.ocupar(1, NUNCA), g.ocupar(2, NUNCA)
    g.liberar(r0)
    assert g.ocupar(3, NUNCA) == Reserva(FOGAO, 0)


def test_liberar_duas_vezes():
    g = GrupoDeEstacoes(FOGAO, 1, fatia=0.01)
    r = g.ocupar(1, NUNCA)
    g.liberar(r)
    with pytest.raises(ValueError):
        g.liberar(r)


def test_liberar_reserva_invalida():
    g = GrupoDeEstacoes(FOGAO, 1, fatia=0.01)
    g.ocupar(1, NUNCA)
    antes = (g.views(), g.view())
    with pytest.raises(ValueError):
        g.liberar(Reserva(FOGAO, 5))
    with pytest.raises(ValueError):
        g.liberar(Reserva(PIA, 0))
    assert (g.views(), g.view()) == antes


def test_exclusao_grupo():
    g = GrupoDeEstacoes(FOGAO, 2, fatia=0.01)
    trava = threading.Lock()
    donos: dict[Reserva, int] = {}
    erros: list[str] = []

    def usar(dono: int) -> None:
        for _ in range(200):
            r = g.ocupar(dono, NUNCA)
            with trava:
                if r in donos:
                    erros.append(f"{r} já era de {donos[r]}")
                donos[r] = dono
                if len(donos) > 2:
                    erros.append("mais de 2 ocupadas")
            with trava:
                del donos[r]
            g.liberar(r)

    threads = [threading.Thread(target=usar, args=(i,), daemon=True) for i in range(1, 5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive()
    assert erros == []


def test_cancelado():
    g = GrupoDeEstacoes(FOGAO, 1, fatia=0.01)
    g.ocupar(1, NUNCA)
    assert g.ocupar(2, lambda: True) is None
    assert 2 not in g.view().fila_espera


def test_views():
    g = GrupoDeEstacoes(FOGAO, 1, fatia=0.01)
    r = g.ocupar(1, NUNCA)
    t = threading.Thread(target=g.ocupar, args=(2, NUNCA), daemon=True)
    t.start()
    _esperar(lambda: g.view().fila_espera == (2,))
    assert g.views() == (EstacaoView(FOGAO, 0, 1),)
    assert g.view() == GrupoView(FOGAO, 1, (2,))
    g.liberar(r)
    t.join(timeout=1)
    assert not t.is_alive()
    assert g.views() == (EstacaoView(FOGAO, 0, 2),)
