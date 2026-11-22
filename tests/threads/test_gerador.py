from __future__ import annotations

import threading
from dataclasses import replace

from cozinha.config import Config
from cozinha.modelo.fila import FilaDePedidos
from cozinha.modelo.relogio import Relogio
from cozinha.threads.gerador import GeradorDePedidos


def _gerador(**config) -> GeradorDePedidos:
    cfg = replace(Config(), **config)
    return GeradorDePedidos(FilaDePedidos(cfg.tamanho_max_fila), Relogio(), cfg, threading.Event())


def test_nome_e_daemon():
    g = _gerador()
    assert g.name == "gerador"
    assert g.daemon is True
    assert g.erro is None


def test_intervalo():
    g = _gerador(duracao_partida=100, intervalo_inicial=8, intervalo_minimo=3)
    assert g.intervalo(0) == 8
    assert g.intervalo(50) == 5.5
    assert g.intervalo(100) == 3
    assert g.intervalo(500) == 3
    valores = [g.intervalo(t) for t in range(0, 101, 10)]
    assert valores == sorted(valores, reverse=True)
    assert len(set(valores)) == len(valores)


def test_sorteio_reproduzivel():
    a, b = _gerador(semente=42), _gerador(semente=42)
    assert [a.sortear().nome for _ in range(20)] == [b.sortear().nome for _ in range(20)]
    livre = _gerador()
    assert {livre.sortear().nome for _ in range(60)} == {"Salada", "Sopa", "Prato do dia"}
