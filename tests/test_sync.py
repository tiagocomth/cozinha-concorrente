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


def esperar_na_fila(sem: SemaforoJusto, dono: int, vezes: int = 1, prazo: float = 1.0) -> None:
    """Espera `dono` aparecer `vezes` vezes em esperando() (sem sleep fixo)."""
    fim = time.monotonic() + prazo
    while sem.esperando().count(dono) < vezes:
        assert time.monotonic() < fim, f"{dono} não entrou na fila"
        time.sleep(0.005)


def _chegam_em_ordem(sem: SemaforoJusto, donos: list[int], fatia: float) -> tuple[list[int], list[threading.Thread]]:
    ordem: list[int] = []
    trava = threading.Lock()

    def entrar(dono: int) -> None:
        assert sem.acquire(dono, fatia=fatia)
        with trava:
            ordem.append(dono)
        sem.release()

    threads = []
    for d in donos:
        t = threading.Thread(target=entrar, args=(d,), daemon=True)
        t.start()
        esperar_na_fila(sem, d)
        threads.append(t)
    return ordem, threads


def _terminar(threads: list[threading.Thread], timeout: float = 2) -> None:
    for t in threads:
        t.join(timeout=timeout)
        assert not t.is_alive()


def test_fifo():
    sem = SemaforoJusto(1)
    assert sem.acquire(0)
    ordem, threads = _chegam_em_ordem(sem, [1, 2, 3], fatia=0.05)
    assert sem.esperando() == (1, 2, 3)
    sem.release()
    _terminar(threads)
    assert ordem == [1, 2, 3]


def test_fifo_espera_longa():
    sem = SemaforoJusto(1)
    assert sem.acquire(0)
    ordem, threads = _chegam_em_ordem(sem, [1, 2, 3], fatia=0.01)
    time.sleep(1.0)                 # muitas fatias de espera: ninguém pode perder a vez
    sem.release()
    _terminar(threads)
    assert ordem == [1, 2, 3]


def test_sem_inanicao():
    """Ordem de chegada, não igualdade de usos: quem chega passa na frente de quem chega depois."""
    sem = SemaforoJusto(1)
    parar = threading.Event()
    trava = threading.Lock()
    entradas: list[int] = []

    def disputar(dono: int) -> None:
        while not parar.is_set():
            if sem.acquire(dono, cancelar=parar.is_set, fatia=0.01):
                with trava:
                    entradas.append(dono)
                time.sleep(0.001)
                sem.release()

    rivais = [threading.Thread(target=disputar, args=(i,), daemon=True) for i in range(1, 5)]
    for t in rivais:
        t.start()
    time.sleep(0.1)
    x_entrou = threading.Event()

    def chegar() -> None:
        assert sem.acquire(99, fatia=0.01)
        with trava:
            entradas.append(99)
        x_entrou.set()
        sem.release()

    x = threading.Thread(target=chegar, daemon=True)
    x.start()
    esperar_na_fila(sem, 99)
    fila = sem.esperando()
    with trava:
        ja_registradas = len(entradas)
    assert x_entrou.wait(timeout=2)
    parar.set()
    _terminar(rivais + [x])
    a_frente = fila.index(99) if 99 in fila else 0
    entradas_antes_de_x = entradas.index(99) - ja_registradas
    # Só quem estava à frente passa antes (+1: uma entrada pode ainda não ter sido registrada).
    assert entradas_antes_de_x <= a_frente + 1


def test_timeout():
    sem = SemaforoJusto(1)
    assert sem.acquire(0)
    inicio = time.monotonic()
    assert sem.acquire(9, timeout=0.05) is False
    assert 0.04 <= time.monotonic() - inicio <= 0.5
    assert 9 not in sem.esperando()


def test_timeout_zero():
    sem = SemaforoJusto(1)
    assert sem.acquire(1, timeout=0) is True
    inicio = time.monotonic()
    assert sem.acquire(2, timeout=0) is False
    assert time.monotonic() - inicio < 0.05
    assert sem.esperando() == ()


def test_cancelar():
    sem = SemaforoJusto(1)
    assert sem.acquire(0)
    sinal = threading.Event()
    threading.Timer(0.1, sinal.set).start()
    inicio = time.monotonic()
    assert sem.acquire(1, cancelar=sinal.is_set, fatia=0.05) is False
    assert time.monotonic() - inicio < 0.1 + 2 * 0.05
    assert sem.esperando() == ()


def test_desistencia_no_meio():
    sem = SemaforoJusto(1)
    assert sem.acquire(0)
    ordem: list[int] = []
    desistir_b = threading.Event()

    def entrar(dono: int, cancelar=None) -> None:
        if sem.acquire(dono, cancelar=cancelar, fatia=0.01):
            ordem.append(dono)
            sem.release()

    a = threading.Thread(target=entrar, args=(1,), daemon=True)
    b = threading.Thread(target=entrar, args=(2, desistir_b.is_set), daemon=True)
    c = threading.Thread(target=entrar, args=(3,), daemon=True)
    for t, d in ((a, 1), (b, 2), (c, 3)):
        t.start()
        esperar_na_fila(sem, d)
    desistir_b.set()
    fim = time.monotonic() + 1
    while 2 in sem.esperando():
        assert time.monotonic() < fim
        time.sleep(0.005)
    sem.release()
    _terminar([a, b, c])
    assert ordem == [1, 3]


def test_duas_senhas_do_mesmo_dono():
    sem = SemaforoJusto(1)
    assert sem.acquire(0)
    cancelar_primeira = threading.Event()
    t1 = threading.Thread(target=sem.acquire, args=(7,),
                          kwargs={"cancelar": cancelar_primeira.is_set, "fatia": 0.01}, daemon=True)
    t2 = threading.Thread(target=sem.acquire, args=(7,), kwargs={"fatia": 0.01}, daemon=True)
    t1.start()
    esperar_na_fila(sem, 7)
    t2.start()
    esperar_na_fila(sem, 7, vezes=2)
    cancelar_primeira.set()
    t1.join(timeout=1)
    assert not t1.is_alive()
    assert sem.esperando().count(7) == 1
    sem.release()
    t2.join(timeout=1)
    assert not t2.is_alive()
