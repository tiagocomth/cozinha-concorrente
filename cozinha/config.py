"""Todos os parâmetros do jogo (spec 00, RNF03). Nada de número mágico fora daqui."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from cozinha.modelo.receita import RECEITAS, Receita
from cozinha.modelo.tipos import TipoEstacao

TABUA, PIA, FOGAO, BALCAO = TipoEstacao


def _quantidade_padrao() -> Mapping[TipoEstacao, int]:
    return MappingProxyType({TABUA: 2, PIA: 1, FOGAO: 2, BALCAO: 2})


@dataclass(frozen=True)
class Config:
    duracao_partida: float = 180.0
    meta_pontos: int = 300
    limite_perdidos: int = 5
    n_cozinheiros: int = 3
    # quantidade[BALCAO] é a capacidade do balcão (um balcão, N vagas).
    quantidade: Mapping[TipoEstacao, int] = field(default_factory=_quantidade_padrao)
    tempo_retirada: float = 1.0            # cliente pegando o prato no balcão
    tamanho_max_fila: int = 6
    intervalo_inicial: float = 8.0         # entre pedidos
    intervalo_minimo: float = 3.0
    bonus_maximo: int = 15
    receitas: tuple[Receita, ...] = RECEITAS
    expiracao: bool = True                 # False só na demonstração de deadlock
    ordem_fixa: bool = True                # False só na demonstração de deadlock
    tick: float = 0.05                     # granularidade de toda espera
    fps: int = 60
    semente: int | None = None             # aleatoriedade reproduzível nos testes

    def __post_init__(self) -> None:
        if not isinstance(self.quantidade, MappingProxyType):
            object.__setattr__(self, "quantidade", MappingProxyType(dict(self.quantidade)))
        positivos = ("duracao_partida", "intervalo_inicial", "intervalo_minimo", "tick")
        for nome in positivos:
            if getattr(self, nome) <= 0:
                raise ValueError(f"{nome} precisa ser > 0")
        if self.tempo_retirada < 0:
            raise ValueError("tempo_retirada precisa ser >= 0")
        if self.intervalo_minimo > self.intervalo_inicial:
            raise ValueError("intervalo_minimo não pode passar de intervalo_inicial")
        for nome in ("n_cozinheiros", "tamanho_max_fila", "limite_perdidos", "fps"):
            if getattr(self, nome) < 1:
                raise ValueError(f"{nome} precisa ser >= 1")
        for tipo in TipoEstacao:
            if self.quantidade.get(tipo, 0) < 1:
                raise ValueError(f"quantidade[{tipo.name}] precisa ser >= 1")
        if not self.receitas:
            raise ValueError("é preciso pelo menos uma receita")

    def validar_para_jogo(self) -> None:
        """Faixas do jogo de verdade. Chamado por __main__, não pelos testes."""
        if not 180 <= self.duracao_partida <= 300:
            raise ValueError("duracao_partida precisa estar entre 180 e 300 s (RF01)")
        if not 3 <= self.n_cozinheiros <= 4:
            raise ValueError("n_cozinheiros precisa estar entre 3 e 4")

    @classmethod
    def demo_deadlock(cls) -> Config:
        """Cenário que trava sem a ordem fixa (spec 09, --demo-deadlock)."""
        quantidade = {TABUA: 2, PIA: 1, FOGAO: 1, BALCAO: 1}
        sopa = tuple(r for r in RECEITAS if r.nome == "Sopa")
        return replace(cls(), ordem_fixa=False, expiracao=False, quantidade=quantidade,
                       receitas=sopa, n_cozinheiros=2, limite_perdidos=1000)
