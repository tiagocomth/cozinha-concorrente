# 04 — Cozinheiro

**Status:** proposta
**Cobre:** RF11, RF12, RF14, RF15 (lado da thread), RC01, RC07
**Depende de:** 00, 02, 03, 06 (Relogio, Pontuacao)
**Arquivo:** `cozinha/threads/cozinheiro.py`

## Objetivo

A thread de cada cozinheiro: pega um pedido, executa as etapas da receita nas estações e entrega. É o consumidor da fila e quem disputa as estações.

## Interface

```python
class Cozinheiro(threading.Thread):
    def __init__(self, id: int, fila: FilaDePedidos, cozinha: Cozinha,
                 pontuacao: Pontuacao, relogio: Relogio, config: Config,
                 parar: Event) -> None: ...   # daemon=True, name=f"cozinheiro-{id}"

    def run(self) -> None: ...
    def ordenar(self, pedido_id: int) -> None: ...   # chamado pela interface (via Jogo)
    def view(self) -> CozinheiroView: ...
    def pedido_view(self, agora: float) -> PedidoView | None: ...   # o pedido em preparo, para o Retrato
```

## Comportamento

### Loop

```
enquanto não parar:
    relogio.esperar_rodando(parar)                 # fica parado durante a pausa
    pedido = fila.retirar(id, preferido=ordem_pendente(), timeout)
    se não pegou: continua
    para cada etapa da receita:
        se pedido.expirou(agora): abandona → perda; sai do for
        reservas = cozinha.ocupar_todas(id, etapa.estacoes, ..., desistir=pedido expirou)   # estado ESPERANDO
        se None: se expirou → abandona → perda; senão (parar) → sai
        trabalha etapa.duracao segundos de jogo                     # estado TRABALHANDO
        cozinha.liberar_todas(reservas)                             # sempre, em finally
    se fez todas: pontuacao.registrar_entrega(pedido, agora)
    volta a LIVRE
```

### Regras

- **Solta tudo no fim de cada etapa**, inclusive com exceção (`try/finally`). Nunca segura estação entre etapas: elimina o "segura e espera" fora das etapas de várias estações.
- **A última etapa é a entrega:** usa o BALCÃO. Depois de `duracao`, o prato fica no balcão mais `config.tempo_retirada` (o cliente pegando) e só então o balcão é solto e a entrega é registrada. É isso que faz o balcão de capacidade limitada encher (RF13).
- **Trabalhar** = dormir em passos de `config.tick` somando o tempo de jogo de `relogio.agora()`, checando `parar` e a pausa a cada passo. Durante a pausa o progresso não anda.
- **Expiração durante o preparo:** checada antes de cada etapa e a cada tick. Expirou → solta tudo, marca o pedido PERDIDO e chama `pontuacao.registrar_perda(pedido)`. O cliente foi embora; não adianta terminar.
- **Ordem do jogador:** `ordenar(pedido_id)` guarda o pedido numa `queue.Queue(maxsize=1)`; uma ordem nova substitui a antiga. Só é lida quando o cozinheiro está LIVRE, na hora do `retirar`. Não interrompe o pedido atual.
- **Estado para a tela:** `estado`, `pedido` atual, `etapa`, `progresso`, `estacoes` e `esperando` ficam sob um `Lock` do próprio cozinheiro. `view()` e `pedido_view()` copiam sob esse lock. Só o próprio cozinheiro escreve.
- **Saída:** quando `parar` é setado, termina a etapa atual sem registrar entrega, solta o que tiver e sai do `run`.

## Casos de borda

- Pedido expira enquanto o cozinheiro está ESPERANDO uma estação: o `desistir` passado ao `ocupar_todas` (spec 02) é `lambda: pedido.expirou(relogio.agora())`; na tentativa seguinte ele solta o que pegou e o cozinheiro abandona o pedido.
- Duas entregas no mesmo instante: a `Pontuacao` é que protege a soma (spec 06).

## Fora do escopo

- Movimento físico do cozinheiro pela cozinha (posição, caminho). A tela pode animar a partir do estado, mas a lógica não tem coordenadas.

## Critérios de aceite (pytest, tempos de etapa pequenos)

- [ ] Um cozinheiro e um pedido de salada: o pedido termina ENTREGUE e a pontuação sobe.
- [ ] Ao fim de cada etapa nenhuma estação fica com o id do cozinheiro (inspecionar `cozinha.views()`).
- [ ] Pedido que expira no meio: vira PERDIDO, conta como perdido e as estações ficam livres.
- [ ] `ordenar(id)` faz o cozinheiro LIVRE pegar aquele pedido, não o mais antigo.
- [ ] Pausa: com o relógio pausado, o `progresso` não muda.
- [ ] **Estresse:** 4 cozinheiros, 100 pedidos, tempos mínimos, balcão de capacidade 1; todos os pedidos acabam ENTREGUE ou PERDIDO, sem travar, em menos de 10 s.
- [ ] `parar.set()` + `join(timeout=1)`: a thread termina e nada fica ocupado.
