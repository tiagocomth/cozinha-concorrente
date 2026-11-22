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


# ---------- Cozinha ----------

from dataclasses import replace  # noqa: E402

from cozinha.config import Config  # noqa: E402
from cozinha.modelo.estacoes import Cozinha  # noqa: E402

UM_DE_CADA = {TABUA: 1, PIA: 1, FOGAO: 1, BALCAO: 1}


def _cozinha(**kw) -> Cozinha:
    return Cozinha(replace(Config(), quantidade=UM_DE_CADA, tick=0.01, **kw))


def _grupo(coz: Cozinha, tipo: TipoEstacao) -> GrupoView:
    return next(g for g in coz.views()[1] if g.tipo == tipo)


def _ocupadas(coz: Cozinha) -> dict[tuple[TipoEstacao, int], int]:
    return {(e.tipo, e.indice): e.ocupada_por for e in coz.views()[0] if e.ocupada_por is not None}


def test_ordem_errada():
    with pytest.raises(ValueError):
        _cozinha().ocupar_todas(1, (BALCAO, FOGAO), NUNCA)


def test_tipos_vazio():
    chamadas = []
    assert _cozinha().ocupar_todas(1, (), NUNCA, lambda s, e: chamadas.append((s, e))) == ()
    assert chamadas == []


def test_views_ordenadas():
    estacoes, grupos = Cozinha(Config()).views()
    assert [g.tipo for g in grupos] == list(TipoEstacao)
    assert [(e.tipo, e.indice) for e in estacoes] == [
        (TABUA, 0), (TABUA, 1), (PIA, 0), (FOGAO, 0), (FOGAO, 1), (BALCAO, 0), (BALCAO, 1)]


def test_balcao_cheio_bloqueia():
    coz = _cozinha()
    r1 = coz.ocupar_todas(1, (BALCAO,), NUNCA)
    pegou = threading.Event()
    t = threading.Thread(target=lambda: coz.ocupar_todas(2, (BALCAO,), NUNCA) and pegou.set(),
                         daemon=True)
    t.start()
    time.sleep(0.1)
    assert not pegou.is_set()
    coz.liberar(r1)
    assert pegou.wait(timeout=0.5)
    t.join(timeout=1)
    assert not t.is_alive()


def test_fifo_caminho_real():
    coz = _cozinha()
    r0 = coz.ocupar_todas(0, (FOGAO,), NUNCA)
    ordem: list[int] = []

    def cozinhar(dono: int) -> None:
        reservas = coz.ocupar_todas(dono, (FOGAO,), NUNCA)
        ordem.append(dono)
        coz.liberar(reservas)

    threads = []
    for d in (3, 4, 5):
        t = threading.Thread(target=cozinhar, args=(d,), daemon=True)
        t.start()
        _esperar(lambda d=d: d in _grupo(coz, FOGAO).fila_espera)
        threads.append(t)
    time.sleep(1.0)
    coz.liberar(r0)
    for t in threads:
        t.join(timeout=2)
        assert not t.is_alive()
    assert ordem == [3, 4, 5]


def test_ao_mudar():
    coz = _cozinha()
    r2 = coz.ocupar_todas(2, (BALCAO,), NUNCA)
    chamadas = []
    t = threading.Thread(target=coz.ocupar_todas,
                         args=(1, (FOGAO, BALCAO), NUNCA, lambda s, e: chamadas.append((s, e))),
                         daemon=True)
    t.start()
    _esperar(lambda: 1 in _grupo(coz, BALCAO).fila_espera)
    assert ((Reserva(FOGAO, 0),), BALCAO) in chamadas
    coz.liberar(r2)
    t.join(timeout=1)
    assert not t.is_alive()
    assert chamadas[0] == ((), FOGAO)
    assert chamadas[-1] == ((Reserva(FOGAO, 0), Reserva(BALCAO, 0)), None)


def test_cancelado_no_meio():
    coz = _cozinha()
    coz.ocupar_todas(2, (BALCAO,), NUNCA)
    sinal = threading.Event()
    threading.Timer(0.1, sinal.set).start()
    chamadas = []
    assert coz.ocupar_todas(1, (FOGAO, BALCAO), sinal.is_set,
                            lambda s, e: chamadas.append((s, e))) is None
    assert chamadas[-1] == ((), None)
    assert _ocupadas(coz) == {(BALCAO, 0): 2}


def test_liberar_parcial():
    coz = _cozinha()
    reservas = coz.ocupar_todas(1, (FOGAO, BALCAO), NUNCA)
    assert reservas == (Reserva(FOGAO, 0), Reserva(BALCAO, 0))
    coz.liberar([Reserva(FOGAO, 0)])
    assert _ocupadas(coz) == {(BALCAO, 0): 1}
    coz.liberar([Reserva(BALCAO, 0)])
    assert _ocupadas(coz) == {}


def test_cozinha_liberar_invalida_nao_solta_nada():
    coz = _cozinha()
    reservas = coz.ocupar_todas(1, (FOGAO, BALCAO), NUNCA)
    with pytest.raises(ValueError):
        coz.liberar([reservas[0], Reserva(BALCAO, 7)])
    assert _ocupadas(coz) == {(FOGAO, 0): 1, (BALCAO, 0): 1}
