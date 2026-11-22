"""Pedido de um cliente (spec 00).

Quem escreve: a fila (AGUARDANDO → EM_PREPARO) e só a Pontuacao (ENTREGUE/PERDIDO).
"""
from __future__ import annotations

from dataclasses import dataclass

from cozinha.modelo.receita import Receita
from cozinha.modelo.tipos import EstadoPedido


@dataclass(eq=False)            # identidade, não valor
class Pedido:
    id: int
    receita: Receita
    criado_em: float            # Relogio.agora()
    estado: EstadoPedido = EstadoPedido.AGUARDANDO
    cozinheiro_id: int | None = None

    def prazo(self) -> float:
        return self.criado_em + self.receita.paciencia

    def paciencia_restante(self, agora: float) -> float:
        """Fração 0..1 da paciência que sobra."""
        fracao = (self.prazo() - agora) / self.receita.paciencia
        return min(1.0, max(0.0, fracao))

    def expirou(self, agora: float) -> bool:
        return agora >= self.prazo()
