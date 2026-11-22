"""Fila de pedidos: produtor-consumidor com semáforos (spec 03, RC03).

Gerador coloca, cozinheiros retiram. Dois cozinheiros nunca pegam o mesmo pedido
e a fila nunca passa do tamanho máximo. Também guarda a ordem do jogador (reserva).

Ordem dos locks: o mutex é sempre o último pego e o primeiro solto; ninguém o
segura esperando outro semáforo, e `criar()` roda fora dele.
"""
from __future__ import annotations

import threading
from collections.abc import Callable

from cozinha.modelo.pedido import Pedido
from cozinha.modelo.retrato import PedidoView
from cozinha.modelo.tipos import EstadoPedido


class FilaDePedidos:
    def __init__(self, tamanho_max: int) -> None:
        if tamanho_max < 1:
            raise ValueError("tamanho_max precisa ser >= 1")
        self._tamanho_max = tamanho_max
        self._vagas = threading.Semaphore(tamanho_max)   # lugares livres
        self._disponiveis = threading.Semaphore(0)       # pedidos para pegar (pode ter fichas fantasmas)
        self._mutex = threading.Semaphore(1)             # protege a lista e as reservas
        self._pedidos: list[Pedido] = []                 # do mais antigo ao mais novo
        self._reservas: dict[int, int] = {}              # pedido_id → cozinheiro_id

    def colocar(self, criar: Callable[[], Pedido], timeout: float) -> Pedido | None:
        """Gerador. None se a fila ficou cheia durante todo o `timeout` (RF10)."""
        if not self._vagas.acquire(timeout=timeout):
            return None
        pedido = criar()          # só agora o cliente chega: nunca perde paciência fora da fila
        with self._mutex:
            pedido.estado = EstadoPedido.AGUARDANDO
            self._pedidos.append(pedido)
        self._disponiveis.release()
        return pedido

    def reservar(self, pedido_id: int, cozinheiro_id: int) -> bool:
        """Ordem do jogador. Uma por cozinheiro; a última ordem para um pedido vale."""
        with self._mutex:
            if not any(p.id == pedido_id for p in self._pedidos):
                return False
            for pid, cid in list(self._reservas.items()):
                if cid == cozinheiro_id:
                    del self._reservas[pid]
            self._reservas[pedido_id] = cozinheiro_id
            return True

    def retirar(self, cozinheiro_id: int, timeout: float) -> Pedido | None:
        """Cozinheiro. Prefere o reservado para ele; nunca pega o reservado para outro."""
        if not self._disponiveis.acquire(timeout=timeout):
            return None
        with self._mutex:
            if not self._pedidos:
                return None                              # ficha fantasma (pedido expirou)
            escolhido = next((p for p in self._pedidos
                              if self._reservas.get(p.id) == cozinheiro_id), None)
            if escolhido is None:
                escolhido = next((p for p in self._pedidos if p.id not in self._reservas), None)
            if escolhido is None:
                devolver_ficha = True                    # só sobraram reservados para outros
            else:
                devolver_ficha = False
                self._pedidos.remove(escolhido)
                self._reservas.pop(escolhido.id, None)
                escolhido.estado = EstadoPedido.EM_PREPARO
                escolhido.cozinheiro_id = cozinheiro_id
        if devolver_ficha:
            self._disponiveis.release()
            return None
        self._vagas.release()
        return escolhido

    def remover_expirados(self, agora: float) -> list[Pedido]:
        """Tira os vencidos (RF09). Não muda o estado: quem marca PERDIDO é a Pontuacao.

        Não mexe em `disponiveis`: a ficha que sobra vira "fantasma" e o próximo
        retirar acha a lista vazia. Tentar um acquire aqui competiria com um
        cozinheiro que já passou do primeiro passo do retirar.
        """
        with self._mutex:
            vencidos = [p for p in self._pedidos if p.expirou(agora)]
            for p in vencidos:
                self._pedidos.remove(p)
                self._reservas.pop(p.id, None)
        for _ in vencidos:
            self._vagas.release()
        return vencidos

    def views(self, agora: float) -> tuple[PedidoView, ...]:
        with self._mutex:
            return tuple(sorted(
                (PedidoView(p.id, p.receita.nome, EstadoPedido.AGUARDANDO,
                            p.paciencia_restante(agora), None, self._reservas.get(p.id))
                 for p in self._pedidos),
                key=lambda v: v.id))

    @property
    def tamanho_max(self) -> int:
        return self._tamanho_max

    def __len__(self) -> int:
        with self._mutex:
            return len(self._pedidos)
