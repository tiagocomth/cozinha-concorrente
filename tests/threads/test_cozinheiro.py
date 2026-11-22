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

TABUA, PIA, FOGAO, BALCAO = TipoEstacao
NUNCA = lambda: False  # noqa: E731


def salada(dur: float = 0.01, paciencia: float = 60, entrega: float = 0.01) -> Receita:
    return Receita("Salada", (Etapa("cortar", (TABUA,), dur),
                              Etapa("entregar", (BALCAO,), entrega)), 20, paciencia)


def sopa(dur: float = 0.01, paciencia: float = 60) -> Receita:
    return Receita("Sopa", (Etapa("cortar", (TABUA,), dur),
                            Etapa("cozinhar", (FOGAO,), dur),
                            Etapa("empratar", (FOGAO, BALCAO), dur)), 35, paciencia)


def esperar(condicao, prazo: float = 2.0) -> None:
    fim = time.monotonic() + prazo
    while not condicao():
        assert time.monotonic() < fim, "condição não ficou verdadeira a tempo"
        time.sleep(0.002)


class Montagem:
    def __init__(self, **config) -> None:
        self.config = replace(Config(), **{"tick": 0.005, "tempo_retirada": 0, **config})
        self.relogio = Relogio()
        self.relogio.iniciar()
        self.pontuacao = Pontuacao(self.config)
        self.cozinha = Cozinha(self.config)
        self.fila = FilaDePedidos(self.config.tamanho_max_fila)
        self.parar = threading.Event()
        self.cozinheiros: list[Cozinheiro] = []
        self._ids = itertools.count(1)

    def pedir(self, receita: Receita) -> Pedido:
        return self.fila.colocar(lambda: Pedido(next(self._ids), receita, self.relogio.agora()), 0.1)

    def cozinheiro(self, cid: int = 1, iniciar: bool = True) -> Cozinheiro:
        c = Cozinheiro(cid, self.fila, self.cozinha, self.pontuacao, self.relogio,
                       self.config, self.parar)
        self.cozinheiros.append(c)
        if iniciar:
            c.start()
        return c

    def ocupadas(self) -> dict[tuple[TipoEstacao, int], int]:
        return {(e.tipo, e.indice): e.ocupada_por
                for e in self.cozinha.views()[0] if e.ocupada_por is not None}

    def encerrar(self) -> None:
        self.parar.set()
        self.relogio.congelar()
        for c in self.cozinheiros:
            if c.is_alive() or c.ident is not None:
                c.join(timeout=1)
                assert not c.is_alive()


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


def finalizado(p: Pedido) -> bool:
    return p.estado in (EstadoPedido.ENTREGUE, EstadoPedido.PERDIDO)


# ---------- Task 3 ----------

def test_nome_e_daemon(montar):
    c = montar().cozinheiro(iniciar=False)
    assert c.name == "cozinheiro-1"
    assert c.daemon is True
    assert c.erro is None
    assert c.view().estado is EstadoCozinheiro.LIVRE


def test_salada_entregue(montar):
    m = montar()
    p = m.pedir(salada())
    c = m.cozinheiro()
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)
    assert m.pontuacao.valores()[0] > 0
    esperar(lambda: c.view().estado is EstadoCozinheiro.LIVRE)
    assert c.erro is None


def test_solta_tudo(montar):
    m = montar()
    p = m.pedir(sopa())
    m.cozinheiro()
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)
    esperar(lambda: m.ocupadas() == {})


def test_pega_o_reservado(montar):
    m = montar()
    p1, p2 = m.pedir(salada()), m.pedir(salada(dur=0.3))
    m.fila.reservar(p2.id, 1)
    m.cozinheiro()
    esperar(lambda: p2.estado is not EstadoPedido.AGUARDANDO)
    assert p2.cozinheiro_id == 1
    assert p1.estado is EstadoPedido.AGUARDANDO      # o reservado saiu primeiro
    esperar(lambda: p1.estado is EstadoPedido.ENTREGUE)


def test_livre_nao_retira_na_pausa(montar):
    m = montar()
    m.relogio.pausar()
    p = m.pedir(salada())
    m.cozinheiro()
    time.sleep(0.2)
    assert len(m.fila) == 1
    m.relogio.retomar()
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)


def test_parar_livre(montar):
    m = montar()
    c = m.cozinheiro()
    time.sleep(0.05)
    m.parar.set()
    c.join(timeout=1)
    assert not c.is_alive()


# ---------- Task 4 ----------

def test_pausa_congela_progresso(montar):
    m = montar()
    p = m.pedir(salada(dur=0.5))
    c = m.cozinheiro()
    esperar(lambda: c.view().estado is EstadoCozinheiro.TRABALHANDO and c.view().progresso > 0)
    m.relogio.pausar()
    time.sleep(0.02)
    antes = c.view().progresso
    time.sleep(0.2)
    assert c.view().progresso == antes
    m.relogio.retomar()
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)


def test_expira_em_etapa_normal(montar):
    m = montar()
    p = m.pedir(salada(dur=0.5, paciencia=0.05))
    m.cozinheiro()
    esperar(lambda: p.estado is EstadoPedido.PERDIDO)
    assert m.pontuacao.valores()[2] == 1
    esperar(lambda: m.ocupadas() == {})


def test_expira_esperando_estacao(montar):
    m = montar(quantidade={TABUA: 1, PIA: 1, FOGAO: 1, BALCAO: 1})
    m.cozinha.ocupar_todas(99, (TABUA,), NUNCA)
    p = m.pedir(salada(paciencia=0.1))
    m.cozinheiro()
    esperar(lambda: p.estado is EstadoPedido.PERDIDO)
    grupo_tabua = next(g for g in m.cozinha.views()[1] if g.tipo is TABUA)
    assert 1 not in grupo_tabua.fila_espera
    assert m.ocupadas() == {(TABUA, 0): 99}


def test_sem_expiracao_na_demo(montar):
    m = montar(expiracao=False)
    p = m.pedir(salada(dur=0.2, paciencia=0.05))
    m.cozinheiro()
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)


def test_pausa_nao_expira(montar):
    m = montar()
    p = m.pedir(salada(dur=0.2, paciencia=0.3))
    c = m.cozinheiro()
    esperar(lambda: c.view().estado is EstadoCozinheiro.TRABALHANDO)
    m.relogio.pausar()
    time.sleep(0.5)
    m.relogio.retomar()
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)


def test_estacao_na_pausa_espera_retomar(montar):
    m = montar(quantidade={TABUA: 1, PIA: 1, FOGAO: 1, BALCAO: 1})
    reservas = m.cozinha.ocupar_todas(99, (TABUA,), NUNCA)
    p = m.pedir(salada())
    c = m.cozinheiro()
    esperar(lambda: c.view().esperando is TABUA)
    m.relogio.pausar()
    m.cozinha.liberar(reservas)
    esperar(lambda: m.ocupadas() == {(TABUA, 0): 1})
    time.sleep(0.1)
    assert c.view().progresso == 0
    assert p.estado is EstadoPedido.EM_PREPARO
    m.relogio.retomar()
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)


# ---------- Task 5 ----------

def test_empratar_solta_fogao_antes(montar):
    m = montar(tempo_retirada=0.2, quantidade={TABUA: 1, PIA: 1, FOGAO: 1, BALCAO: 1})
    p = m.pedir(sopa())
    c = m.cozinheiro()
    esperar(lambda: c.view().etapa == "empratar" and m.ocupadas() == {(BALCAO, 0): 1})
    assert p.estado is EstadoPedido.EM_PREPARO       # ainda na retirada
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)


def test_balcao_cheio_bloqueia(montar):
    m = montar(tempo_retirada=0.3, quantidade={TABUA: 2, PIA: 1, FOGAO: 1, BALCAO: 1})
    p1, p2 = m.pedir(salada()), m.pedir(salada())
    c1, c2 = m.cozinheiro(1), m.cozinheiro(2)

    def alguem_espera_balcao() -> bool:
        return any(c.view().estado is EstadoCozinheiro.ESPERANDO and c.view().esperando is BALCAO
                   for c in (c1, c2))

    esperar(alguem_espera_balcao)
    assert len([v for v in m.ocupadas() if v[0] is BALCAO]) == 1
    esperar(lambda: p1.estado is p2.estado is EstadoPedido.ENTREGUE, prazo=3)


def test_view_segurando_e_esperando(montar):
    m = montar(quantidade={TABUA: 1, PIA: 1, FOGAO: 1, BALCAO: 1})
    balcao = m.cozinha.ocupar_todas(99, (BALCAO,), NUNCA)
    p = m.pedir(sopa())
    c = m.cozinheiro()
    esperar(lambda: c.view().esperando is BALCAO)
    v = c.view()
    assert v.segurando == ((FOGAO, 0),)
    assert v.estado is EstadoCozinheiro.ESPERANDO
    time.sleep(0.05)
    assert c.view().esperando_ha > 0
    m.cozinha.liberar(balcao)
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)
    assert c.view().espera_total > 0


def test_expira_na_retirada_conta_entregue(montar):
    m = montar(tempo_retirada=0.3)
    p = m.pedir(salada(paciencia=0.15))
    c = m.cozinheiro()
    esperar(lambda: c.view().etapa == "entregar")
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)
    assert m.pontuacao.valores() == (20, 1, 0)


def test_parar_no_meio_da_etapa(montar):
    m = montar()
    p = m.pedir(salada(dur=5))
    c = m.cozinheiro()
    esperar(lambda: c.view().estado is EstadoCozinheiro.TRABALHANDO)
    m.parar.set()
    c.join(timeout=1)
    assert not c.is_alive()
    assert m.ocupadas() == {}
    assert m.pontuacao.valores() == (0, 0, 0)
    assert p.estado is EstadoPedido.EM_PREPARO


def test_parar_na_retirada(montar):
    m = montar(tempo_retirada=5)
    p = m.pedir(salada())
    c = m.cozinheiro()
    esperar(lambda: m.ocupadas() == {(BALCAO, 0): 1} and c.view().etapa == "entregar")
    time.sleep(0.05)
    m.parar.set()
    c.join(timeout=1)
    assert not c.is_alive()
    assert m.ocupadas() == {}
    assert m.pontuacao.valores() == (0, 0, 0)
    assert p.estado is EstadoPedido.EM_PREPARO


def test_pedido_view(montar):
    m = montar()
    p = m.pedir(salada(dur=0.3))
    c = m.cozinheiro()
    esperar(lambda: c.pedido_view(m.relogio.agora()) is not None)
    v = c.pedido_view(m.relogio.agora())
    assert (v.id, v.estado, v.cozinheiro_id, v.reservado_para) == (p.id, EstadoPedido.EM_PREPARO, 1, None)
    esperar(lambda: p.estado is EstadoPedido.ENTREGUE)
    assert c.pedido_view(m.relogio.agora()) is None


# ---------- Task 6 ----------

def test_excecao_preenche_erro(montar):
    m = montar()
    quebrada = Etapa("quebrar", (TABUA,), 0.01)
    object.__setattr__(quebrada, "estacoes", (99,))          # estação que não existe
    receita = Receita("Quebrada", (quebrada,), 10, 60)
    p = m.pedir(receita)
    c = m.cozinheiro()
    c.join(timeout=1)
    assert not c.is_alive()
    assert isinstance(c.erro, KeyError)
    assert p.estado is EstadoPedido.PERDIDO
    assert m.ocupadas() == {}


def test_excecao_depois_da_entrega(montar, monkeypatch):
    m = montar()
    original = m.pontuacao.registrar_entrega

    def entregar_e_quebrar(pedido, agora):
        original(pedido, agora)
        raise RuntimeError("boom")

    monkeypatch.setattr(m.pontuacao, "registrar_entrega", entregar_e_quebrar)
    p = m.pedir(salada())
    c = m.cozinheiro()
    c.join(timeout=1)
    assert not c.is_alive()
    assert isinstance(c.erro, RuntimeError) and str(c.erro) == "boom"
    assert p.estado is EstadoPedido.ENTREGUE
    assert m.pontuacao.valores()[2] == 0
    assert m.ocupadas() == {}


def test_estresse(montar):
    m = montar(quantidade={TABUA: 2, PIA: 1, FOGAO: 2, BALCAO: 1})
    receitas = [salada(paciencia=0.5), sopa(paciencia=0.5)]
    pedidos: list[Pedido] = []
    cozinheiros = [m.cozinheiro(i) for i in range(1, 5)]

    def produzir() -> None:
        for i in range(100):
            while not m.parar.is_set():
                p = m.pedir(receitas[i % 2])
                if p is not None:
                    pedidos.append(p)
                    break

    produtor = threading.Thread(target=produzir, daemon=True)
    produtor.start()
    produtor.join(timeout=10)
    assert not produtor.is_alive()
    # Pedidos que ficaram na fila: expiram e ninguém os pega se demorarem demais.
    def terminou() -> bool:
        for p in m.fila.remover_expirados(m.relogio.agora()):
            m.pontuacao.registrar_perda(p)
        return sum(m.pontuacao.valores()[1:]) == 100

    esperar(terminou, prazo=10)
    m.parar.set()
    for c in cozinheiros:
        c.join(timeout=10)
        assert not c.is_alive()
        assert c.erro is None
    assert all(finalizado(p) for p in pedidos)
    assert m.ocupadas() == {}


def test_erro_preenchido_mesmo_se_registrar_perda_falhar(montar, monkeypatch):
    m = montar()

    def falhar_entrega(pedido, agora):
        raise ValueError("entrega falhou")

    def falhar_perda(pedido):
        raise ValueError("perda também falhou")

    monkeypatch.setattr(m.pontuacao, "registrar_entrega", falhar_entrega)
    monkeypatch.setattr(m.pontuacao, "registrar_perda", falhar_perda)
    m.pedir(salada())
    c = m.cozinheiro()
    c.join(timeout=1)
    assert not c.is_alive()
    assert isinstance(c.erro, ValueError) and str(c.erro) == "entrega falhou"
    assert m.ocupadas() == {}
