from __future__ import annotations

import threading
import time

from cozinha.modelo.relogio import Relogio


def _iniciado(fonte) -> Relogio:
    r = Relogio(fonte)
    r.iniciar()
    return r


def test_pausa_desconta(fonte_falsa):
    r = _iniciado(fonte_falsa)
    fonte_falsa.avancar(10)
    r.pausar()
    fonte_falsa.avancar(5)
    r.retomar()
    fonte_falsa.avancar(2)
    assert r.agora() == 12


def test_antes_de_iniciar(fonte_falsa):
    r = Relogio(fonte_falsa)
    fonte_falsa.avancar(7)
    assert r.agora() == 0


def test_congelar(fonte_falsa):
    r = _iniciado(fonte_falsa)
    fonte_falsa.avancar(3)
    r.congelar()
    fonte_falsa.avancar(50)
    assert r.agora() == 3


def test_congelar_na_pausa(fonte_falsa):
    r = _iniciado(fonte_falsa)
    fonte_falsa.avancar(4)
    r.pausar()
    fonte_falsa.avancar(3)
    r.congelar()
    r.retomar()
    fonte_falsa.avancar(10)
    assert r.agora() == 4
    assert r.pausado is False


def test_pausa_antes_de_iniciar(fonte_falsa):
    r = Relogio(fonte_falsa)
    r.pausar()
    r.retomar()
    assert r.agora() == 0
    r.iniciar()
    fonte_falsa.avancar(2)
    assert r.agora() == 2


def test_pausar_duas_vezes(fonte_falsa):
    r = _iniciado(fonte_falsa)
    fonte_falsa.avancar(1)
    r.pausar()
    fonte_falsa.avancar(2)
    r.pausar()
    fonte_falsa.avancar(3)
    r.retomar()
    r.retomar()
    fonte_falsa.avancar(1)
    assert r.agora() == 2
    assert r.pausado is False


def test_pausado(fonte_falsa):
    r = _iniciado(fonte_falsa)
    assert r.pausado is False
    r.pausar()
    assert r.pausado is True


def _espera_em_thread(r: Relogio, parar: threading.Event) -> threading.Thread:
    t = threading.Thread(target=r.esperar_rodando, args=(parar, 0.05), daemon=True)
    t.start()
    return t


def test_esperar_rodando_sai_com_parar():
    r = Relogio()
    r.iniciar()
    r.pausar()
    parar = threading.Event()
    t = _espera_em_thread(r, parar)
    time.sleep(0.1)
    assert t.is_alive()
    inicio = time.monotonic()
    parar.set()
    t.join(timeout=1)
    assert not t.is_alive()
    assert time.monotonic() - inicio < 0.1   # menos de 2 × fatia


def test_esperar_rodando_volta_ao_retomar():
    r = Relogio()
    r.iniciar()
    r.pausar()
    t = _espera_em_thread(r, threading.Event())
    time.sleep(0.1)
    assert t.is_alive()
    r.retomar()
    t.join(timeout=1)
    assert not t.is_alive()


def test_esperar_rodando_nao_prende_depois_de_congelar():
    r = Relogio()
    r.iniciar()
    r.pausar()
    t = _espera_em_thread(r, threading.Event())
    r.congelar()
    t.join(timeout=1)
    assert not t.is_alive()
