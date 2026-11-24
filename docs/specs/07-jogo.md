# 07 — Jogo (integração)

**Status:** feita
**Cobre:** RC01, RC06, RC07, RF09 (expiração na fila), RF15 (ordem do jogador), integração geral
**Depende de:** 00–06
**Arquivo:** `cozinha/jogo.py`

## Objetivo

Montar todas as peças, iniciar e parar as threads, e ser a **única porta** entre a interface e a lógica. A interface não conhece fila, semáforo nem thread: só o `Jogo`.

## Interface

Definida na spec 00:

```python
class Jogo:
    def __init__(self, config: Config, fonte_tempo: Callable[[], float] = time.monotonic) -> None: ...
    def iniciar(self) -> None: ...
    def atualizar(self) -> None: ...
    def retrato(self) -> Retrato: ...
    def selecionar(self, cozinheiro_id: int) -> None: ...
    def atribuir(self, pedido_id: int) -> None: ...
    def pausar(self) -> None: ...
    def retomar(self) -> None: ...
    def encerrar(self, timeout: float = 2.0) -> list[str]: ...
```

## Comportamento

### Montagem (`__init__`)

Cria, nesta ordem: `parar = Event()`, `Relogio(fonte_tempo)`, `Pontuacao`, `Partida`, `Cozinha`, `FilaDePedidos`, o `GeradorDePedidos` e `config.n_cozinheiros` `Cozinheiro` (ids 1..n). **Não inicia threads** no construtor: assim os testes montam e inspecionam sem nada rodando.

### `iniciar`

`relogio.iniciar()`, `partida.iniciar()`, `start()` no gerador e nos cozinheiros. Chamar duas vezes não faz nada.

### `atualizar` (thread da interface, 1x por quadro)

1. Se a partida não está RODANDO, não faz nada.
2. Se alguma thread tem `erro` (spec 04/05) → sinaliza a parada e levanta `RuntimeError` com a exceção original. Bug de thread derruba o jogo de forma visível, em vez de deixar um cozinheiro "congelado".
3. Se `config.expiracao`: `fila.remover_expirados(agora)` → `pontuacao.registrar_perda` para cada um (RF09).
4. `partida.verificar_fim()`. Se terminou → `_sinalizar_parada()`.

Tudo aqui é lock curto, sem `join`.

### Parada em dois passos

- `_sinalizar_parada()` (interno, não bloqueia): `parar.set()` e `relogio.congelar()` (que também libera quem estava esperando a pausa). As threads saem sozinhas em poucos ticks.
- `encerrar(timeout)` (público, bloqueia): chama `_sinalizar_parada()` e **sempre** faz `join` em todas as threads, dividindo o `timeout` entre elas. Devolve os nomes das que não terminaram (e loga um aviso). Pode ser chamado mais de uma vez: cada chamada espera de novo.

A tela chama `encerrar()` ao sair da partida ou fechar a janela (spec 08). Os testes tratam lista não vazia como falha.

### `retrato` (RC06)

Monta o `Retrato` pedindo uma cópia a cada parte, **uma de cada vez**, cada uma sob o próprio lock:

```python
pontos, entregues, perdidos = pontuacao.valores()
na_fila = fila.views(agora)
em_preparo = [v for c in self._cozinheiros if (v := c.pedido_view(agora))]
pedidos = {v.id: v for v in na_fila} | {v.id: v for v in em_preparo}   # sem repetidos; o do cozinheiro vence
cozinheiros = tuple(c.view() for c in self._cozinheiros)
estacoes, grupos = cozinha.views()
# + estado, tempo_restante, meta_batida da Partida; tamanho_max_fila da fila; selecionado
```

`pedidos` vai ordenado por id. Nunca segura dois locks ao mesmo tempo. Funciona antes de iniciar (tempo cheio, nada na fila) e depois do fim (valores congelados).

### Comandos do jogador

- `selecionar(id)`: guarda o cozinheiro selecionado (sob lock). Id inválido é ignorado.
- `atribuir(pedido_id)`: `fila.reservar(pedido_id, selecionado)` (spec 03). Sem selecionado, ou pedido que já saiu da fila, não faz nada.
- `pausar` / `retomar`: `partida` + `relogio`. As threads param sozinhas pelo `esperar_rodando`.

Todos chamados da thread da interface, com locks curtos. Não há fila de mensagens: a reserva já é a mensagem.

### Single player (`config.jogador`)

O cozinheiro 1 é um `CozinheiroJogador` (thread que executa comandos da tela); os outros são automáticos. Comandos, todos sem bloquear (vão para a fila de comandos do jogador):

- `pegar_pedido(pedido_id=None)`: pega esse pedido, ou o mais antigo livre. Se outro levou antes, a `mensagem` do jogador avisa.
- `usar_estacao(tipo)`: faz a etapa atual se `tipo` é uma das estações dela, pelo mesmo `ocupar_todas` dos automáticos (fila justa, ordem fixa).
- `desistir()`: esperando estação, sai da fila e mantém o pedido; parado com pedido, descarta (perdido).

Sem jogador, os três não fazem nada. O retrato marca o cozinheiro do jogador com `jogador=True`, a `proxima` etapa e a `mensagem`.

## Fora do escopo

- Reiniciar o mesmo `Jogo`: "jogar de novo" cria um `Jogo` novo (spec 08).

## Critérios de aceite (pytest)

- [x] Construir não inicia nenhuma thread (`threading.active_count()` não muda).
- [x] `iniciar` sobe `n_cozinheiros + 1` threads com nomes `cozinheiro-N` e `gerador`.
- [x] **Partida completa acelerada:** config com partida de 3 s e receitas de teste roda até VITORIA ou DERROTA sozinha (chamando `atualizar` em loop no teste) e `encerrar(timeout=2)` devolve `[]`.
- [x] Depois do fim, `retrato()` mostra placar e tempo iguais em chamadas separadas por 0,5 s.
- [x] `retrato()` funciona antes de iniciar, durante e depois de terminar.
- [x] `retrato()` chamado em loop por 1 s com o jogo rodando nunca levanta exceção, nunca tem id repetido em `pedidos`, e o p99 do tempo de cada chamada fica abaixo de 5 ms.
- [x] Pedido vencido na fila some do retrato e aumenta `perdidos`.
- [x] `selecionar(2)` + `atribuir(7)`: o pedido 7 aparece com `reservado_para=2` e é o C2 que o prepara.
- [x] `atribuir` sem cozinheiro selecionado não faz nada.
- [x] `encerrar()` com o jogo pausado devolve `[]` em menos de 1 s; chamar de novo também devolve `[]`.
- [x] Thread com `erro` faz o próximo `atualizar` levantar `RuntimeError`.
