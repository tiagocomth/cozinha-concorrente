# Fila de pedidos (03) e Cozinheiro (04) — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar a fila produtor-consumidor com reservas do jogador e a thread do cozinheiro que prepara os pratos nas estações, destravando as specs 05 e 07.

**Architecture:** `cozinha/modelo/fila.py` é o produtor-consumidor clássico com três `threading.Semaphore` (vagas, disponíveis, mutex) e um dicionário de reservas. `cozinha/threads/cozinheiro.py` é uma `threading.Thread` que retira da fila, adquire as estações de cada etapa pela `Cozinha` (spec 02), trabalha em ticks de tempo de jogo e registra entrega ou perda na `Pontuacao` (spec 06). O estado para a tela fica sob um `Lock` do próprio cozinheiro.

**Tech Stack:** Python ≥ 3.11 (`threading`, `dataclasses`, `logging`), pytest ≥ 8, pytest-timeout.

**Specs:** [docs/specs/03-fila-de-pedidos.md](../../specs/03-fila-de-pedidos.md), [docs/specs/04-cozinheiro.md](../../specs/04-cozinheiro.md). Usa o que já está em `develop`: `Config`, `Pedido`, `PedidoView`, `CozinheiroView` (spec 00); `Cozinha`, `Reserva` (spec 02); `Relogio`, `Pontuacao` (spec 06).

## Branches

| PR | Branch | Sai de | Tarefas |
| --- | --- | --- | --- |
| 1 | `feature/fila-de-pedidos` | `develop` | 1–2 |
| 2 | `feature/cozinheiro` | `feature/fila-de-pedidos` (rebase em `develop` após o merge do PR 1) | 3–6 |

Ao fechar cada PR: critérios de aceite marcados na spec e **Status** mudado para "feita".

## APIs já existentes que este plano usa (não redefinir)

- `Relogio.agora() -> float`, `Relogio.esperar_rodando(parar, fatia=Config().tick)`, `Relogio.pausar()/retomar()`.
- `Pontuacao.registrar_entrega(pedido, agora) -> int`, `registrar_perda(pedido)`; registrar o mesmo pedido duas vezes levanta `ValueError`; depois de `fechar()`, registros são ignorados.
- `Cozinha.ocupar_todas(dono, tipos, cancelar, ao_mudar) -> tuple[Reserva, ...] | None`; `Cozinha.liberar(reservas)` aceita uma parte das reservas e levanta `ValueError` para reserva não ocupada ou repetida; `ao_mudar(segurando: tuple[Reserva, ...], esperando: TipoEstacao | None)`. Se `ao_mudar` levantar exceção, `ocupar_todas` solta o que pegou e repassa o erro.
- `Etapa.entrega` é `True` na etapa que usa BALCÃO, que é sempre a última.
- Fixture `fonte_falsa` em `tests/conftest.py` (`avancar(s)`).

## Global Constraints

- Todo módulo começa com `from __future__ import annotations`; nada aqui importa `pygame`.
- Tempo de jogo sempre de `relogio.agora()`; nunca `time.time()` na lógica.
- Nenhuma espera sem fim: toda espera acorda pelo menos a cada `config.tick`.
- Nunca segurar um lock e esperar outro. Na fila, o mutex é sempre o último pego e o primeiro solto; `criar()` roda fora dele.
- Quem marca ENTREGUE/PERDIDO é só a `Pontuacao`. A fila marca AGUARDANDO → EM_PREPARO e `cozinheiro_id`.
- Testes com threads: `daemon=True`, todo `join` com `timeout` seguido de `assert not t.is_alive()`. Nos testes do cozinheiro, use `tick=0.005` e etapas de 0,01 s.
- Commits em Conventional Commits; PR só entra com `pytest` verde.

## Review Focus

Entradas que as specs implicam e nenhum critério cobre. Cada uma tem teste na tarefa dona.

1. **Duas ordens para o mesmo pedido:** `reservar(7, C1)` e depois `reservar(7, C2)` → vale a última (o pedido fica reservado para C2, e C1 volta a pegar qualquer pedido livre). → Tarefa 1.
2. **Exceção depois de a entrega já ter sido registrada:** o tratador do `run` não chama `registrar_perda` (que levantaria `ValueError` de duplicado e esconderia o erro original); só registra perda se o pedido ainda está EM_PREPARO. → Tarefa 6.
3. **`parar` durante a retirada no balcão:** sai sem registrar entrega e solta o balcão. → Tarefa 5.
4. **Pausa com o cozinheiro LIVRE:** ele não retira pedido da fila enquanto o relógio está pausado (o `esperar_rodando` vem antes do `retirar`). → Tarefa 3.
5. **Pedido que expira enquanto o relógio está pausado:** não expira, porque `agora()` fica parado; ao retomar, o cozinheiro continua normalmente. → Tarefa 4.

---

### Task 1: `FilaDePedidos` — colocar, retirar e reservar

**Files:**
- Create: `cozinha/modelo/fila.py`
- Test: `tests/modelo/test_fila.py`

**Interfaces:**
- Consumes: `Pedido`, `EstadoPedido` (spec 00).
- Produces: `FilaDePedidos(tamanho_max: int)` com `colocar(criar: Callable[[], Pedido], timeout: float) -> Pedido | None`, `retirar(cozinheiro_id: int, timeout: float) -> Pedido | None`, `reservar(pedido_id: int, cozinheiro_id: int) -> bool`, propriedade `tamanho_max -> int`, `__len__() -> int`.

- [ ] **Step 1: Escrever os testes que falham** (helper `_criador()` que devolve uma função criando `Pedido(id sequencial, RECEITAS[0], criado_em=0.0)` e conta as chamadas):
  - `test_colocar_e_retirar`: coloca 1 e retira com C1 → mesmo pedido, `estado is EM_PREPARO`, `cozinheiro_id == 1`, `len(fila) == 0`.
  - `test_ordem_fifo`: coloca 1, 2, 3; retiradas devolvem 1, 2, 3.
  - `test_fila_cheia_nao_cria`: `tamanho_max=2`, coloca 2; `colocar(criar, timeout=0.05)` devolve `None` e `criar` foi chamado só 2 vezes.
  - `test_fila_vazia`: `retirar(1, timeout=0.05) is None`.
  - `test_reserva`: pedidos 1..3; `reservar(2, 2)`; C1 retira → 1; C1 retira → 3; C1 retira com `timeout=0.05` → `None`; C2 retira → 2.
  - `test_reserva_substitui`: `reservar(1, 2)` e `reservar(3, 2)`; C1 retira → 1 (não está mais reservado).
  - `test_duas_ordens_mesmo_pedido` *(Review Focus 1)*: `reservar(1, 1)` e `reservar(1, 2)`; C1 retira com `timeout=0.05` com só o pedido 1 na fila → `None`; C2 retira → 1.
  - `test_so_reservados_devolve_ficha`: único pedido reservado para C2; `retirar(1, 0.05) is None`; depois `retirar(2, 0.05)` devolve o pedido.
  - `test_reservar_pedido_ausente`: `reservar(99, 1) is False`.
  - `test_sem_duplicado`: `tamanho_max=6`; 2 produtores × 250 `colocar(timeout=0.05)` em laço até conseguir, 4 consumidores retirando até um `Event` de fim; cada id sai exatamente uma vez (500 ids); um observador amostra `len(fila) <= 6` o tempo todo.
- [ ] **Step 2: Rodar** `pytest tests/modelo/test_fila.py -v` → FAIL.
- [ ] **Step 3: Implementar** exatamente os passos de `colocar`, `reservar` e `retirar` da spec 03 (três `threading.Semaphore`; `criar()` fora do mutex; ao retirar, procura primeiro a reserva deste cozinheiro, depois o mais antigo não reservado para outro; ficha devolvida quando só há reservados para outros). Em `reservar`, apague as reservas anteriores do mesmo cozinheiro antes de gravar a nova; como o dicionário é `pedido_id → cozinheiro_id`, gravar substitui a ordem anterior para o mesmo pedido.
- [ ] **Step 4: Rodar** → PASS; repetir `test_sem_duplicado` 20 vezes.
- [ ] **Step 5: Commit** `feat(modelo): fila de pedidos produtor-consumidor`.

### Task 2: `FilaDePedidos` — expiração e views

**Files:**
- Modify: `cozinha/modelo/fila.py`, `tests/modelo/test_fila.py`, `docs/specs/03-fila-de-pedidos.md`

**Interfaces:**
- Produces: `remover_expirados(agora: float) -> list[Pedido]`; `views(agora: float) -> tuple[PedidoView, ...]`, um por pedido na fila, ordenado por id, com `estado=AGUARDANDO`, `paciencia=pedido.paciencia_restante(agora)`, `cozinheiro_id=None`, `reservado_para` vindo das reservas.

- [ ] **Step 1: Escrever os testes que falham** (receita de paciência 10):
  - `test_remover_expirados`: pedidos criados em 0 e em 5; `reservar` o primeiro para C2; `remover_expirados(12)` devolve só o primeiro, com `estado` ainda AGUARDANDO; `len(fila) == 1`; `views(12)` não mostra reserva.
  - `test_expirar_libera_vaga`: `tamanho_max=1`, um pedido vencido; depois de `remover_expirados`, um `colocar(timeout=0.05)` funciona.
  - `test_ficha_fantasma`: coloca 2, expira os 2; `retirar(1, 0.05)` devolve `None` (até duas vezes, uma por ficha fantasma); depois coloca 1 e `retirar` devolve esse pedido.
  - `test_estresse_com_expiracao`: o estresse da Task 1 com uma thread chamando `remover_expirados` com `agora` crescente; todo id sai exatamente uma vez, ou pela retirada ou pela expiração; ninguém fica preso (`join(timeout=10)`).
  - `test_views`: pedidos 1 e 2, `reservar(2, 3)`; `views(0)` devolve dois `PedidoView` em ordem de id, `paciencia == 1.0`, o segundo com `reservado_para == 3`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** `remover_expirados` como na spec 03 (vaga liberada para cada removido; não mexe em `disponiveis` nem no estado) e `views` sob o mutex.
- [ ] **Step 4: Rodar** → PASS; repetir os testes de estresse 20 vezes.
- [ ] **Step 5: Marcar os critérios** da spec 03 e mudar o Status para "feita".
- [ ] **Step 6: Commit** `feat(modelo): expiracao e views da fila` e abra o PR 1.

### Task 3: `Cozinheiro` — esqueleto, loop e etapa simples

**Files:**
- Create: `cozinha/threads/cozinheiro.py`
- Test: `tests/threads/__init__.py`, `tests/threads/test_cozinheiro.py`

**Interfaces:**
- Consumes: `FilaDePedidos` (Tasks 1–2), `Cozinha`, `Reserva`, `Relogio`, `Pontuacao`, `Config`.
- Produces: `Cozinheiro(id: int, fila: FilaDePedidos, cozinha: Cozinha, pontuacao: Pontuacao, relogio: Relogio, config: Config, parar: threading.Event)`, subclasse de `threading.Thread` com `daemon=True` e `name=f"cozinheiro-{id}"`; `run()`; `view() -> CozinheiroView`; `pedido_view(agora: float) -> PedidoView | None`; atributo `erro: BaseException | None` (começa `None`).

Montagem compartilhada dos testes (fixture `montar` em `tests/threads/test_cozinheiro.py`): `config = replace(Config(), tick=0.005, tempo_retirada=0, receitas=(...))` com receitas de teste de etapas de 0,01 s (Salada: cortar TÁBUA 0,01 → entregar BALCÃO 0,01; Sopa: cortar → cozinhar FOGÃO 0,01 → empratar FOGÃO+BALCÃO 0,01; paciência 60 s, para nada expirar sem querer; testes de expiração criam a própria receita), `Relogio()` real já iniciado, `Pontuacao(config)`, `Cozinha(config)`, `FilaDePedidos(config.tamanho_max_fila)`, `parar = Event()`. Um finalizador sempre faz `parar.set()` e `join(timeout=1)` em todos os cozinheiros criados.

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_nome_e_daemon`: `name == "cozinheiro-1"`, `daemon is True`, `erro is None`, `view().estado is LIVRE`.
  - `test_salada_entregue`: um cozinheiro, uma Salada na fila → em até 1 s o pedido fica ENTREGUE e `pontuacao.valores()[0] > 0`; `view()` volta a LIVRE.
  - `test_solta_tudo`: depois da entrega, `cozinha.views()` não tem nenhuma estação com `ocupada_por == 1`.
  - `test_pega_o_reservado`: pedidos 1 e 2; `fila.reservar(2, 1)` antes de iniciar → o primeiro pedido que o cozinheiro 1 entrega é o 2.
  - `test_livre_nao_retira_na_pausa` *(Review Focus 4)*: relógio pausado antes de iniciar o cozinheiro; pedido na fila; depois de 0,2 s, `len(fila) == 1`; ao retomar, o pedido é entregue.
  - `test_parar_livre`: sem pedidos, `parar.set()` → `join(timeout=1)` termina.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar o loop** da spec 04: `esperar_rodando(parar, config.tick)` → `fila.retirar(id, timeout=config.tick)` → sem pedido, `parar.wait(config.tick)` e continua → para cada etapa: `ocupar_todas(id, etapa.estacoes, cancelar, self._ao_mudar)`; trabalhar `etapa.duracao`; entrega simples (registrar e soltar); `liberar` em `finally`. Estado da tela sob `self._lock`: `estado`, `pedido`, `etapa`, `progresso`, `segurando` (tupla de `(tipo, indice)`), `esperando`, `esperando_desde`, `espera_total`. `_ao_mudar(segurando, esperando)` converte cada `Reserva` em `(reserva.tipo, reserva.indice)` (decisão do grupo, spec 04), muda `estado` para ESPERANDO quando `esperando` não é `None` e acumula `espera_total` quando a espera acaba. `view()` calcula `esperando_ha = relogio.agora() - esperando_desde` (0 sem espera).
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(threads): cozinheiro prepara pedidos`.

### Task 4: Trabalho em ticks, pausa e expiração

**Files:**
- Modify: `cozinha/threads/cozinheiro.py`, `tests/threads/test_cozinheiro.py`

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_pausa_congela_progresso`: etapa de 0,5 s; quando `view().estado is TRABALHANDO` e `progresso > 0`, pausa; leia `progresso`, espere 0,2 s, leia de novo → igual; retome e o pedido termina.
  - `test_expira_em_etapa_normal`: receita com paciência 0,05 e etapa de 0,5 s → o pedido vira PERDIDO, `valores()[2] == 1` e nenhuma estação fica ocupada.
  - `test_expira_esperando_estacao`: a tábua (única, `quantidade[TABUA]=1`) ocupada pelo teste via `cozinha.ocupar_todas(99, (TABUA,), ...)`; pedido de paciência 0,1 → PERDIDO, e o cozinheiro some da `fila_espera` da TÁBUA.
  - `test_sem_expiracao_na_demo`: `expiracao=False`, paciência 0,05, etapa de 0,2 s → ENTREGUE.
  - `test_pausa_nao_expira` *(Review Focus 5)*: paciência 0,3, etapa de 0,2 s; pausa logo que o cozinheiro começa a trabalhar, espere 0,5 s, retome → ENTREGUE.
  - `test_estacao_na_pausa_espera_retomar`: tábua ocupada pelo teste; cozinheiro esperando; pausa; o teste solta a tábua; depois de 0,1 s o `progresso` é 0 (pegou a tábua mas não trabalha); retome → ENTREGUE.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** `cancelar = lambda: parar.is_set() or (config.expiracao and pedido.expirou(relogio.agora()))`. Expiração checada antes de cada etapa e a cada tick do trabalho (exceto na etapa de entrega depois de pegar o balcão). Trabalhar = laço que chama `esperar_rodando`, `parar.wait(config.tick)` e soma o avanço de `relogio.agora()` até atingir `duracao`, atualizando `progresso` sob o lock. Depois de `ocupar_todas` devolver as reservas, chame `esperar_rodando` antes de começar. Expirou → solta tudo e `pontuacao.registrar_perda(pedido)`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(threads): trabalho em ticks com pausa e expiracao`.

### Task 5: Entrega no balcão e parada

**Files:**
- Modify: `cozinha/threads/cozinheiro.py`, `tests/threads/test_cozinheiro.py`

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_empratar_solta_fogao_antes`: Sopa com `tempo_retirada=0.2`; quando o balcão está ocupado pelo cozinheiro na retirada, o fogão já está livre em `cozinha.views()`.
  - `test_balcao_cheio_bloqueia`: `quantidade[BALCAO]=1`, `tempo_retirada=0.3`, dois cozinheiros e duas Saladas; em algum momento C2 aparece com `view().estado is ESPERANDO` e `esperando is BALCAO` enquanto C1 segura o balcão; os dois pedidos terminam ENTREGUE.
  - `test_view_segurando_e_esperando`: 1 fogão, balcão de capacidade 1 ocupado pelo teste; Sopa → em algum momento `view().segurando == ((FOGAO, 0),)` e `view().esperando is BALCAO`.
  - `test_expira_na_retirada_conta_entregue`: paciência que acaba durante o `tempo_retirada` → ENTREGUE.
  - `test_parar_no_meio_da_etapa`: etapa de 5 s; quando TRABALHANDO, `parar.set()` → `join(timeout=1)` termina, nada ocupado, pedido não registrado (`valores() == (0, 0, 0)`).
  - `test_parar_na_retirada` *(Review Focus 3)*: `tempo_retirada=5`; quando o balcão está ocupado na retirada, `parar.set()` → termina em 1 s, balcão livre, `valores() == (0, 0, 0)`.
  - `test_pedido_view`: durante o preparo, `pedido_view(agora)` mostra o pedido EM_PREPARO com o `cozinheiro_id` certo; depois da entrega, `None`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar a etapa de entrega:** trabalha `duracao` sem checar expiração; solta as reservas que não são BALCÃO; espera `config.tempo_retirada` em ticks pausáveis (mesmo laço do trabalho, sem expiração); `registrar_entrega(pedido, relogio.agora())`; solta o balcão no `finally`. Com `parar`, interrompe no próximo tick, solta tudo e sai do `run` sem registrar. `pedido_view` devolve `None` quando não há pedido ou ele já está ENTREGUE/PERDIDO.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(threads): entrega no balcao e parada`.

### Task 6: Exceções e estresse

**Files:**
- Modify: `cozinha/threads/cozinheiro.py`, `tests/threads/test_cozinheiro.py`, `docs/specs/04-cozinheiro.md`

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_excecao_preenche_erro`: receita com uma etapa inválida injetada (`object.__setattr__(etapa, "estacoes", (99,))`, que faz a `Cozinha` levantar `KeyError`) → em até 1 s a thread termina, `isinstance(c.erro, KeyError)`, o pedido fica PERDIDO e nenhuma estação fica ocupada.
  - `test_excecao_depois_da_entrega` *(Review Focus 2)*: `monkeypatch` de `pontuacao.registrar_entrega` por uma função que chama a original e depois levanta `RuntimeError("boom")` → `c.erro` é esse `RuntimeError` (não um `ValueError` de duplicado), o pedido continua ENTREGUE e `valores()[2] == 0`.
  - `test_estresse`: 4 cozinheiros, 100 Saladas e Sopas misturadas, balcão de capacidade 1, `tempo_retirada=0`, um produtor colocando os 100 pedidos com `colocar` em laço; espera até `entregues + perdidos == 100` (prazo de 10 s); `parar.set()`; `join(timeout=10)` sem nenhuma viva; todos os pedidos ENTREGUE ou PERDIDO; nenhum `erro`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** o `try/except BaseException` em volta do `run` inteiro: solta o que estiver segurando, registra perda do pedido atual **só se** ele ainda está EM_PREPARO (e a `Pontuacao` não foi fechada), guarda a exceção em `self.erro` e loga com `logging.getLogger(__name__).exception`.
- [ ] **Step 4: Rodar** `pytest -v` (suíte inteira) → verde; repetir `test_estresse` 10 vezes.
- [ ] **Step 5: Marcar os critérios** da spec 04 e mudar o Status para "feita".
- [ ] **Step 6: Commit** `feat(threads): cozinheiro nunca morre em silencio` e abra o PR 2.
