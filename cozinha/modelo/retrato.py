"""Retrato: o único jeito de a interface ler o jogo (spec 00, RC06).

Tudo imutável: a interface pode guardar e desenhar à vontade.
"""
from __future__ import annotations

from dataclasses import dataclass

from cozinha.modelo.tipos import EstadoCozinheiro, EstadoPartida, EstadoPedido, TipoEstacao


@dataclass(frozen=True)
class PedidoView:
    id: int
    receita: str
    estado: EstadoPedido               # só AGUARDANDO ou EM_PREPARO aparecem
    paciencia: float                   # fração 0..1
    cozinheiro_id: int | None          # quem está preparando
    reservado_para: int | None         # ordem do jogador ainda não cumprida (spec 03)
    etapas: tuple[tuple[TipoEstacao, ...], ...] = ()   # estações de cada etapa da receita
    etapa_atual: int = 0               # índice da etapa que falta fazer


@dataclass(frozen=True)
class CozinheiroView:
    id: int
    estado: EstadoCozinheiro
    pedido_id: int | None
    etapa: str | None
    progresso: float                   # 0..1 da etapa atual
    segurando: tuple[tuple[TipoEstacao, int], ...]   # (tipo, índice) das estações que já pegou
    esperando: TipoEstacao | None      # estação que está esperando agora
    esperando_ha: float                # segundos esperando a estação atual (0 se não espera)
    espera_total: float                # segundos esperando na partida inteira
    jogador: bool = False              # controlado pelo jogador (modo single player)
    proxima: tuple[TipoEstacao, ...] = ()   # estações da etapa que o jogador precisa fazer
    mensagem: str | None = None        # resultado do último comando do jogador


@dataclass(frozen=True)
class EstacaoView:
    tipo: TipoEstacao
    indice: int                        # para o balcão, é a vaga
    ocupada_por: int | None


@dataclass(frozen=True)
class GrupoView:
    tipo: TipoEstacao
    capacidade: int
    fila_espera: tuple[int, ...]       # ids dos cozinheiros, na ordem de chegada


@dataclass(frozen=True)
class Retrato:
    estado: EstadoPartida
    tempo_restante: float              # nunca negativo; congela no fim
    pontos: int
    meta: int
    meta_batida: bool
    perdidos: int
    limite_perdidos: int
    entregues: int
    tamanho_max_fila: int
    pedidos: tuple[PedidoView, ...]    # sem ids repetidos, ordenados por id
    cozinheiros: tuple[CozinheiroView, ...]
    estacoes: tuple[EstacaoView, ...]
    grupos: tuple[GrupoView, ...]
    selecionado: int | None            # cozinheiro selecionado pelo jogador (spec 09)

    @classmethod
    def exemplo(cls) -> Retrato:
        """Retrato fixo e coerente, para a interface trabalhar sem a lógica.

        Usa as capacidades da Config() padrão e 5 cozinheiros (mais que o jogo real)
        para mostrar todos os casos: as duas vagas do balcão ocupadas e alguém
        segurando um fogão enquanto espera o balcão (o desenho da demo de deadlock).
        """
        T, P, F, B = TipoEstacao
        TR, ES, LV = EstadoCozinheiro.TRABALHANDO, EstadoCozinheiro.ESPERANDO, EstadoCozinheiro.LIVRE
        AG, EP = EstadoPedido.AGUARDANDO, EstadoPedido.EM_PREPARO
        sal, sop, pra = ((T,), (B,)), ((T,), (F,), (F, B)), ((P,), (T,), (F,), (F, B))
        pedidos = (
            PedidoView(1, "Salada", EP, 0.80, 1, None, sal, 0),
            PedidoView(2, "Sopa", EP, 0.55, 2, None, sop, 2),
            PedidoView(3, "Prato do dia", EP, 0.40, 3, None, pra, 3),
            PedidoView(4, "Sopa", EP, 0.20, 4, None, sop, 2),
            PedidoView(5, "Salada", AG, 0.95, None, None, sal, 0),
            PedidoView(6, "Prato do dia", AG, 0.70, None, 5, pra, 0),
        )
        cozinheiros = (
            CozinheiroView(1, TR, 1, "cortar", 0.50, ((T, 0),), None, 0.0, 1.5,
                           jogador=True, proxima=(T,), mensagem="Pegou #1 Salada"),
            CozinheiroView(2, TR, 2, "empratar", 0.30, ((F, 1), (B, 0)), None, 0.0, 4.0),
            CozinheiroView(3, TR, 3, "empratar", 0.90, ((B, 1),), None, 0.0, 2.2),
            CozinheiroView(4, ES, 4, "empratar", 0.0, ((F, 0),), B, 3.2, 6.8),
            CozinheiroView(5, LV, None, None, 0.0, (), None, 0.0, 0.0),
        )
        estacoes = (
            EstacaoView(T, 0, 1), EstacaoView(T, 1, None),
            EstacaoView(P, 0, None),
            EstacaoView(F, 0, 4), EstacaoView(F, 1, 2),
            EstacaoView(B, 0, 2), EstacaoView(B, 1, 3),
        )
        grupos = (
            GrupoView(T, 2, ()), GrupoView(P, 1, ()),
            GrupoView(F, 2, ()), GrupoView(B, 2, (4,)),
        )
        return cls(
            estado=EstadoPartida.RODANDO, tempo_restante=95.0, pontos=140, meta=300,
            meta_batida=False, perdidos=1, limite_perdidos=5, entregues=5,
            tamanho_max_fila=6, pedidos=pedidos, cozinheiros=cozinheiros,
            estacoes=estacoes, grupos=grupos, selecionado=1,
        )
