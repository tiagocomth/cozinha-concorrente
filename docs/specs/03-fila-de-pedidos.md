# 03 — Fila de pedidos

**Status:** proposta
**Cobre:** RF07, RF09, RF10, RC03 (corrida na fila)
**Depende de:** 00
**Arquivo:** `cozinha/modelo/fila.py`

## Objetivo

A fila compartilhada entre o gerador (produtor) e os cozinheiros (consumidores). É o produtor-consumidor clássico com **semáforos**, como o grupo prometeu: dois cozinheiros nunca pegam o mesmo pedido e a fila nunca passa do tamanho máximo.

## Interface

```python
class FilaDePedidos:
    def __init__(self, tamanho_max: int) -> None: ...

    def colocar(self, pedido: Pedido, timeout: float) -> bool: ...
    def retirar(self, cozinheiro_id: int, preferido: int | None,
                timeout: float) -> Pedido | None: ...
    def remover_expirados(self, agora: float) -> list[Pedido]: ...
    def views(self, agora: float) -> tuple[PedidoView, ...]: ...
    def __len__(self) -> int: ...
```

## Comportamento

Três semáforos (os do `threading` servem aqui: a justiça entre cozinheiros pela fila não é requisito):

```python
self._vagas = Semaphore(tamanho_max)     # lugares livres
self._disponiveis = Semaphore(0)         # pedidos para pegar (pode ter "fichas fantasmas", ver abaixo)
self._mutex = Semaphore(1)               # protege a lista
self._pedidos: list[Pedido] = []         # do mais antigo ao mais novo
```

### `colocar` (gerador)

1. `vagas.acquire(timeout)`. Falhou → devolve `False` (fila cheia; o gerador tenta de novo, RF10).
2. Com o mutex: põe no fim da lista, estado AGUARDANDO.
3. `disponiveis.release()`.

### `retirar` (cozinheiro)

1. `disponiveis.acquire(timeout)`. Falhou → `None`.
2. Com o mutex: se `preferido` está na lista, pega ele; senão, pega o mais antigo. Marca EM_PREPARO e `cozinheiro_id`.
3. Lista vazia (ficha fantasma, ver abaixo) → devolve `None` **sem** mexer em `vagas`.
4. Pegou → `vagas.release()` e devolve o pedido.

### `remover_expirados` (chamado pelo `Jogo.atualizar`, spec 07)

1. Com o mutex: tira da lista todo pedido com `expirou(agora)`, marca PERDIDO.
2. Para cada um removido, `vagas.release()`.
3. **Não** mexe em `disponiveis`: tentar um `acquire` ali competiria com um cozinheiro que já passou do passo 1 do `retirar`. A ficha que sobra vira uma "ficha fantasma": o próximo `retirar` acorda, acha a lista vazia e devolve `None`. É inofensivo e é o que mantém a contagem certa.
4. Devolve os removidos (a `Pontuacao` registra a perda, spec 06).

### Ordem dos locks

Ninguém segura o `mutex` e espera outro semáforo. O mutex é sempre o último pego e o primeiro solto, e nada demora lá dentro.

## Casos de borda

- `preferido` que já saiu (outro pegou ou expirou) → pega o mais antigo. O jogador pediu um pedido, mas ficar parado é pior.
- `timeout` curto em tudo, para as threads conseguirem ver o `Event` de parada.

## Fora do escopo

- Prioridade por receita, cancelar pedido manualmente.

## Critérios de aceite (pytest)

- [ ] **Sem pedido duplicado:** 2 produtores colocando 500 pedidos e 4 consumidores retirando; cada id sai exatamente uma vez.
- [ ] **Nunca acima do máximo:** observado sob estresse, `len(fila) <= tamanho_max` sempre.
- [ ] Fila cheia: `colocar(timeout=0.05)` devolve `False`.
- [ ] Fila vazia: `retirar(timeout=0.05)` devolve `None`.
- [ ] `preferido` presente é retirado mesmo não sendo o mais antigo; ausente cai no mais antigo.
- [ ] `remover_expirados` tira só os vencidos, marca PERDIDO e libera vaga.
- [ ] Depois de expirar pedidos, produtores e consumidores continuam funcionando (fichas fantasmas não travam nem duplicam).
- [ ] Pedido retirado sai como EM_PREPARO com o `cozinheiro_id` certo.
