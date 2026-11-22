"""Etapas e receitas (spec 00)."""
from __future__ import annotations

from dataclasses import dataclass

from cozinha.modelo.tipos import TipoEstacao

TABUA, PIA, FOGAO, BALCAO = TipoEstacao


@dataclass(frozen=True)
class Etapa:
    nome: str                          # "cortar", "cozinhar", "empratar"...
    estacoes: tuple[TipoEstacao, ...]  # quase sempre 1; empratar usa 2
    duracao: float                     # segundos de jogo

    def __post_init__(self) -> None:
        if len(set(self.estacoes)) != len(self.estacoes):
            raise ValueError(f"etapa {self.nome!r} com estação repetida: {self.estacoes}")
        # Já em ordem de aquisição: quem adquire nunca precisa ordenar (RC04).
        object.__setattr__(self, "estacoes", tuple(sorted(self.estacoes)))

    @property
    def entrega(self) -> bool:
        return BALCAO in self.estacoes


@dataclass(frozen=True)
class Receita:
    nome: str
    etapas: tuple[Etapa, ...]
    pontos: int        # base por entrega a tempo
    paciencia: float   # segundos que o cliente espera

    def __post_init__(self) -> None:
        if any(e.entrega for e in self.etapas[:-1]):
            raise ValueError(f"receita {self.nome!r}: só a última etapa pode usar o BALCAO")


# Proposta, balancear no M5.
RECEITAS: tuple[Receita, ...] = (
    Receita("Salada", (
        Etapa("cortar", (TABUA,), 2),
        Etapa("entregar", (BALCAO,), 0),
    ), pontos=20, paciencia=25),
    Receita("Sopa", (
        Etapa("cortar", (TABUA,), 2),
        Etapa("cozinhar", (FOGAO,), 4),
        Etapa("empratar", (FOGAO, BALCAO), 1),
    ), pontos=35, paciencia=35),
    Receita("Prato do dia", (
        Etapa("lavar", (PIA,), 2),
        Etapa("cortar", (TABUA,), 2),
        Etapa("cozinhar", (FOGAO,), 5),
        Etapa("empratar", (FOGAO, BALCAO), 1),
    ), pontos=50, paciencia=45),
)
