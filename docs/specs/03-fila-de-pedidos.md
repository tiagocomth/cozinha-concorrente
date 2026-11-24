# 03 — Fila de pedidos

**Status:** feita
**Cobre:** RF07, RF09, RF10, RF15 (reserva do jogador), RC03 (corrida na fila)
**Depende de:** 00
**Arquivo:** `cozinha/modelo/fila.py`

## Objetivo

A fila compartilhada entre o gerador (produtor) e os cozinheiros (consumidores). É o produtor-consumidor clássico com **semáforos**, como o grupo prometeu: dois cozinheiros nunca pegam o mesmo pedido e a fila nunca passa do tamanho máximo. É também onde fica a ordem do jogador ("C2, faça o pedido #7").

## Interface

```python
class FilaDePedidos:
    def __init__(self, tamanho_max: int) -> None: ...

    def colocar(self, criar: Callable[[], Pedido], timeout: float) -> Pedido | None: ...
    def retirar(self, cozinheiro_id: int, timeout: float) -> Pedido | None: ...
    def reservar(self, pedido_id: int, cozinheiro_id: int) -> bool: ...
    def remover_expirados(self, agora: float) -> list[Pedido]: ...
    def views(self, agora: float) -> tuple[PedidoView, ...]: ...
    def tem_pedido_livre(self, cozinheiro_id: int, agora: float, idade_minima: float) -> bool: ...  # single player
    @property
    def tamanho_max(self) -> int: ...
    def __len__(self) -> int: ...
```

## Comportamento

Três semáforos (os do `threading` servem aqui, porque a justiça entre cozinheiros pela fila não é requisito) e um dicionário de reservas:

```python
self._vagas = Semaphore(tamanho_max)     # lugares livres
self._disponiveis = Semaphore(0)         # pedidos para pegar (pode ter "fichas fantasmas", ver abaixo)
self._mutex = Semaphore(1)               # protege a lista e as reservas
self._pedidos: list[Pedido] = []         # do mais antigo ao mais novo
self._reservas: dict[int, int] = {}      # pedido_id → cozinheiro_id
```

### `colocar` (gerador)

1. `vagas.acquire(timeout)`. Falhou → devolve `None` (fila cheia; o gerador tenta de novo, RF10).
2. **Só agora** chama `criar()`, que monta o pedido com `criado_em = agora`. O cliente só "chega" quando há lugar na fila, então nunca existe pedido perdendo paciência fora da fila e fora da tela.
3. Com o mutex: põe no fim da lista, estado AGUARDANDO.
4. `disponiveis.release()` e devolve o pedido.

### `reservar` (a ordem do jogador, chamado pelo `Jogo`)

Com o mutex: se o pedido está na lista, grava `reservas[pedido_id] = cozinheiro_id` e apaga qualquer reserva anterior desse cozinheiro (uma ordem por cozinheiro; a nova substitui). Devolve `False` se o pedido não está mais na fila.

### `retirar` (cozinheiro)

1. `disponiveis.acquire(timeout)`. Falhou → `None`.
2. Com o mutex, escolher nesta ordem:
   1. o pedido reservado **para este** cozinheiro;
   2. senão, o mais antigo **não reservado para outro**.
3. Achou → tira da lista e das reservas, marca EM_PREPARO e `cozinheiro_id`, dá `vagas.release()` e devolve o pedido.
4. Lista vazia (ficha fantasma, ver abaixo) → devolve `None` sem mexer em nada.
5. Só sobraram pedidos reservados para outros → **devolve a ficha** (`disponiveis.release()`) e devolve `None`. O cozinheiro espera um `tick` antes de tentar de novo (spec 04), para não ficar girando.

Com isso, a ordem do jogador vale mesmo com outro cozinheiro livre: ninguém "rouba" um pedido reservado.

### `remover_expirados` (chamado pelo `Jogo.atualizar`, spec 07)

1. Com o mutex: tira da lista (e das reservas) todo pedido com `expirou(agora)`.
2. Para cada um removido, `vagas.release()`.
3. **Não** mexe em `disponiveis`. Tentar um `acquire` ali competiria com um cozinheiro que já passou do passo 1 do `retirar`. A ficha que sobra vira uma "ficha fantasma": o próximo `retirar` acorda, acha a lista vazia e devolve `None`. É inofensivo e mantém a contagem certa: sempre há pelo menos uma ficha por pedido na lista.
4. **Não** muda o estado do pedido. Devolve os removidos, e o `Jogo` chama `Pontuacao.registrar_perda` (spec 06), que é quem marca PERDIDO (spec 00).

### Ordem dos locks

Ninguém segura o `mutex` e espera outro semáforo. O mutex é sempre o último pego e o primeiro solto, e nada demora lá dentro (`criar()` roda **fora** do mutex).

## Casos de borda

- Pedido reservado que expira: some da fila e da reserva, e conta como perdido. Foi escolha do jogador.
- `reservar` de um pedido que outro cozinheiro já pegou → `False` (a tela pode ignorar).
- `timeout` curto (`config.tick`) em tudo, para as threads conseguirem ver o `Event` de parada.

## Fora do escopo

- Prioridade por receita, cancelar pedido manualmente.

## Critérios de aceite (pytest)

- [x] **Sem pedido duplicado:** 2 produtores colocando 500 pedidos e 4 consumidores retirando; cada id sai exatamente uma vez.
- [x] **Nunca acima do máximo:** observado sob estresse, `len(fila) <= tamanho_max` sempre.
- [x] Fila cheia: `colocar(timeout=0.05)` devolve `None` e **não chama** `criar`.
- [x] Fila vazia: `retirar(timeout=0.05)` devolve `None`.
- [x] **Reserva:** pedido 7 reservado para C2; C1 livre retira e recebe outro pedido (ou `None`), nunca o 7; depois C2 retira e recebe o 7.
- [x] Reserva nova do mesmo cozinheiro substitui a antiga.
- [x] Com só pedidos reservados para outros, `retirar` devolve `None` e a ficha volta (o dono da reserva ainda consegue retirar).
- [x] `remover_expirados` tira só os vencidos, libera vaga, limpa a reserva e não muda o estado.
- [x] Depois de expirar pedidos, produtores e consumidores continuam funcionando (fichas fantasmas não travam nem duplicam).
- [x] Pedido retirado sai como EM_PREPARO com o `cozinheiro_id` certo.
