"""Efeitos de tela (só visuais): "+N" ao entregar, "X" quando um cliente desiste.

São deduzidos comparando um Retrato com o anterior: a lógica não ganha eventos novos.
"""
from __future__ import annotations

from dataclasses import dataclass

from cozinha.modelo.retrato import Retrato
from cozinha.modelo.tipos import EstadoPedido, TipoEstacao
from cozinha.ui import layout
from cozinha.ui.layout import Cor, MapaEstacoes, Ponto


@dataclass
class Efeito:
    texto: str
    origem: Ponto
    cor: Cor
    idade: float = 0.0
    duracao: float = layout.EFEITO_SEGUNDOS

    @property
    def pos(self) -> Ponto:
        """Sobe com a idade."""
        return self.origem[0], self.origem[1] - layout.EFEITO_SUBIDA * self.idade

    @property
    def alfa(self) -> int:
        return max(0, round(255 * (1 - self.idade / self.duracao)))


class Efeitos:
    def __init__(self) -> None:
        self.ativos: list[Efeito] = []
        self.pulso_pontos = 0.0            # 1 logo depois de uma entrega, decai até 0

    def observar(self, anterior: Retrato | None, atual: Retrato, mapa: MapaEstacoes) -> None:
        if anterior is None:
            return
        if atual.entregues > anterior.entregues:
            balcao = mapa.estacao(TipoEstacao.BALCAO, 0)
            ganho = atual.pontos - anterior.pontos
            # À esquerda do balcão, que fica na parede direita: o texto não sai da janela.
            self.ativos.append(Efeito(f"+{ganho}", (float(balcao.left - layout.EFEITO_RECUO),
                                                    float(balcao.top)), layout.META))
            self.pulso_pontos = 1.0
        if atual.perdidos > anterior.perdidos:
            agora = {p.id for p in atual.pedidos}
            cartoes = layout.cartoes_pedidos(anterior.pedidos, anterior.tamanho_max_fila)
            sumiram = [p.id for p in anterior.pedidos
                       if p.estado is EstadoPedido.AGUARDANDO and p.id not in agora]
            lugares = [cartoes[i].center for i in sumiram if i in cartoes] or [
                (layout.JANELA[0] / 2, layout.CARTAO_Y + layout.CARTAO_TAMANHO[1] / 2)]
            for x, y in lugares:
                self.ativos.append(Efeito("X", (float(x), float(y)), layout.ALERTA))

    def atualizar(self, dt: float) -> None:
        for e in self.ativos:
            e.idade += dt
        self.ativos = [e for e in self.ativos if e.idade < e.duracao]
        self.pulso_pontos = max(0.0, self.pulso_pontos - dt / layout.PULSO_SEGUNDOS)
