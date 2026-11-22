"""Thread do cozinheiro (spec 04): pega um pedido, faz as etapas nas estações e entrega."""
from __future__ import annotations

import threading
from threading import Event

from cozinha.config import Config
from cozinha.modelo.estacoes import Cozinha, Reserva
from cozinha.modelo.fila import FilaDePedidos
from cozinha.modelo.pedido import Pedido
from cozinha.modelo.pontuacao import Pontuacao
from cozinha.modelo.receita import Etapa
from cozinha.modelo.relogio import Relogio
from cozinha.modelo.retrato import CozinheiroView, PedidoView
from cozinha.modelo.tipos import EstadoCozinheiro, EstadoPedido, TipoEstacao

LIVRE, ESPERANDO, TRABALHANDO = EstadoCozinheiro


class Cozinheiro(threading.Thread):
    def __init__(self, id: int, fila: FilaDePedidos, cozinha: Cozinha,
                 pontuacao: Pontuacao, relogio: Relogio, config: Config,
                 parar: Event) -> None:
        super().__init__(name=f"cozinheiro-{id}", daemon=True)
        self.id = id
        self._fila = fila
        self._cozinha = cozinha
        self._pontuacao = pontuacao
        self._relogio = relogio
        self._config = config
        self._parar = parar
        self.erro: BaseException | None = None
        # Estado para a tela: só esta thread escreve; view() copia sob o lock.
        self._lock = threading.Lock()
        self._estado = LIVRE
        self._pedido: Pedido | None = None
        self._etapa: str | None = None
        self._progresso = 0.0
        self._segurando: tuple[tuple[TipoEstacao, int], ...] = ()
        self._esperando: TipoEstacao | None = None
        self._esperando_desde = 0.0
        self._espera_total = 0.0

    # ---------- loop ----------

    def run(self) -> None:
        tick = self._config.tick
        while not self._parar.is_set():
            self._relogio.esperar_rodando(self._parar, tick)
            if self._parar.is_set():
                break
            pedido = self._fila.retirar(self.id, timeout=tick)
            if pedido is None:
                self._parar.wait(tick)
                continue
            with self._lock:
                self._pedido = pedido
            for etapa in pedido.receita.etapas:
                if not self._fazer_etapa(pedido, etapa):
                    break
            self._mudar(estado=LIVRE, pedido=None, etapa=None, progresso=0.0)

    def _fazer_etapa(self, pedido: Pedido, etapa: Etapa) -> bool:
        """Faz uma etapa. False se o pedido acabou (parar)."""
        reservas = self._cozinha.ocupar_todas(self.id, etapa.estacoes,
                                              self._parar.is_set, self._ao_mudar)
        if reservas is None:
            return False
        try:
            self._mudar(estado=TRABALHANDO, etapa=etapa.nome, progresso=0.0)
            if not self._trabalhar(etapa.duracao):
                return False
            if etapa.entrega:
                self._pontuacao.registrar_entrega(pedido, self._relogio.agora())
            return True
        finally:
            self._cozinha.liberar(reservas)
            self._mudar(segurando=())

    def _trabalhar(self, duracao: float) -> bool:
        """Espera `duracao` de tempo de jogo em ticks. False se `parar`."""
        feito = 0.0
        anterior = self._relogio.agora()
        while feito < duracao:
            if self._parar.wait(self._config.tick):
                return False
            agora = self._relogio.agora()
            feito += agora - anterior
            anterior = agora
            self._mudar(progresso=min(1.0, feito / duracao) if duracao else 1.0)
        return True

    # ---------- estado para a tela ----------

    def _mudar(self, **campos) -> None:
        with self._lock:
            for nome, valor in campos.items():
                setattr(self, f"_{nome}", valor)

    def _ao_mudar(self, segurando: tuple[Reserva, ...], esperando: TipoEstacao | None) -> None:
        """Chamado pela Cozinha durante a aquisição. Converte Reserva em (tipo, indice)."""
        agora = self._relogio.agora()
        with self._lock:
            self._segurando = tuple((r.tipo, r.indice) for r in segurando)
            if esperando is not None and self._esperando is None:
                self._esperando_desde = agora
                self._estado = ESPERANDO
            elif esperando is None and self._esperando is not None:
                self._espera_total += agora - self._esperando_desde
            self._esperando = esperando

    def view(self) -> CozinheiroView:
        agora = self._relogio.agora()
        with self._lock:
            esperando_ha = 0.0
            if self._esperando is not None:
                esperando_ha = max(0.0, agora - self._esperando_desde)
            return CozinheiroView(
                id=self.id, estado=self._estado,
                pedido_id=self._pedido.id if self._pedido else None,
                etapa=self._etapa, progresso=self._progresso,
                segurando=self._segurando, esperando=self._esperando,
                esperando_ha=esperando_ha,
                espera_total=self._espera_total + esperando_ha)

    def pedido_view(self, agora: float) -> PedidoView | None:
        with self._lock:
            p = self._pedido
        if p is None or p.estado in (EstadoPedido.ENTREGUE, EstadoPedido.PERDIDO):
            return None
        return PedidoView(p.id, p.receita.nome, EstadoPedido.EM_PREPARO,
                          p.paciencia_restante(agora), self.id, None)
