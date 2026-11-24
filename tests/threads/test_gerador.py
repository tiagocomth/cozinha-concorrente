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


# ---------- loop ----------

import time  # noqa: E402

import pytest  # noqa: E402

from cozinha.modelo.pedido import Pedido  # noqa: E402


def esperar(condicao, prazo: float = 1.0) -> None:
    fim = time.monotonic() + prazo
    while not condicao():
        assert time.monotonic() < fim, "condição não ficou verdadeira a tempo"
        time.sleep(0.002)


class Montagem:
    def __init__(self, **config) -> None:
        base = {"tick": 0.005, "intervalo_inicial": 0.05, "intervalo_minimo": 0.05,
                "tamanho_max_fila": 4}
        self.config = replace(Config(), **{**base, **config})
        self.relogio = Relogio()
        self.relogio.iniciar()
        self.fila = FilaDePedidos(self.config.tamanho_max_fila)
        self.parar = threading.Event()
        self.gerador = GeradorDePedidos(self.fila, self.relogio, self.config, self.parar)
        self.vistos: list[int] = []
        self._consumidor: threading.Thread | None = None

    def iniciar(self, consumir: bool = False) -> None:
        self.gerador.start()
        if consumir:
            self._consumidor = threading.Thread(target=self._consumir, daemon=True)
            self._consumidor.start()

    def _consumir(self) -> None:
        while not self.parar.is_set():
            p = self.fila.retirar(1, timeout=0.005)
            if p is not None:
                self.vistos.append(p.id)

    def ids_na_fila(self) -> list[int]:
        return [v.id for v in self.fila.views(self.relogio.agora())]

    def encerrar(self) -> None:
        self.parar.set()
        self.relogio.congelar()
        for t in (self.gerador, self._consumidor):
            if t is not None and t.ident is not None:
                t.join(timeout=1)
                assert not t.is_alive()


@pytest.fixture
def montar():
    criadas: list[Montagem] = []

    def fabrica(**config) -> Montagem:
        m = Montagem(**config)
        criadas.append(m)
        return m

    yield fabrica
    for m in criadas:
        m.encerrar()


def test_primeiro_pedido_logo(montar):
    m = montar(intervalo_inicial=10, intervalo_minimo=10)
    m.iniciar()
    esperar(lambda: len(m.fila) == 1, prazo=0.2)


def test_ids_sequenciais(montar):
    m = montar()
    m.iniciar(consumir=True)
    time.sleep(0.5)
    vistos = list(m.vistos)
    assert len(vistos) >= 3
    assert vistos == list(range(1, len(vistos) + 1))


def test_fila_enche_e_espera(montar):
    m = montar()
    m.iniciar()
    esperar(lambda: len(m.fila) == 4)
    time.sleep(0.2)
    assert len(m.fila) == 4
    m.fila.retirar(1, timeout=0.05)
    esperar(lambda: len(m.fila) == 4, prazo=0.2)
    assert m.ids_na_fila() == [2, 3, 4, 5]     # nenhum pedido criado fora da fila


def test_pausa_nao_coloca(montar):
    m = montar()
    m.iniciar(consumir=True)
    esperar(lambda: len(m.vistos) >= 2)
    m.relogio.pausar()
    time.sleep(0.05)                           # assenta um colocar que já estava em andamento
    maior = max(m.vistos + m.ids_na_fila())
    time.sleep(1.0)
    assert max(m.vistos + m.ids_na_fila()) == maior
    m.relogio.retomar()
    esperar(lambda: max(m.vistos + m.ids_na_fila()) > maior)


def test_parar_com_fila_cheia(montar):
    m = montar()
    m.iniciar()
    esperar(lambda: len(m.fila) == 4)
    m.parar.set()
    m.gerador.join(timeout=1)
    assert not m.gerador.is_alive()


def test_excecao_preenche_erro(montar, monkeypatch):
    def quebrar(*args, **kwargs) -> Pedido:
        raise RuntimeError("boom")

    monkeypatch.setattr("cozinha.threads.gerador.Pedido", quebrar)
    m = montar()
    m.iniciar()
    m.gerador.join(timeout=1)
    assert not m.gerador.is_alive()
    assert isinstance(m.gerador.erro, RuntimeError)


def test_pesos_progressivos():
    from cozinha.modelo.receita import RECEITAS
    from cozinha.threads.gerador import pesos_receitas
    inicio, fim = pesos_receitas(RECEITAS, 0.0), pesos_receitas(RECEITAS, 1.0)
    assert inicio[0] == max(inicio)            # Salada (2 etapas) no começo
    assert fim[2] == max(fim)                  # Prato do dia (4 etapas) no fim
    assert sum(inicio) > 0 and sum(fim) > 0


def test_sorteio_progressivo():
    g = _gerador(semente=7, receitas_progressivas=True, duracao_partida=100)
    comeco = [g.sortear(0).nome for _ in range(300)]
    fim = [g.sortear(100).nome for _ in range(300)]
    assert comeco.count("Salada") > comeco.count("Prato do dia")
    assert fim.count("Prato do dia") > fim.count("Salada")


def test_sorteio_sem_progressivo_igual():
    import random
    from cozinha.modelo.receita import RECEITAS
    g = _gerador(semente=3)
    rng = random.Random(3)
    assert [g.sortear().nome for _ in range(20)] == [rng.choice(RECEITAS).nome for _ in range(20)]
