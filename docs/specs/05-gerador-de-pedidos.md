# 05 — Gerador de pedidos

**Status:** proposta
**Cobre:** RF06, RF07, RF10, RC01
**Depende de:** 00, 03, 06 (Relogio)
**Arquivo:** `cozinha/threads/gerador.py`

## Objetivo

A thread produtora: cria os clientes com seus pedidos em intervalos cada vez menores e coloca na fila.

## Interface

```python
class GeradorDePedidos(threading.Thread):
    def __init__(self, fila: FilaDePedidos, relogio: Relogio, config: Config,
                 parar: Event) -> None: ...   # daemon=True, name="gerador"

    def run(self) -> None: ...
    def intervalo(self, decorrido: float) -> float: ...   # pura, testável sozinha
```

## Comportamento

### Loop

```
primeiro pedido logo no início
enquanto não parar:
    relogio.esperar_rodando(parar)
    espera intervalo(decorrido) segundos de jogo (em ticks, checando parar e pausa)
    cria Pedido(id=próximo, receita=sorteada, criado_em=agora)
    enquanto não parar e não fila.colocar(pedido, timeout): repete    # fila cheia: espera (RF10)
```

### Aceleração (RF06)

```python
def intervalo(self, decorrido):
    fracao = min(decorrido / config.duracao_partida, 1.0)
    return max(config.intervalo_minimo,
               config.intervalo_inicial - (config.intervalo_inicial - config.intervalo_minimo) * fracao)
```

Linear do inicial ao mínimo ao longo da partida. **(Proposta:** trocar por degraus se o balanceamento pedir.)

### Detalhes

- **Sorteio:** `random.Random(config.semente)` próprio da thread (não o global), para testes reproduzíveis. Peso igual entre receitas **(proposta:** pesar para receitas simples no começo).
- **Ids:** contador próprio, começando em 1. Só esta thread cria pedidos, então não precisa de lock.
- **`criado_em`** é o momento em que o pedido é criado, não quando entra na fila. Se a fila estava cheia, o cliente já chega com menos paciência: é a cozinha "lotada".
- A paciência de quem está na fila é vigiada pelo `Jogo.atualizar` (spec 07), não por esta thread.

## Fora do escopo

- Clientes com mais de um prato, eventos especiais (horário de pico).

## Critérios de aceite (pytest)

- [ ] `intervalo(0) == intervalo_inicial`, `intervalo(duracao) == intervalo_minimo`, e é decrescente.
- [ ] Com semente fixa, a sequência de receitas é sempre a mesma.
- [ ] Com intervalo pequeno e ninguém consumindo, a fila enche até `tamanho_max` e o gerador espera (não cria pedidos perdidos por falta de vaga).
- [ ] Ids sobem de 1 em 1, sem repetir.
- [ ] Pausado, não cria pedidos.
- [ ] `parar.set()` + `join(timeout=1)` termina a thread mesmo com a fila cheia.
