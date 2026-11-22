from __future__ import annotations

import itertools
import threading
import time

from cozinha.modelo.fila import FilaDePedidos
from cozinha.modelo.pedido import Pedido
from cozinha.modelo.receita import Etapa, Receita
from cozinha.modelo.tipos import EstadoPedido, TipoEstacao

RECEITA = Receita("teste", (Etapa("entregar", (TipoEstacao.BALCAO,), 0),), 20, 10)


class Criador:
    """Fábrica de pedidos com ids sequenciais; conta quantas vezes foi chamada."""

    def __init__(self, criado_em: float = 0.0) -> None:
        self._ids = itertools.count(1)
        self._trava = threading.Lock()
        self.chamadas = 0
        self.criado_em = criado_em

    def __call__(self) -> Pedido:
        with self._trava:
            self.chamadas += 1
            return Pedido(next(self._ids), RECEITA, self.criado_em)


def _encher(fila: FilaDePedidos, criar: Criador, n: int) -> list[Pedido]:
    return [fila.colocar(criar, timeout=0.05) for _ in range(n)]


def test_colocar_e_retirar():
    fila = FilaDePedidos(6)
    (p,) = _encher(fila, Criador(), 1)
    assert p.estado is EstadoPedido.AGUARDANDO
    assert fila.retirar(1, timeout=0.05) is p
    assert p.estado is EstadoPedido.EM_PREPARO
    assert p.cozinheiro_id == 1
    assert len(fila) == 0


def test_ordem_fifo():
    fila = FilaDePedidos(6)
    _encher(fila, Criador(), 3)
    assert [fila.retirar(1, 0.05).id for _ in range(3)] == [1, 2, 3]


def test_tamanho_max():
    assert FilaDePedidos(4).tamanho_max == 4


def test_fila_cheia_nao_cria():
    fila, criar = FilaDePedidos(2), Criador()
    _encher(fila, criar, 2)
    assert fila.colocar(criar, timeout=0.05) is None
    assert criar.chamadas == 2


def test_fila_vazia():
    assert FilaDePedidos(2).retirar(1, timeout=0.05) is None


def test_reserva():
    fila = FilaDePedidos(6)
    _encher(fila, Criador(), 3)
    assert fila.reservar(2, 2) is True
    assert fila.retirar(1, 0.05).id == 1
    assert fila.retirar(1, 0.05).id == 3
    assert fila.retirar(1, 0.05) is None
    assert fila.retirar(2, 0.05).id == 2


def test_reserva_substitui():
    fila = FilaDePedidos(6)
    _encher(fila, Criador(), 3)
    fila.reservar(1, 2)
    fila.reservar(3, 2)
    assert fila.retirar(1, 0.05).id == 1


def test_duas_ordens_mesmo_pedido():
    fila = FilaDePedidos(6)
    _encher(fila, Criador(), 1)
    fila.reservar(1, 1)
    fila.reservar(1, 2)
    assert fila.retirar(1, 0.05) is None
    assert fila.retirar(2, 0.05).id == 1


def test_so_reservados_devolve_ficha():
    fila = FilaDePedidos(6)
    _encher(fila, Criador(), 1)
    fila.reservar(1, 2)
    assert fila.retirar(1, 0.05) is None
    assert fila.retirar(2, 0.05).id == 1


def test_reservar_pedido_ausente():
    fila = FilaDePedidos(6)
    assert fila.reservar(99, 1) is False
    _encher(fila, Criador(), 1)
    fila.retirar(1, 0.05)
    assert fila.reservar(1, 2) is False


def _estresse(fila: FilaDePedidos, total_por_produtor: int, expirar=None) -> tuple[list[int], list[int], list[str]]:
    criar = Criador()
    retirados: list[int] = []
    expirados: list[int] = []
    erros: list[str] = []
    trava = threading.Lock()
    fim = threading.Event()

    def produzir() -> None:
        feitos = 0
        while feitos < total_por_produtor:
            if fila.colocar(criar, timeout=0.05) is not None:
                feitos += 1

    def consumir(cid: int) -> None:
        while not fim.is_set():
            p = fila.retirar(cid, timeout=0.01)
            if p is not None:
                with trava:
                    retirados.append(p.id)

    def observar() -> None:
        while not fim.is_set():
            if len(fila) > fila.tamanho_max:
                erros.append(f"fila com {len(fila)}")
            time.sleep(0.0005)

    def expirar_loop() -> None:
        agora = 0.0
        while not fim.is_set():
            agora += 0.5
            for p in fila.remover_expirados(agora if agora < 15 else 0):
                with trava:
                    expirados.append(p.id)
            time.sleep(0.001)

    produtores = [threading.Thread(target=produzir, daemon=True) for _ in range(2)]
    outros = [threading.Thread(target=consumir, args=(c,), daemon=True) for c in range(1, 5)]
    outros.append(threading.Thread(target=observar, daemon=True))
    if expirar:
        outros.append(threading.Thread(target=expirar_loop, daemon=True))
    for t in produtores + outros:
        t.start()
    for t in produtores:
        t.join(timeout=10)
        assert not t.is_alive()
    prazo = time.monotonic() + 5
    while len(retirados) + len(expirados) < 2 * total_por_produtor and time.monotonic() < prazo:
        time.sleep(0.01)
    fim.set()
    for t in outros:
        t.join(timeout=2)
        assert not t.is_alive()
    return retirados, expirados, erros


def test_sem_duplicado():
    retirados, _, erros = _estresse(FilaDePedidos(6), 250)
    assert sorted(retirados) == list(range(1, 501))
    assert erros == []
