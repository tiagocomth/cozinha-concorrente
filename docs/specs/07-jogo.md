# 07 — Jogo (integração)

**Status:** proposta
**Cobre:** RC01, RC06, RC07, RF09 (expiração na fila), integração geral
**Depende de:** 00–06
**Arquivo:** `cozinha/jogo.py`

## Objetivo

Montar todas as peças, iniciar e parar as threads, e ser a **única porta** entre a interface e a lógica. A interface não conhece fila, semáforo nem thread: só o `Jogo`.

## Interface

Definida na spec 00:

```python
class Jogo:
    def __init__(self, config: Config, fonte_tempo=time.monotonic) -> None: ...
    def iniciar(self) -> None: ...
    def atualizar(self) -> None: ...
    def retrato(self) -> Retrato: ...
    def selecionar(self, cozinheiro_id: int) -> None: ...
    def atribuir(self, pedido_id: int) -> None: ...
    def pausar(self) -> None: ...
    def retomar(self) -> None: ...
    def encerrar(self) -> None: ...
```

## Comportamento

### Montagem (`__init__`)

Cria, nesta ordem: `parar = Event()`, `Relogio`, `Pontuacao`, `Partida`, `Cozinha`, `FilaDePedidos`, o `GeradorDePedidos` e `config.n_cozinheiros` `Cozinheiro` (ids 1..n). **Não inicia threads** no construtor: assim os testes montam e inspecionam sem nada rodando.

### `iniciar`

`relogio.iniciar()`, `partida.iniciar()`, `start()` no gerador e nos cozinheiros. Chamar duas vezes não faz nada.

### `atualizar` (thread da interface, 1x por quadro)

1. Se a partida não está RODANDO, não faz nada.
2. `fila.remover_expirados(agora)` → `pontuacao.registrar_perda` para cada um (RF09).
3. `partida.verificar_fim()`. Se terminou → `encerrar()` (as threads param; o último retrato fica disponível para a tela de resultado).

Tudo aqui é lock curto. **Nada de `join` com timeout longo:** o `encerrar` chamado daqui usa `join(timeout=0)` e deixa as threads terminarem sozinhas (são `daemon`); o `encerrar` do fechamento da janela é que espera.

### `retrato` (RC06)

Monta o `Retrato` pedindo uma cópia a cada parte, **uma de cada vez**, cada uma sob o próprio lock:

```python
pontos, entregues, perdidos = pontuacao.valores()
pedidos = fila.views(agora) + tuple(v for c in self._cozinheiros if (v := c.pedido_view(agora)))  # ordenar por id
cozinheiros = tuple(c.view() for c in self._cozinheiros)
estacoes, grupos = cozinha.views()
```

Nunca segura dois locks ao mesmo tempo. Pequenas inconsistências entre partes são aceitas (spec 00).

### Comandos do jogador

- `selecionar(id)`: guarda o cozinheiro selecionado (atributo simples sob lock). Id inválido é ignorado.
- `atribuir(pedido_id)`: chama `cozinheiro.ordenar(pedido_id)` do selecionado. Sem selecionado, ignora.
- `pausar` / `retomar`: `partida` + `relogio`. As threads param sozinhas pelo `esperar_rodando`.

### `encerrar` (RC07)

1. `parar.set()`.
2. Retoma o relógio, se pausado, para ninguém ficar preso no `esperar_rodando`.
3. `join(timeout=...)` em todas as threads (configurável; 2 s no fechamento da janela).
4. Thread que não terminou → log de aviso com o nome. Os testes tratam isso como falha.

Idempotente: chamar duas vezes não quebra.

## Fora do escopo

- Reiniciar o mesmo `Jogo`: "jogar de novo" cria um `Jogo` novo (spec 08).

## Critérios de aceite (pytest)

- [ ] Construir não inicia nenhuma thread (`threading.active_count()` não muda).
- [ ] `iniciar` sobe `n_cozinheiros + 1` threads com nomes `cozinheiro-N` e `gerador`.
- [ ] **Partida completa acelerada:** `Config` com partida de 3 s e tempos mínimos roda até VITORIA ou DERROTA sozinha (chamando `atualizar` em loop no teste) e termina com todas as threads paradas.
- [ ] `retrato()` funciona antes de iniciar, durante e depois de terminar.
- [ ] `retrato()` chamado em loop por 1 s enquanto o jogo roda nunca levanta exceção e nunca demora mais que alguns milissegundos.
- [ ] Pedido vencido na fila some do retrato e aumenta `perdidos`.
- [ ] `encerrar()` com o jogo pausado termina todas as threads em menos de 1 s.
- [ ] `atribuir` sem cozinheiro selecionado não faz nada.
