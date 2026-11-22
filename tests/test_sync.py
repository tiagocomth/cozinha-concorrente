from __future__ import annotations

import threading
import time

import pytest

from cozinha.sync import SemaforoJusto


def _rodar(threads: list[threading.Thread], timeout: float = 10) -> None:
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=timeout)
        assert not t.is_alive()


def _maximo_dentro(valor: int, n_threads: int, voltas: int, pausa: float = 0.0) -> int:
    sem = SemaforoJusto(valor)
    trava = threading.Lock()
    dentro = maximo = 0

    def trabalhar(dono: int) -> None:
        nonlocal dentro, maximo
        for _ in range(voltas):
            assert sem.acquire(dono)
            with trava:
                dentro += 1
                maximo = max(maximo, dentro)
            if pausa:
                time.sleep(pausa)
            with trava:
                dentro -= 1
            sem.release()

    _rodar([threading.Thread(target=trabalhar, args=(i,), daemon=True) for i in range(n_threads)])
    assert sem.disponivel == valor
    return maximo


def test_valor_invalido():
    with pytest.raises(ValueError):
        SemaforoJusto(0)


def test_exclusao():
    assert _maximo_dentro(1, 8, 200) == 1


def test_capacidade():
    assert _maximo_dentro(2, 8, 50, pausa=0.001) == 2


def test_release_sobrando():
    sem = SemaforoJusto(1)
    with pytest.raises(ValueError):
        sem.release()
    assert sem.disponivel == sem.capacidade == 1


def test_disponivel():
    sem = SemaforoJusto(2)
    assert sem.acquire(1)
    assert sem.disponivel == 1
    assert sem.capacidade == 2
    assert sem.esperando() == ()


def test_cancelar_com_vaga_livre_passa():
    assert SemaforoJusto(1).acquire(1, cancelar=lambda: True) is True
