"""Enums compartilhados por toda a lógica (spec 00)."""
from __future__ import annotations

from enum import Enum, IntEnum, auto


class TipoEstacao(IntEnum):
    # O valor É a ordem global de aquisição (RC04). Não reordenar.
    TABUA = 1
    PIA = 2
    FOGAO = 3
    BALCAO = 4


class EstadoPedido(Enum):
    AGUARDANDO = auto()   # na fila
    EM_PREPARO = auto()   # com um cozinheiro
    ENTREGUE = auto()
    PERDIDO = auto()      # a paciência acabou


class EstadoCozinheiro(Enum):
    LIVRE = auto()        # sem pedido
    ESPERANDO = auto()    # parado na fila de uma estação
    TRABALHANDO = auto()  # usando uma estação


class EstadoPartida(Enum):
    PRONTA = auto()
    RODANDO = auto()
    PAUSADA = auto()
    VITORIA = auto()
    DERROTA = auto()
