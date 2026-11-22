# Contratos (00) e Partida/Pontuação (06) — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar a base do pacote `cozinha` (tipos, receitas, pedido, config, retrato, infra de testes) e o tempo de jogo, o placar e as regras de vitória/derrota, para destravar as outras quatro pessoas.

**Architecture:** Tudo em `cozinha/` sem Pygame. Valores imutáveis são dataclasses `frozen=True`; estruturas compartilhadas (`Relogio`, `Pontuacao`, `Partida`) protegem o próprio estado com um `Lock`/`Semaphore(1)` e nunca seguram o lock de outra. Tempo sempre vem de `Relogio.agora()`, com fonte injetável para testes.

**Tech Stack:** Python ≥ 3.11 (`threading`, `dataclasses`, `enum`), pytest ≥ 8, pytest-timeout ≥ 2.3.

**Specs:** [docs/specs/00-contratos.md](../../specs/00-contratos.md), [docs/specs/06-partida-e-pontuacao.md](../../specs/06-partida-e-pontuacao.md). Leia as duas antes de começar; o plano não repete o que elas já fixam.

## Entrega em dois PRs (uma spec = uma branch = um PR)

| PR | Branch | Tarefas | Destrava |
| --- | --- | --- | --- |
| 1 | `feature/contratos` (de `develop`) | 1–5 | Pessoas 1, 2, 4 e 5 começam |
| 2 | `feature/partida-e-pontuacao` (de `feature/contratos`, rebase em `develop` após o merge do PR 1) | 6–8 | Specs 04 e 05 (`Relogio`, `Pontuacao`) |

Abra o PR 1 assim que a tarefa 5 passar: é ele que todos esperam. Ao fechar cada PR, marque os critérios de aceite e mude o **Status** da spec para "feita".

## Global Constraints

- `requires-python = ">=3.11"`; todo módulo começa com `from __future__ import annotations`.
- Só `cozinha/ui/` e `cozinha/__main__.py` importam `pygame`.
- Nomes de domínio em português, sem acento no código.
- Lógica nunca usa `time.time()`/`time.monotonic()` direto, exceto como fonte padrão do `Relogio`.
- Toda espera acorda pelo menos a cada `config.tick` (padrão `0.05`) para olhar o `Event` de parada.
- Testes com threads: `daemon=True`, todo `join` com `timeout` seguido de `assert not t.is_alive()`.
- Tolerâncias de tempo com folga explícita ("entre 0,04 e 0,5 s"), nunca "~".
- Commits em Conventional Commits; PR só entra com `pytest` passando.

## Review Focus

Entradas que as specs implicam mas nenhum critério de aceite cobre. Cada uma ganhou um teste na tarefa dona.

1. **`agora < criado_em`** (pedido lido antes da criação, por desalinhamento do retrato): `paciencia_restante` deve ficar em 1, não passar de 1. → Tarefa 3.
2. **`congelar` durante a pausa:** `agora()` fica no valor da pausa, e `retomar` depois não faz o tempo voltar a andar. → Tarefa 6.
3. **`pausar`/`retomar` antes de `iniciar`:** não fazem nada, e `agora()` continua 0. → Tarefa 6.
4. **Pedido registrado como perda e depois como entrega** (ou o contrário): levanta `ValueError`, como o duplicado. → Tarefa 7.
5. **Tempo acaba e o limite de perdidos é atingido no mesmo quadro, com pontos ≥ meta:** DERROTA (perdidos têm prioridade). Além disso, `verificar_fim` só age em RODANDO. → Tarefa 8.

---

### Task 1: Esqueleto do pacote e infra de testes

**Files:**
- Create: `pyproject.toml`, `cozinha/__init__.py`, `cozinha/modelo/__init__.py`, `cozinha/threads/__init__.py`, `cozinha/ui/__init__.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_infra.py`
- Keep: `requirements.txt` (já tem `pygame>=2.5`, `pytest>=8`, `pytest-timeout>=2.3`)

**Interfaces:**
- Produces: o pacote importável `cozinha` e o marcador `demo`.

- [ ] **Step 1: Criar `pyproject.toml`** com `[project] name = "cozinha-concorrente"`, `requires-python = ">=3.11"` e, exatamente como na spec 00:
  ```toml
  [tool.pytest.ini_options]
  markers = ["demo: demonstrações que travam de propósito (fora da suíte padrão)"]
  addopts = "-m 'not demo'"
  timeout = 30
  testpaths = ["tests"]
  ```
- [ ] **Step 2: Criar os `__init__.py` vazios** e um `tests/conftest.py` vazio (ponto de fixtures compartilhadas).
- [ ] **Step 3: Escrever `tests/test_infra.py`:**
  - `test_so_ui_importa_pygame`: percorre `cozinha/**/*.py`, ignora `cozinha/ui/` e `cozinha/__main__.py`, faz `ast.parse` e falha se algum `Import`/`ImportFrom` tem módulo `pygame` ou começando com `pygame.`. A mensagem lista os arquivos culpados.
  - `test_demo_fica_fora`: marcado `@pytest.mark.demo`, faz `pytest.fail("demo não deveria rodar na suíte padrão")`.
- [ ] **Step 4: Rodar** `pytest -v` → 1 passed, 1 deselected. Rodar `pytest -m demo -v` → o teste demo roda e falha (prova que o marcador funciona). Depois troque o corpo do teste demo por `pass`, para `pytest -m demo` passar.
- [ ] **Step 5: Commit** `chore: estrutura do pacote e infra de testes`.

### Task 2: Enums e receitas

**Files:**
- Create: `cozinha/modelo/tipos.py`, `cozinha/modelo/receita.py`
- Test: `tests/modelo/__init__.py`, `tests/modelo/test_receita.py`

**Interfaces:**
- Produces: `TipoEstacao(IntEnum)` com `TABUA=1, PIA=2, FOGAO=3, BALCAO=4`; `EstadoPedido`, `EstadoCozinheiro`, `EstadoPartida` com os membros da spec 00 (via `auto()`); `Etapa(nome: str, estacoes: tuple[TipoEstacao, ...], duracao: float)` com a propriedade `entrega -> bool`; `Receita(nome: str, etapas: tuple[Etapa, ...], pontos: int, paciencia: float)`; `RECEITAS: tuple[Receita, ...]` com Salada, Sopa e Prato do dia (nesta ordem).

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_ordem_das_estacoes`: `[t.value for t in TipoEstacao] == [1, 2, 3, 4]`.
  - `test_etapa_ordena`: `Etapa("empratar", (BALCAO, FOGAO), 1).estacoes == (FOGAO, BALCAO)`.
  - `test_etapa_repetida`: `Etapa("x", (FOGAO, FOGAO), 1)` levanta `ValueError`.
  - `test_etapa_entrega`: `entrega` é `True` com BALCAO, `False` sem.
  - `test_balcao_fora_da_ultima`: `Receita("r", (Etapa("e", (BALCAO,), 0), Etapa("c", (TABUA,), 1)), 10, 10)` levanta `ValueError`.
  - `test_receitas_iniciais`: para cada receita de `RECEITAS`, só `etapas[-1].entrega`; nomes, pontos e paciências batem com a tabela da spec 00 (Salada 20/25, Sopa 35/35, Prato do dia 50/45); a Sopa termina em `("empratar", (FOGAO, BALCAO), 1)`.
- [ ] **Step 2: Rodar** `pytest tests/modelo/test_receita.py -v` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implementar `tipos.py` e `receita.py`.** `Etapa.__post_init__` ordena por valor com `object.__setattr__(self, "estacoes", tuple(sorted(...)))` e rejeita repetidas. Etapas de `RECEITAS` exatamente como na tabela da spec 00 (entregar da Salada com duração 0).
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(modelo): tipos e receitas`.

### Task 3: Pedido

**Files:**
- Create: `cozinha/modelo/pedido.py`
- Test: `tests/modelo/test_pedido.py`

**Interfaces:**
- Consumes: `Receita`, `EstadoPedido` (Task 2).
- Produces: `@dataclass(eq=False) Pedido(id: int, receita: Receita, criado_em: float, estado: EstadoPedido = AGUARDANDO, cozinheiro_id: int | None = None)`; `prazo() -> float`; `paciencia_restante(agora: float) -> float` (fração em [0, 1]); `expirou(agora: float) -> bool`.

- [ ] **Step 1: Escrever os testes que falham** (receita de paciência 10, `criado_em=100`):
  - `test_paciencia_vai_de_1_a_0`: `paciencia_restante(100) == 1.0`, `(105) == 0.5`, `(110) == 0.0`, `(200) == 0.0`.
  - `test_paciencia_antes_da_criacao` *(Review Focus 1)*: `paciencia_restante(90) == 1.0`.
  - `test_expirou`: `expirou(109.99) is False`, `expirou(110) is True`.
  - `test_identidade`: dois pedidos com os mesmos campos são diferentes (`!=`) e cabem juntos num `set`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** `paciencia_restante` = `(prazo() - agora) / receita.paciencia` limitada a `[0.0, 1.0]`; `expirou` = `agora >= prazo()`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(modelo): pedido`.

### Task 4: Config

**Files:**
- Create: `cozinha/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `TipoEstacao`, `RECEITAS` (Task 2).
- Produces: `@dataclass(frozen=True) Config` com todos os campos e padrões da spec 00 (`duracao_partida=180.0`, `meta_pontos=300`, `limite_perdidos=5`, `n_cozinheiros=3`, `quantidade={TABUA: 2, PIA: 1, FOGAO: 2, BALCAO: 2}` como `MappingProxyType`, `tempo_retirada=1.0`, `tamanho_max_fila=6`, `intervalo_inicial=8.0`, `intervalo_minimo=3.0`, `bonus_maximo=15`, `receitas=RECEITAS`, `expiracao=True`, `ordem_fixa=True`, `tick=0.05`, `fps=60`, `semente=None`); `validar_para_jogo() -> None`; `Config.demo_deadlock() -> Config`.

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_padrao_e_replace`: `Config()` e `dataclasses.replace(Config(), n_cozinheiros=1)` funcionam; o segundo tem `n_cozinheiros == 1`.
  - `test_quantidade_imutavel`: `Config().quantidade[TipoEstacao.TABUA] = 3` levanta `TypeError`.
  - `test_validacao_basica`: `Config(tick=0)`, `Config(n_cozinheiros=0)` e `Config(quantidade={TABUA: 0, PIA: 1, FOGAO: 1, BALCAO: 1})` levantam `ValueError`.
  - `test_validar_para_jogo`: `Config(duracao_partida=60).validar_para_jogo()` e `Config(n_cozinheiros=5).validar_para_jogo()` levantam `ValueError`; `Config().validar_para_jogo()` passa; `Config(duracao_partida=3, n_cozinheiros=1)` constrói sem erro (testes usam isso).
  - `test_demo_deadlock`: `ordem_fixa is False`, `expiracao is False`, `quantidade[FOGAO] == 1`, `quantidade[BALCAO] == 1`, `n_cozinheiros == 2`, `[r.nome for r in receitas] == ["Sopa"]`, `limite_perdidos >= 1000`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** `quantidade` via `field(default_factory=lambda: MappingProxyType({...}))`; `__post_init__` converte dict comum recebido em `MappingProxyType` (com `object.__setattr__`) e valida: `duracao_partida`, `intervalo_inicial`, `intervalo_minimo` e `tick` > 0; `tempo_retirada` ≥ 0 (os testes da spec 04 usam 0), quantidades ≥ 1 para os quatro tipos, `n_cozinheiros` ≥ 1, `intervalo_minimo <= intervalo_inicial`. `validar_para_jogo` exige `180 <= duracao_partida <= 300` e `3 <= n_cozinheiros <= 4`. `demo_deadlock` usa `limite_perdidos=1000`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat: config do jogo`.

### Task 5: Retrato e `Retrato.exemplo()`

**Files:**
- Create: `cozinha/modelo/retrato.py`
- Test: `tests/modelo/test_retrato.py`

**Interfaces:**
- Consumes: enums (Task 2).
- Produces: `PedidoView`, `CozinheiroView`, `EstacaoView`, `GrupoView`, `Retrato`, todas `frozen=True`, com exatamente os campos e tipos da spec 00; `Retrato.exemplo() -> Retrato`. **A pessoa 4 desenha em cima do `exemplo()`:** ele precisa ser coerente e cobrir os casos visuais.

- [ ] **Step 1: Escrever os testes que falham** sobre `r = Retrato.exemplo()`:
  - `test_exemplo_estados`: `{c.estado for c in r.cozinheiros} == set(EstadoCozinheiro)`.
  - `test_exemplo_coerente`: ids de `r.pedidos` sem repetição e ordenados; todo `pedido_id` de cozinheiro existe em `r.pedidos`; toda `EstacaoView.ocupada_por` não nula é id de cozinheiro que tem `(tipo, indice)` em `segurando`; todo id em `GrupoView.fila_espera` é de cozinheiro ESPERANDO com `esperando == grupo.tipo`; há um `EstacaoView` por vaga de cada `GrupoView.capacidade`.
  - `test_exemplo_casos_visuais`: existe um cozinheiro segurando `(FOGAO, 0)` e esperando `BALCAO` (caso da demo de deadlock); existe um pedido com `reservado_para` não nulo; `0 <= paciencia <= 1` e `0 <= progresso <= 1` em todos.
  - `test_imutavel`: atribuir `r.pontos = 1` levanta `dataclasses.FrozenInstanceError`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** Use as capacidades de `Config()` (2 tábuas, 1 pia, 2 fogões, balcão com 2 vagas). Para alguém esperar o BALCÃO de forma coerente, as duas vagas precisam estar ocupadas, então o exemplo tem 5 cozinheiros (mais que o jogo real; é só um retrato fixo): C1 TRABALHANDO em `(TABUA, 0)`; C2 TRABALHANDO em `(FOGAO, 1)` e `(BALCAO, 0)` empratando; C3 TRABALHANDO em `(BALCAO, 1)` na retirada; C4 ESPERANDO BALCÃO segurando `(FOGAO, 0)`, `esperando_ha=3.2`, aparecendo em `GrupoView(BALCAO).fila_espera`; C5 LIVRE. Pedidos: um por cozinheiro ocupado (EM_PREPARO) mais dois AGUARDANDO, um deles com `reservado_para=5`. `estado=RODANDO`, `tempo_restante=95.0`, `pontos=140`, `meta=300`, `entregues=5`, `perdidos=1`, `selecionado=1`, demais valores da `Config()`.
- [ ] **Step 4: Rodar** → PASS. Rodar a suíte inteira `pytest -v` → tudo verde.
- [ ] **Step 5: Commit** `feat(modelo): retrato e exemplo para a interface`.
- [ ] **Step 6: Abrir o PR 1** `feature/contratos` → `develop`, com os critérios de aceite da spec 00 marcados e o Status da spec mudado para "feita". Avise o grupo.

### Task 6: Relogio

**Files:**
- Create: `cozinha/modelo/relogio.py`
- Test: `tests/modelo/test_relogio.py`, fixture `fonte_falsa` em `tests/conftest.py`

**Interfaces:**
- Produces: `Relogio(fonte: Callable[[], float] = time.monotonic)` com `iniciar()`, `agora() -> float`, `pausar()`, `retomar()`, `congelar()`, propriedade `pausado -> bool`, `esperar_rodando(parar: threading.Event, fatia: float) -> None`. Fixture `fonte_falsa` com `.avancar(s: float)` e chamável que devolve o tempo atual — reutilizada pelos testes das specs 04, 05 e 07.

- [ ] **Step 1: Escrever a fixture e os testes que falham:**
  - `test_pausa_desconta`: avança 10, pausa, avança 5, retoma, avança 2 → `agora() == 12`.
  - `test_antes_de_iniciar`: `agora() == 0` antes de `iniciar`, mesmo com a fonte avançando.
  - `test_congelar`: depois de `congelar`, avançar a fonte não muda `agora()`.
  - `test_congelar_na_pausa` *(Review Focus 2)*: avança 4, pausa, avança 3, congela, retoma, avança 10 → `agora() == 4`; `pausado is False`.
  - `test_pausa_antes_de_iniciar` *(Review Focus 3)*: `pausar()` e `retomar()` antes de `iniciar` não levantam; `agora() == 0`; `iniciar` depois funciona normalmente.
  - `test_pausar_duas_vezes`: pausar duas vezes e retomar uma vez desconta só o tempo pausado de fato.
  - `test_esperar_rodando_sai_com_parar`: relógio real, pausado; thread daemon chama `esperar_rodando(parar, 0.05)`; após 0,1 s faz `parar.set()`; `join(timeout=1)` e a thread terminou em menos de 2 × 0,05 s depois do `set` (medir com `time.monotonic`, aceitar até 0,1 s).
  - `test_esperar_rodando_volta_ao_retomar`: mesma montagem, `retomar()` em vez de `parar.set()` → a thread termina.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** Estado sob um `Lock`: `_inicio`, `_total_pausado`, `_pausado_em` (ou `None`), `_congelado_em` (ou `None`). `rodando` é um `threading.Event` setado em `iniciar`/`retomar`/`congelar`, limpo em `pausar`. Depois de `congelar`, `pausar`/`retomar` não fazem nada e `agora()` devolve o valor fixado. `esperar_rodando`: `while not parar.is_set() and not rodando.wait(fatia): pass`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(modelo): relogio pausavel`.

### Task 7: Pontuacao

**Files:**
- Create: `cozinha/modelo/pontuacao.py`
- Test: `tests/modelo/test_pontuacao.py`

**Interfaces:**
- Consumes: `Config` (Task 4), `Pedido` (Task 3).
- Produces: `Pontuacao(config: Config)` com `registrar_entrega(pedido: Pedido, agora: float) -> int`, `registrar_perda(pedido: Pedido) -> None`, `fechar() -> None`, `valores() -> tuple[int, int, int]` (pontos, entregues, perdidos).

- [ ] **Step 1: Escrever os testes que falham** (receita de 20 pontos e paciência 10, `bonus_maximo=15`):
  - `test_bonus`: entrega com `agora == criado_em` devolve 35; outro pedido entregue no prazo exato devolve 20; `valores() == (55, 2, 0)`; os pedidos ficam ENTREGUE.
  - `test_perda`: `registrar_perda` marca PERDIDO e `valores() == (0, 0, 1)`.
  - `test_duplicado`: registrar a mesma entrega duas vezes levanta `ValueError`; `valores()` conta só uma.
  - `test_perda_depois_de_entrega` *(Review Focus 4)*: entrega e depois perda do mesmo pedido levanta `ValueError`, e o contrário também; o estado do pedido não muda na segunda chamada.
  - `test_fechar`: depois de `fechar()`, `registrar_entrega` devolve 0, `registrar_perda` não faz nada, `valores()` igual ao de antes e o pedido continua no estado anterior.
  - `test_sem_corrida`: 8 threads daemon × 500 pedidos distintos, todas começando juntas num `threading.Barrier(8)`, entregues com `agora == criado_em` → `valores() == (8 * 500 * 35, 4000, 0)`; todos os `join(timeout=10)` terminam.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** com `threading.Semaphore(1)` (spec 06, RC03) protegendo pontos, entregues, perdidos, o `set` de ids registrados, a flag de fechada e a escrita de `pedido.estado`. Pontos = `receita.pontos + round(config.bonus_maximo * pedido.paciencia_restante(agora))`. A checagem de fechada vem antes da de duplicado: registro após o fim é ignorado em silêncio, inclusive duplicado.
- [ ] **Step 4: Rodar** `for i in $(seq 20); do pytest -q tests/modelo/test_pontuacao.py || break; done` → 20 execuções verdes.
- [ ] **Step 5: Commit** `feat(modelo): pontuacao protegida por semaforo`.

### Task 8: Partida

**Files:**
- Create: `cozinha/modelo/partida.py`
- Test: `tests/modelo/test_partida.py`

**Interfaces:**
- Consumes: `Config`, `Relogio` (Task 6), `Pontuacao` (Task 7), `EstadoPartida`.
- Produces: `Partida(config, relogio, pontuacao)` com `iniciar()`, `pausar()`, `retomar()`, `verificar_fim() -> EstadoPartida`, `tempo_restante() -> float`, propriedades `estado`, `terminou`, `meta_batida`. `Partida.pausar/retomar` chamam `relogio.pausar/retomar` (o `Jogo` da spec 07 só fala com a `Partida`).

- [ ] **Step 1: Escrever os testes que falham** (fonte falsa, `duracao_partida=10`, `meta_pontos=50`, `limite_perdidos=2`):
  - `test_transicoes_invalidas`: `pausar` em PRONTA não muda nada; `iniciar` duas vezes mantém RODANDO sem reiniciar o relógio; `retomar` em RODANDO não faz nada.
  - `test_vitoria`: soma 50 pontos, avança 10 → `verificar_fim() == VITORIA`.
  - `test_derrota_por_pontos`: 49 pontos, avança 10 → DERROTA.
  - `test_derrota_por_perdidos`: avança 3, registra 2 perdas → DERROTA na hora, `tempo_restante() == 7`.
  - `test_perdidos_tem_prioridade` *(Review Focus 5)*: 60 pontos e 2 perdas, avança 10 → DERROTA.
  - `test_meta_batida_nao_encerra`: 60 pontos, avança 5 → RODANDO e `meta_batida is True`.
  - `test_congela_no_fim`: depois de VITORIA, avançar a fonte e registrar entrega não mudam `tempo_restante()` (≥ 0) nem `valores()`.
  - `test_pausa_preserva_tempo`: avança 2, pausa, avança 100 → `tempo_restante() == 8` e `verificar_fim() == PAUSADA`; retoma, avança 1 → 7.
  - `test_tempo_restante_nunca_negativo`: avança 50 sem chamar `verificar_fim` → `tempo_restante() == 0`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** `estado` sob `Lock`. `verificar_fim` só age em RODANDO; checa perdidos primeiro, depois o tempo. Ao terminar, nesta ordem: `pontuacao.fechar()`, `relogio.congelar()`, muda o estado. `tempo_restante = max(0.0, duracao_partida - relogio.agora())`. `meta_batida` lê `pontuacao.valores()[0] >= meta_pontos`.
- [ ] **Step 4: Rodar** `pytest -v` (suíte inteira) → tudo verde.
- [ ] **Step 5: Commit** `feat(modelo): partida com vitoria e derrota`.
- [ ] **Step 6: Abrir o PR 2** `feature/partida-e-pontuacao` → `develop` (rebase em `develop` se o PR 1 já entrou), com os critérios da spec 06 marcados e o Status mudado para "feita". Avise as pessoas 2 e 5.
