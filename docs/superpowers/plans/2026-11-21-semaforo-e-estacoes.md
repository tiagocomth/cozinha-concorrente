# Semáforo justo (01) e Estações (02) — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o `SemaforoJusto` (FIFO, sem inanição) e as estações da cozinha com aquisição em ordem fixa (sem deadlock), destravando a spec 04.

**Architecture:** `cozinha/sync.py` tem um semáforo contador sobre `threading.Condition` e uma fila de senhas; a thread espera em fatias sem sair da fila. `cozinha/modelo/estacoes.py` usa um `SemaforoJusto` por tipo de estação (`GrupoDeEstacoes`) e uma `Cozinha` que adquire vários tipos sempre em ordem crescente de `TipoEstacao`.

**Tech Stack:** Python ≥ 3.11 (`threading`, `dataclasses`, `collections.deque`), pytest ≥ 8, pytest-timeout.

**Specs:** [docs/specs/01-semaforo-justo.md](../../specs/01-semaforo-justo.md), [docs/specs/02-estacoes.md](../../specs/02-estacoes.md). Usa os contratos da [spec 00](../../specs/00-contratos.md), já implementados (`Config`, `TipoEstacao`, `EstacaoView`, `GrupoView`).

## Pré-requisito e branches

O PR da spec 00 ([tiagocomth/cozinha-concorrente#2](https://github.com/tiagocomth/cozinha-concorrente/pull/2)) precisa estar mesclado em `develop`. Se ainda não estiver, saia de `feature/contratos` e faça rebase depois.

| PR | Branch | Sai de | Tarefas |
| --- | --- | --- | --- |
| 1 | `feature/semaforo-justo` | `develop` | 1–2 |
| 2 | `feature/estacoes` | `feature/semaforo-justo` (rebase em `develop` após o merge do PR 1) | 3–5 |

Ao fechar cada PR: critérios de aceite marcados na spec e **Status** mudado para "feita".

## Decisões já tomadas pelo grupo (aplicar nas specs dentro destes PRs)

1. **Justiça por ordem de chegada, não por igualdade de usos.** O critério "Justiça: diferença de usos < 10%" da spec 01 sai. Ele contradiz o plano da equipe e é instável. No lugar dele entra o critério "Sem inanição": uma thread que chega com o semáforo disputado por 4 threads em laço é atendida antes de qualquer thread que chegou depois dela. → Tarefa 2.
2. **`ao_mudar` recebe `Reserva`.** A `Cozinha` passa `tuple[Reserva, ...]`; o cozinheiro (spec 04) converte em `(tipo, indice)` para o `CozinheiroView.segurando`. O critério da spec 02 passa a dizer `(Reserva(FOGAO, i),), BALCAO`, e a spec 04 ganha uma linha registrando a conversão. → Tarefa 4.
3. **`GrupoView.fila_espera` vem direto de `semaforo.esperando()`.** → Tarefa 3.
4. **O `cancelar` cobre o `parar`.** É ele que tira as threads da espera, no encerramento e na demo de deadlock. → Tarefas 1, 4 e 5.

## Global Constraints

- Todo módulo começa com `from __future__ import annotations`; nada aqui importa `pygame`.
- Nenhuma espera sem fim: toda espera acorda pelo menos a cada `fatia` (`config.tick`, padrão 0.05).
- Nunca segurar um lock e esperar outro, exceto na aquisição de estações em ordem fixa.
- O `timeout` do semáforo é tempo real (`time.monotonic`), não tempo de jogo.
- Testes com threads: `daemon=True`, todo `join` com `timeout` seguido de `assert not t.is_alive()`. Tolerâncias explícitas ("entre 0,04 e 0,5 s").
- Para sincronizar a ordem de chegada nos testes, espere a thread aparecer em `esperando()` (laço com `time.sleep(0.005)` e prazo de 1 s), nunca um `sleep` fixo.
- Commits em Conventional Commits; PR só entra com `pytest` verde.

## Review Focus

Entradas que as specs implicam e nenhum critério cobre. Cada uma tem teste na tarefa dona.

1. **`cancelar()` já verdadeiro, com vaga livre e fila vazia:** `acquire` passa (devolve `True`), como no esboço da spec: a condição de passagem é checada antes do cancelamento. → Tarefa 1.
2. **`timeout=0` com vaga livre:** devolve `True` na hora; com o semáforo ocupado, devolve `False` sem esperar e não deixa senha na fila. → Tarefa 2.
3. **`Cozinha.liberar` com uma `Reserva` de um tipo que não existe ou de índice fora do grupo:** levanta `ValueError`, sem soltar nada. → Tarefa 3.
4. **`ocupar_todas` com `tipos` vazio:** devolve `()` sem chamar `ao_mudar`. → Tarefa 4.
5. **Modo demo com id ímpar:** pega na ordem normal; só os ids pares invertem. → Tarefa 5.

---

### Task 1: `SemaforoJusto` — exclusão, capacidade e release

**Files:**
- Create: `cozinha/sync.py`
- Test: `tests/test_sync.py`

**Interfaces:**
- Produces: `SemaforoJusto(valor: int)` com `acquire(dono: int, timeout: float | None = None, cancelar: Callable[[], bool] | None = None, fatia: float = 0.05) -> bool`, `release() -> None`, propriedades `disponivel -> int` e `capacidade -> int`, `esperando() -> tuple[int, ...]`.

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_valor_invalido`: `SemaforoJusto(0)` levanta `ValueError`.
  - `test_exclusao`: `valor=1`, 8 threads × 200 voltas de `acquire(i)`/incrementa contador sob `Lock`/registra máximo/decrementa/`release()`; máximo observado `== 1`.
  - `test_capacidade`: o mesmo com `valor=2` e um `time.sleep(0.001)` dentro; máximo `== 2`.
  - `test_release_sobrando`: `release()` sem `acquire` levanta `ValueError`; `disponivel == capacidade` depois.
  - `test_disponivel`: `valor=2`, um `acquire` → `disponivel == 1`, `capacidade == 2`.
  - `test_cancelar_com_vaga_livre_passa` *(Review Focus 1)*: `acquire(1, cancelar=lambda: True) is True`.
- [ ] **Step 2: Rodar** `pytest tests/test_sync.py -v` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implementar** seguindo o esboço da spec 01: `_Senha` como `@dataclass(eq=False)` com `dono`; `deque` de senhas; `Condition`; espera em `min(fatia, restante)`; ao desistir, `remove` por identidade e `notify_all`; ao passar, `popleft`, decrementa e `notify_all`. `esperando()` devolve `tuple(s.dono for s in fila)` sob a `Condition`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(sync): semaforo justo`.

### Task 2: `SemaforoJusto` — ordem de chegada, timeout e cancelamento

**Files:**
- Modify: `tests/test_sync.py`, `docs/specs/01-semaforo-justo.md`

**Interfaces:**
- Consumes: `SemaforoJusto` (Task 1).

- [ ] **Step 1: Escrever os testes** (helper `esperar_na_fila(sem, dono)` em `tests/test_sync.py`):
  - `test_fifo`: semáforo ocupado pela thread principal; A, B, C chegam em sequência (cada uma só depois de a anterior aparecer em `esperando()`); `esperando() == (A, B, C)`; ao soltar, a ordem de entrada registrada é `[A, B, C]`.
  - `test_fifo_espera_longa`: o mesmo com o semáforo ocupado por 1 s e `fatia=0.01`; ordem `[A, B, C]`.
  - `test_sem_inanicao` *(substitui "Justiça")*: 4 threads em laço de pegar/soltar por 0,5 s; no meio, a thread X chega; registra a ordem de entrada; nenhuma thread que entrou na fila depois de X (ordem lida de `esperando()` no momento da chegada de X) entra antes dela. Verificação simples: no instante em que X aparece em `esperando()`, guarde os donos à frente dela; X entra antes de qualquer outra entrada que não esteja nesse conjunto.
  - `test_timeout`: ocupado; `acquire(9, timeout=0.05)` devolve `False` entre 0,04 e 0,5 s; `9 not in esperando()`.
  - `test_timeout_zero` *(Review Focus 2)*: livre → `acquire(1, timeout=0) is True`; ocupado → `False` em menos de 0,05 s e fila vazia.
  - `test_cancelar`: ocupado; `cancelar` vira verdadeiro após 0,1 s (via `threading.Event`); `acquire(fatia=0.05)` devolve `False` em menos de 0,1 + 2 × 0,05 s.
  - `test_desistencia_no_meio`: fila A, B, C; B cancela; ao soltar, A e depois C entram; nada fica preso (`join(timeout=1)`).
  - `test_duas_senhas_do_mesmo_dono`: dono 7 com duas senhas na fila; cancelar uma deixa `esperando().count(7) == 1`.
- [ ] **Step 2: Rodar** → os testes que dependem de comportamento novo falham; se algum passar já na primeira execução, confira que ele realmente pode falhar (comente uma linha da implementação e veja o vermelho).
- [ ] **Step 3: Ajustar a implementação** só se algum teste falhar pelo motivo esperado.
- [ ] **Step 4: Rodar 20 vezes** `for i in $(seq 20); do pytest -q tests/test_sync.py || break; done` → 20 verdes.
- [ ] **Step 5: Atualizar a spec 01:** troque o critério "Justiça" por "**Sem inanição:** com 4 threads disputando em laço, uma thread que chega é atendida antes de qualquer uma que chegou depois dela (ordem de chegada, não igualdade de usos)". Marque os critérios e mude o Status para "feita".
- [ ] **Step 6: Commit** `test(sync): ordem de chegada, timeout e cancelamento` e abra o PR 1.

### Task 3: `GrupoDeEstacoes`

**Files:**
- Create: `cozinha/modelo/estacoes.py`
- Test: `tests/modelo/test_estacoes.py`

**Interfaces:**
- Consumes: `SemaforoJusto` (Task 1), `TipoEstacao`, `EstacaoView`, `GrupoView` (spec 00).
- Produces: `@dataclass(frozen=True) Reserva(tipo: TipoEstacao, indice: int)`; `AoMudar = Callable[[tuple[Reserva, ...], TipoEstacao | None], None]`; `GrupoDeEstacoes(tipo, quantidade: int, fatia: float)` com `ocupar(dono: int, cancelar: Callable[[], bool]) -> Reserva | None`, `liberar(reserva: Reserva) -> None`, `views() -> tuple[EstacaoView, ...]`, `view() -> GrupoView`.

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_indices_validos`: grupo de 2 fogões; dois `ocupar` devolvem `Reserva(FOGAO, 0)` e `Reserva(FOGAO, 1)`.
  - `test_menor_indice_livre`: ocupa 0 e 1, libera 0, ocupa de novo → índice 0.
  - `test_liberar_duas_vezes`: segundo `liberar` da mesma reserva levanta `ValueError`.
  - `test_liberar_reserva_invalida` *(Review Focus 3)*: `liberar(Reserva(FOGAO, 5))` e `liberar(Reserva(PIA, 0))` num grupo de FOGÃO levantam `ValueError`; `view()` não muda.
  - `test_exclusao_grupo`: 4 threads × 200 usos num grupo de 2; um `dict` reserva → dono, protegido por `Lock`, nunca recebe uma reserva já presente; nunca mais de 2 ocupadas.
  - `test_cancelado`: grupo de 1 ocupado; `ocupar(2, cancelar=lambda: True)` devolve `None` e `2` não fica em `view().fila_espera`.
  - `test_views`: com C1 dentro e C2 esperando, `views()` mostra `EstacaoView(FOGAO, 0, 1)` e `view() == GrupoView(FOGAO, 1, (2,))`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** `ocupar` chama `semaforo.acquire(dono, cancelar=cancelar, fatia=fatia)`; passou → sob um `Lock` curto marca o menor índice livre. `liberar` valida tipo e índice e que está ocupada, marca livre sob o lock e só depois dá `release`. `view().fila_espera = semaforo.esperando()`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(modelo): grupo de estacoes`.

### Task 4: `Cozinha` — ordem fixa, `ao_mudar` e cancelamento

**Files:**
- Modify: `cozinha/modelo/estacoes.py`, `tests/modelo/test_estacoes.py`, `docs/specs/02-estacoes.md`, `docs/specs/04-cozinheiro.md`

**Interfaces:**
- Consumes: `GrupoDeEstacoes`, `Reserva`, `AoMudar` (Task 3); `Config` (spec 00: `quantidade`, `tick`, `ordem_fixa`).
- Produces: `Cozinha(config: Config)` com `ocupar_todas(dono: int, tipos: tuple[TipoEstacao, ...], cancelar: Callable[[], bool], ao_mudar: AoMudar = lambda s, e: None) -> tuple[Reserva, ...] | None`, `liberar(reservas: Iterable[Reserva]) -> None`, `views() -> tuple[tuple[EstacaoView, ...], tuple[GrupoView, ...]]` (estações e grupos em ordem de `TipoEstacao`).

- [ ] **Step 1: Escrever os testes que falham** (config de teste: `replace(Config(), quantidade={TABUA: 1, PIA: 1, FOGAO: 1, BALCAO: 1})`):
  - `test_ordem_errada`: com `ordem_fixa=True`, `ocupar_todas(1, (BALCAO, FOGAO), ...)` levanta `ValueError`.
  - `test_tipos_vazio` *(Review Focus 4)*: devolve `()` e `ao_mudar` não é chamado.
  - `test_balcao_cheio_bloqueia`: C1 ocupa `(BALCAO,)`; C2 em thread chama `ocupar_todas((BALCAO,))`; depois de 0,1 s ainda não voltou; `liberar` de C1 → C2 volta em menos de 0,5 s.
  - `test_fifo_caminho_real`: fogão ocupado por 1 s; C3, C4, C5 chegam em sequência (esperando aparecer na `fila_espera` do grupo); recebem na ordem C3, C4, C5.
  - `test_ao_mudar`: C2 segura o balcão; C1 chama `ocupar_todas((FOGAO, BALCAO))` com um `ao_mudar` que grava as chamadas; entre as chamadas aparece `((Reserva(FOGAO, 0),), BALCAO)`; depois de C2 soltar, a última é `((Reserva(FOGAO, 0), Reserva(BALCAO, 0)), None)`.
  - `test_cancelado_no_meio`: C2 segura o balcão; C1 pede `(FOGAO, BALCAO)` com `cancelar` que vira verdadeiro após 0,1 s → devolve `None`, a última chamada de `ao_mudar` é `((), None)` e `views()` mostra o fogão livre.
  - `test_liberar_parcial`: C1 pega `(FOGAO, BALCAO)`; `liberar([Reserva(FOGAO, 0)])` deixa o fogão livre e o balcão ocupado.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** os passos 1–5 de `ocupar_todas` da spec 02 e `liberar` na ordem inversa. A inversão do modo demo fica para a Tarefa 5: aqui, com `ordem_fixa=False`, apenas não valide a ordem.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Atualizar as specs** (decisão 2 do grupo): na spec 02, o critério de `ao_mudar` passa a `(Reserva(FOGAO, i),), BALCAO`; na spec 04, em "Estado para a tela", acrescente: "`_ao_mudar` recebe `tuple[Reserva, ...]` e converte em `tuple[(tipo, indice), ...]` para `segurando`".
- [ ] **Step 6: Commit** `feat(modelo): cozinha com aquisicao em ordem fixa`.

### Task 5: Sem deadlock e demonstração de deadlock

**Files:**
- Modify: `cozinha/modelo/estacoes.py`, `tests/modelo/test_estacoes.py`, `docs/specs/02-estacoes.md`

**Interfaces:**
- Consumes: `Cozinha` (Task 4), `Config.demo_deadlock()` (spec 00).

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_demo_inverte_so_pares` *(Review Focus 5)*: com `ordem_fixa=False`, um `ao_mudar` gravando as esperas: o dono 1 espera FOGAO antes de BALCAO; o dono 2 espera BALCAO antes de FOGAO.
  - `test_sem_deadlock`: 6 threads × 500 voltas de `ocupar_todas((FOGAO, BALCAO))` + `liberar`, 1 fogão, balcão de capacidade 1, `cancelar=parar.is_set`; todas terminam; `join(timeout=5)` + `assert not t.is_alive()`.
  - `test_deadlock_demonstravel` (`@pytest.mark.demo`): o mesmo com `Config.demo_deadlock()` (`ordem_fixa=False`) não termina em 5 s (pelo menos uma thread viva); depois `parar.set()` e todas saem em `join(timeout=1)`; `views()` sem nada ocupado.
- [ ] **Step 2: Rodar** `pytest tests/modelo/test_estacoes.py -v` e `pytest -m demo -v` → FAIL.
- [ ] **Step 3: Implementar a inversão:** com `ordem_fixa=False` e `dono % 2 == 0`, iterar `tipos` invertidos; as reservas devolvidas continuam na ordem em que foram pegas.
- [ ] **Step 4: Rodar** `pytest -v` (suíte inteira) e `pytest -m demo -v` → verdes; repetir `test_sem_deadlock` 20 vezes.
- [ ] **Step 5: Marcar os critérios** da spec 02 e mudar o Status para "feita".
- [ ] **Step 6: Commit** `test(modelo): sem deadlock e demonstracao com ordem invertida` e abra o PR 2.
