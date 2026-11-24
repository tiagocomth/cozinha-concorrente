# Gerador de pedidos (05) e Jogo (07) — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar a thread que gera os clientes com aceleração e a fachada `Jogo`, que monta todas as peças, controla o ciclo de vida das threads e é a única porta entre a interface e a lógica.

**Architecture:** `cozinha/threads/gerador.py` é uma `threading.Thread` que espera um intervalo decrescente de tempo de jogo e coloca pedidos na fila (spec 03), com sorteio por um `random.Random` próprio. `cozinha/jogo.py` cria `Relogio`, `Pontuacao`, `Partida`, `Cozinha`, `FilaDePedidos`, o gerador e os cozinheiros; `atualizar` (1x por quadro) expira pedidos e checa o fim; `retrato` copia cada parte sob o próprio lock, uma de cada vez; `encerrar` para e espera as threads.

**Tech Stack:** Python ≥ 3.11 (`threading`, `random`, `logging`, `time`), pytest ≥ 8, pytest-timeout.

**Specs:** [docs/specs/05-gerador-de-pedidos.md](../../specs/05-gerador-de-pedidos.md), [docs/specs/07-jogo.md](../../specs/07-jogo.md). Usa tudo o que já está em `develop` (specs 00–04 e 06).

## Branches

| PR | Branch | Sai de | Tarefas |
| --- | --- | --- | --- |
| 1 | `feature/gerador-de-pedidos` | `develop` | 1–2 |
| 2 | `feature/jogo` | `feature/gerador-de-pedidos` (rebase em `develop` após o merge do PR 1) | 3–6 |

Ao fechar cada PR: critérios de aceite marcados na spec e **Status** mudado para "feita".

## APIs já existentes que este plano usa (não redefinir)

- `Relogio(fonte)`: `iniciar()`, `agora()`, `pausar()`, `retomar()`, `congelar()`, `pausado`, `esperar_rodando(parar, fatia=Config().tick)`.
- `Pontuacao(config)`: `registrar_perda(pedido)`, `valores() -> (pontos, entregues, perdidos)`.
- `Partida(config, relogio, pontuacao)`: `iniciar()`, `pausar()`, `retomar()`, `verificar_fim()`, `tempo_restante()`, `estado`, `terminou`, `meta_batida`. **`Partida.pausar/retomar` já pausam e retomam o `Relogio`**: o `Jogo` chama só a `Partida` (a spec 07 diz "partida + relogio"; chamar os dois não quebra nada, mas é redundante).
- `Cozinha(config)`: `views() -> (estacoes, grupos)`.
- `FilaDePedidos(tamanho_max)`: `colocar(criar, timeout)`, `reservar(pedido_id, cozinheiro_id) -> bool`, `remover_expirados(agora) -> list[Pedido]`, `views(agora)`, `tamanho_max`, `len()`.
- `Cozinheiro(id, fila, cozinha, pontuacao, relogio, config, parar)`: `view()`, `pedido_view(agora)`, `erro`, nome `cozinheiro-N`.
- Padrão de exceção do cozinheiro: `run` em `try/except BaseException`, `self.erro = exc` **antes** de qualquer outra coisa, depois `log.exception`.
- Fixture `fonte_falsa` em `tests/conftest.py`.

## Global Constraints

- Todo módulo começa com `from __future__ import annotations`; nada aqui importa `pygame`.
- Tempo de jogo sempre de `relogio.agora()`. A única fonte de tempo real é a `fonte_tempo` do `Jogo` (padrão `time.monotonic`).
- Nenhuma espera sem fim: toda espera acorda pelo menos a cada `config.tick`.
- Nunca segurar dois locks ao mesmo tempo para montar o `Retrato`.
- Fora o `encerrar`, nenhum método do `Jogo` bloqueia mais que um lock curto: todos são chamados da thread da interface.
- Testes com threads: `daemon=True`, todo `join` com `timeout` seguido de `assert not t.is_alive()`; todo teste que inicia um `Jogo` chama `encerrar()` num finalizador e confere que devolve `[]`.
- Commits em Conventional Commits; PR só entra com `pytest` verde.

## Review Focus

Entradas que as specs implicam e nenhum critério cobre. Cada uma tem teste na tarefa dona.

1. **`encerrar()` antes de `iniciar()`:** devolve `[]` sem tentar `join` em thread nunca iniciada (o que levantaria `RuntimeError`). → Tarefa 6.
2. **`iniciar()` depois de `encerrar()`:** não faz nada (threads não reiniciam; "jogar de novo" cria um `Jogo` novo, spec 07). → Tarefa 3.
3. **Pedido que aparece na fila e no cozinheiro no mesmo retrato** (desalinhamento de alguns milissegundos): aparece uma vez só, com a versão do cozinheiro. → Tarefa 4.
4. **`selecionar` com id inválido** (0, `n_cozinheiros + 1`): é ignorado e o selecionado anterior continua. → Tarefa 5.
5. **Pausa logo depois de um `colocar` em andamento no gerador:** no máximo um pedido entra até a pausa assentar; durante a pausa, nenhum. O teste espera a pausa assentar antes de medir. → Tarefa 2.

---

### Task 1: `GeradorDePedidos` — intervalo e sorteio

**Files:**
- Create: `cozinha/threads/gerador.py`
- Test: `tests/threads/test_gerador.py`

**Interfaces:**
- Consumes: `FilaDePedidos`, `Relogio`, `Config`, `Pedido`.
- Produces: `GeradorDePedidos(fila: FilaDePedidos, relogio: Relogio, config: Config, parar: threading.Event)`, subclasse de `threading.Thread` com `daemon=True` e `name="gerador"`; `run()`; `intervalo(decorrido: float) -> float`; `sortear() -> Receita`; atributo `erro: BaseException | None`.

- [ ] **Step 1: Escrever os testes que falham** (config `replace(Config(), duracao_partida=100, intervalo_inicial=8, intervalo_minimo=3)`):
  - `test_nome_e_daemon`: `name == "gerador"`, `daemon is True`, `erro is None`.
  - `test_intervalo`: `intervalo(0) == 8`, `intervalo(50) == 5.5`, `intervalo(100) == 3`, `intervalo(500) == 3`; decrescente em `[0, 10, …, 100]`.
  - `test_sorteio_reproduzivel`: dois geradores com `semente=42` produzem a mesma sequência de 20 `sortear().nome`; com `semente=None` e as três receitas padrão, 60 sorteios cobrem as três.
- [ ] **Step 2: Rodar** `pytest tests/threads/test_gerador.py -v` → FAIL.
- [ ] **Step 3: Implementar** `intervalo` exatamente com a fórmula linear da spec 05 e `sortear` com `self._rng = random.Random(config.semente)` e `self._rng.choice(config.receitas)`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(threads): intervalo e sorteio do gerador`.

### Task 2: `GeradorDePedidos` — loop, fila cheia, pausa e exceção

**Files:**
- Modify: `cozinha/threads/gerador.py`, `tests/threads/test_gerador.py`, `docs/specs/05-gerador-de-pedidos.md`

- [ ] **Step 1: Escrever os testes que falham** (montagem: `tick=0.005`, `intervalo_inicial=0.05`, `intervalo_minimo=0.05`, `Relogio()` real iniciado, `FilaDePedidos(4)`, `parar = Event()`; finalizador com `parar.set()`, `relogio.congelar()` e `join(timeout=1)`):
  - `test_primeiro_pedido_logo`: com `intervalo_inicial=10`, em até 0,2 s há 1 pedido na fila.
  - `test_ids_sequenciais`: um consumidor retirando continuamente; depois de 0,5 s, os ids retirados são `[1, 2, …, n]` sem repetir nem pular, com `n >= 3`.
  - `test_fila_enche_e_espera`: sem consumidor; em até 1 s `len(fila) == 4`; depois de mais 0,2 s continua 4; ao retirar 1, em até 0,2 s volta a 4; os ids na fila continuam consecutivos (nenhum pedido foi criado fora dela).
  - `test_pausa_nao_coloca` *(Review Focus 5)*: com a fila sendo esvaziada por um consumidor, pausa; espere 0,05 s para assentar; anote o maior id visto; espere 1 s; nenhum id novo; retome e chegam novos.
  - `test_parar_com_fila_cheia`: fila cheia; `parar.set()` → `join(timeout=1)` termina.
  - `test_excecao_preenche_erro`: `monkeypatch` de `cozinha.threads.gerador.Pedido` por uma função que levanta `RuntimeError("boom")`, para a criação do pedido falhar → a thread termina em 1 s e `isinstance(g.erro, RuntimeError)`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar o loop** da spec 05: primeiro pedido logo no início; depois espera `intervalo(relogio.agora())` em ticks de tempo de jogo pausáveis (`esperar_rodando` + `parar.wait(tick)`, somando o avanço de `agora()`); sorteia uma receita; tenta `fila.colocar(lambda: Pedido(self._proximo_id(), receita, relogio.agora()), timeout=tick)` em laço (com `esperar_rodando` antes de cada tentativa) até conseguir ou `parar`. O id só é consumido dentro do `criar`, que a fila só chama quando há vaga. `run` em `try/except BaseException` com `self.erro = exc` primeiro, depois `log.exception`.
- [ ] **Step 4: Rodar** → PASS; repetir o arquivo 10 vezes.
- [ ] **Step 5: Marcar os critérios** da spec 05 e mudar o Status para "feita".
- [ ] **Step 6: Commit** `feat(threads): gerador de pedidos` e abra o PR 1.

### Task 3: `Jogo` — montagem, `iniciar` e `atualizar`

**Files:**
- Create: `cozinha/jogo.py`
- Test: `tests/test_jogo.py`

**Interfaces:**
- Consumes: todas as peças acima e `GeradorDePedidos` (Tasks 1–2).
- Produces: `Jogo(config: Config, fonte_tempo: Callable[[], float] = time.monotonic)` com `iniciar() -> None`, `atualizar() -> None`. Atributos internos usados nos testes: `_cozinheiros: list[Cozinheiro]`, `_gerador`, `_fila`, `_pontuacao`, `_partida`, `_relogio`, `_parar`.

Config de teste compartilhada (fixture `config_rapida` em `tests/test_jogo.py`): `duracao_partida=3`, `n_cozinheiros=2`, `tick=0.005`, `tempo_retirada=0`, `intervalo_inicial=0.1`, `intervalo_minimo=0.05`, `semente=1`, receitas de teste com etapas de 0,01 s e paciência 2 s. Fixture `jogo` que cria, entrega e no fim faz `assert jogo.encerrar(timeout=2) == []`.

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_construir_nao_inicia_threads`: `threading.active_count()` igual antes e depois de `Jogo(config)`.
  - `test_iniciar_sobe_threads`: depois de `iniciar()`, os nomes das threads vivas incluem `gerador`, `cozinheiro-1` e `cozinheiro-2`; `active_count()` subiu exatamente `n_cozinheiros + 1`.
  - `test_iniciar_duas_vezes`: a segunda chamada não sobe threads nem levanta.
  - `test_iniciar_depois_de_encerrar` *(Review Focus 2)*: `iniciar()`, `encerrar()`, `iniciar()` → nenhuma thread nova e nenhuma exceção.
  - `test_pedido_vencido_vira_perdido`: tempo real, `n_cozinheiros=1`, receita com etapa de 5 s e paciência 0,1 s, para a fila acumular pedidos que ninguém pega; chame `atualizar()` em laço por 0,5 s → `valores()[2] > 0` e nenhum pedido vencido continua em `fila.views(agora)`.
  - `test_atualizar_parado_nao_faz_nada`: antes de `iniciar()` e com a partida pausada, `atualizar()` não muda `valores()` nem a fila.
  - `test_erro_de_thread_levanta`: depois de `iniciar()`, `jogo._cozinheiros[0].erro = ValueError("x")` → `atualizar()` levanta `RuntimeError` cujo `__cause__` é esse `ValueError`, e `jogo._parar.is_set()`.
  - `test_fim_sinaliza_parada`: com `fonte_falsa`, `iniciar()`, avance 3 s, `atualizar()` → `partida.terminou`, `_parar.is_set()`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** a montagem na ordem da spec 07 (sem iniciar threads), `iniciar` idempotente (flags `_iniciado` e `_encerrado`), `atualizar` com os quatro passos da spec 07 (`raise RuntimeError(...) from erro`) e `_sinalizar_parada()` (`parar.set()` + `relogio.congelar()`).
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat: jogo monta, inicia e atualiza`.

### Task 4: `Jogo.retrato`

**Files:**
- Modify: `cozinha/jogo.py`, `tests/test_jogo.py`

**Interfaces:**
- Produces: `retrato() -> Retrato`, com os campos da spec 00 (`estado`, `tempo_restante`, `pontos`, `meta`, `meta_batida`, `perdidos`, `limite_perdidos`, `entregues`, `tamanho_max_fila`, `pedidos`, `cozinheiros`, `estacoes`, `grupos`, `selecionado`).

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_retrato_antes_de_iniciar`: `estado is PRONTA`, `tempo_restante == duracao_partida`, `pedidos == ()`, um `CozinheiroView` LIVRE por cozinheiro, `selecionado is None`.
  - `test_retrato_em_loop`: com o jogo rodando, `retrato()` + `atualizar()` em laço por 1 s; nunca levanta, nunca há id repetido em `pedidos`, `pedidos` sempre ordenado por id; o p99 do tempo de `retrato()` fica abaixo de 5 ms.
  - `test_retrato_congela_no_fim`: com `fonte_falsa`, avance até o fim, `atualizar()`; dois retratos separados por 0,5 s têm os mesmos `pontos`, `perdidos`, `entregues` e `tempo_restante`.
  - `test_retrato_sem_repetidos` *(Review Focus 3)*: monte o caso com um pedido na fila e o mesmo pedido como `pedido_view` de um cozinheiro (use `monkeypatch` em `jogo._cozinheiros[0].pedido_view` para devolver um `PedidoView` EM_PREPARO com o id de um pedido que está na fila) → o retrato tem esse id uma vez, com `estado is EM_PREPARO`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** como o esboço da spec 07: cada parte copiada sob o próprio lock, uma de cada vez; dicionário `{id: view}` da fila, depois o dos cozinheiros por cima; `pedidos` ordenado por id; `meta`, `limite_perdidos` da config; `tamanho_max_fila` da fila; `selecionado` lido sob o lock do `Jogo`.
- [ ] **Step 4: Rodar** → PASS; repetir `test_retrato_em_loop` 5 vezes.
- [ ] **Step 5: Commit** `feat: retrato do jogo para a interface`.

### Task 5: Comandos do jogador

**Files:**
- Modify: `cozinha/jogo.py`, `tests/test_jogo.py`

**Interfaces:**
- Produces: `selecionar(cozinheiro_id: int) -> None`, `atribuir(pedido_id: int) -> None`, `pausar() -> None`, `retomar() -> None`.

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_selecionar_e_atribuir`: com `n_cozinheiros=2` e cozinheiros lentos (etapa de 0,3 s), espere um pedido AGUARDANDO no retrato; `selecionar(2)` + `atribuir(id)` → o retrato mostra esse pedido com `reservado_para == 2` (ou já EM_PREPARO com `cozinheiro_id == 2`); em até 2 s ele é preparado pelo C2.
  - `test_atribuir_sem_selecionado`: `atribuir(id)` sem `selecionar` → `reservado_para` continua `None`.
  - `test_selecionar_invalido` *(Review Focus 4)*: `selecionar(2)`, depois `selecionar(0)` e `selecionar(3)` → `retrato().selecionado == 2`.
  - `test_pausar_e_retomar`: `pausar()` → `retrato().estado is PAUSADA` e `tempo_restante` não muda em 0,2 s; `retomar()` → RODANDO.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** `selecionar` aceita só `1..n_cozinheiros` (sob o lock do `Jogo`). `atribuir` chama `fila.reservar(pedido_id, selecionado)` se houver selecionado. `pausar`/`retomar` chamam só a `Partida`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat: comandos do jogador`.

### Task 6: `encerrar` e partida completa

**Files:**
- Modify: `cozinha/jogo.py`, `tests/test_jogo.py`, `docs/specs/07-jogo.md`

**Interfaces:**
- Produces: `encerrar(timeout: float = 2.0) -> list[str]` (nomes das threads que não terminaram).

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_encerrar_antes_de_iniciar` *(Review Focus 1)*: `Jogo(config).encerrar() == []`.
  - `test_encerrar_pausado`: `iniciar()`, `pausar()`, `encerrar()` devolve `[]` em menos de 1 s; chamar de novo também devolve `[]`.
  - `test_encerrar_informa_presas`: troque uma thread por um stub que ignora o `parar` (`threading.Thread(target=time.sleep, args=(3,), daemon=True, name="presa")` iniciada e colocada em `jogo._cozinheiros`) → `encerrar(timeout=0.2) == ["presa"]`.
  - `test_partida_completa`: `iniciar()` e `atualizar()` em laço (a cada 10 ms) até `partida.terminou`, com prazo de 6 s; o estado final é VITORIA ou DERROTA; `entregues + perdidos > 0`; `encerrar(timeout=2) == []`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** `encerrar` como na spec 07: `_sinalizar_parada()` e `join` em todas as threads **já iniciadas** (`t.ident is not None`), dividindo o `timeout` entre elas; devolve os nomes das vivas e loga um aviso quando a lista não está vazia. Marque `_encerrado = True`.
- [ ] **Step 4: Rodar** `pytest -v` (suíte inteira) → verde; repetir `tests/test_jogo.py` 5 vezes.
- [ ] **Step 5: Marcar os critérios** da spec 07 e mudar o Status para "feita".
- [ ] **Step 6: Commit** `feat: encerrar e partida completa` e abra o PR 2.
