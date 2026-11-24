# Interface (08) e Controles (09) — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o jogo jogável em Pygame: telas de início, partida e resultado, cozinheiros se movendo até as estações, controles do jogador, modo debug e a demonstração de deadlock, com `python -m cozinha`.

**Architecture:** Tudo em `cozinha/ui/` (só ali e em `cozinha/__main__.py` se importa `pygame`). A `TelaJogo` lê **um** `Retrato` por quadro (`jogo.retrato()`) e desenha a partir dele; `desenho.py` são funções puras (superfície + View); `animacao.py` move uma posição de tela em direção a um alvo derivado do retrato; `entrada.traduzir` é uma função pura de evento → ação. Só a thread principal toca no Pygame (RC06).

**Tech Stack:** Python ≥ 3.11 (o grupo usa 3.12: o pygame 2.6.1 não tem pacote pronto para 3.14), pygame ≥ 2.5, pytest ≥ 8.

**Specs:** [docs/specs/08-interface.md](../../specs/08-interface.md), [docs/specs/09-controles.md](../../specs/09-controles.md). A lógica inteira já está em `develop` (specs 00–07).

## Branches

| PR | Branch | Sai de | Tarefas |
| --- | --- | --- | --- |
| 1 | `feature/interface` | `develop` | 1–4 |
| 2 | `feature/controles` | `feature/interface` (rebase em `develop` após o merge do PR 1) | 5–7 |

Ao fechar cada PR: critérios de aceite marcados na spec (os manuais conferidos rodando o jogo) e **Status** mudado para "feita".

## APIs já existentes que este plano usa (não redefinir)

- `Jogo(config, fonte_tempo=time.monotonic)`: `iniciar()`, `atualizar()` (pode levantar `RuntimeError` se uma thread morreu), `retrato() -> Retrato`, `selecionar(id)` (ignora id inválido), `atribuir(pedido_id)` (sem selecionado não faz nada), `pausar()`, `retomar()`, `encerrar(timeout=2.0) -> list[str]`.
- `Retrato` e as Views (spec 00): `estado`, `tempo_restante`, `pontos`, `meta`, `meta_batida`, `perdidos`, `limite_perdidos`, `entregues`, `tamanho_max_fila`, `pedidos`, `cozinheiros`, `estacoes`, `grupos`, `selecionado`. `CozinheiroView.segurando` é `tuple[(TipoEstacao, indice), ...]`; `GrupoView.fila_espera` são ids em ordem de chegada; `EstacaoView.indice` é a vaga no caso do balcão.
- `Retrato.exemplo()`: 5 cozinheiros (todos os estados), balcão cheio, C4 segurando `(FOGAO, 0)` e esperando BALCÃO, pedido 6 reservado para C5.
- `Config()`, `Config.validar_para_jogo()`, `Config.demo_deadlock()`.
- `tests/test_infra.py` já falha se algo fora de `cozinha/ui` e `__main__.py` importar `pygame`.

## Decisões já tomadas

1. **Controles:** os do documento de divisão da equipe (1–4 seleciona, clique atribui, `P` pausa, `D` debug, `Esc` sai). O aviso "precisam ser validados com o grupo" da spec 09 sai no PR 2.
2. **Erro de thread:** `TelaJogo.atualizar` não engole o `RuntimeError` do `Jogo.atualizar`. Ele sobe até `rodar`, cujo `finally` chama `fechar()` (que encerra as threads) e `pygame.quit()`; o processo termina com o traceback no terminal. É a leitura direta de "bug de thread derruba o jogo de forma visível" (spec 07).
3. **Foco:** perder o foco pausa; ganhar o foco de volta **não** retoma sozinho (o jogador aperta `P`).

## Global Constraints

- Todo módulo começa com `from __future__ import annotations`.
- Cores, tamanhos, posições e o tamanho da janela (`JANELA = (1280, 720)`) em `layout.py`; nenhum número solto em `desenho.py`.
- Funções de `desenho.py` recebem a superfície e uma View; sem estado, sem acesso ao `Jogo`.
- Uma fonte só (a padrão do Pygame), em no máximo 3 tamanhos, criadas uma vez (não a cada quadro).
- Testes de interface rodam sem janela: `tests/ui/conftest.py` faz `os.environ.setdefault("SDL_VIDEODRIVER", "dummy")` antes de importar `pygame`, e uma fixture `tela` chama `pygame.init()`, cria `pygame.display.set_mode(layout.JANELA)` e faz `pygame.quit()` no fim.
- Todo teste que cria um `Jogo` real chama `encerrar()` no fim e confere `[]`.
- Commits em Conventional Commits; PR só entra com `pytest` verde.

## Review Focus

Entradas que as specs implicam e nenhum critério cobre. Cada uma tem teste na tarefa dona.

1. **Mais cozinheiros que cores** (o `Retrato.exemplo()` tem 5): a cor do cozinheiro vem de `layout.cor_cozinheiro(id)`, que cicla a paleta; desenhar não levanta. → Tarefa 1.
2. **Quadro longo** (janela arrastada, `dt` de 2 s): a animação chega no alvo e não passa dele. → Tarefa 2.
3. **Fila cheia:** os `tamanho_max_fila` cartões cabem na faixa de pedidos sem se sobrepor nem sair da janela. → Tarefa 1.
4. **`RuntimeError` do `Jogo.atualizar`:** `TelaJogo.atualizar` deixa subir, e um `fechar()` depois disso devolve sem erro (as threads já foram sinalizadas). → Tarefa 3.
5. **Perder o foco com a partida já pausada:** continua pausada; ganhar o foco não retoma. → Tarefa 3.

---

### Task 1: `layout.py` e `desenho.py`

**Files:**
- Create: `cozinha/ui/layout.py`, `cozinha/ui/desenho.py`
- Test: `tests/ui/__init__.py`, `tests/ui/conftest.py`, `tests/ui/test_desenho.py`

**Interfaces:**
- Produces (`layout.py`): `JANELA`, `FPS_TEXTO`, cores (`FUNDO`, `LIVRE`, `ALERTA`, `TEXTO`, `PACIENCIA_ALTA/MEDIA/BAIXA`), `cor_cozinheiro(id: int) -> tuple[int, int, int]`, `retangulo_estacao(tipo: TipoEstacao, indice: int, capacidade: int) -> pygame.Rect` (o balcão é um retângulo só; a vaga é uma caixinha dentro dele: `retangulo_vaga(indice, capacidade)`), `posicao_espera(tipo, ordem: int) -> tuple[float, float]` (ao lado da estação, empilhando pela ordem na fila), `posicao_descanso(id: int) -> tuple[float, float]`, `cartoes_pedidos(pedidos: Sequence[PedidoView], tamanho_max: int) -> dict[int, pygame.Rect]`, `fontes() -> Fontes` (namedtuple com `pequena`, `media`, `grande`, criada uma vez).
- Produces (`desenho.py`): `desenhar_hud(sup, retrato, fontes)`, `desenhar_estacoes(sup, retrato, fontes)`, `desenhar_pedido(sup, pedido_view, rect, fontes, selecionado_cursor: bool)`, `desenhar_cozinheiro(sup, cozinheiro_view, pos, fontes, selecionado: bool)`, `desenhar_painel(sup, retrato, fontes)`, `desenhar_pausa(sup, fontes)`, `cor_paciencia(fracao: float) -> tuple[int, int, int]` e `desenhar_retrato(sup, retrato, posicoes: Mapping[int, tuple[float, float]], fontes, cursor: int | None = None)`, que chama todas as outras.

- [ ] **Step 1: Escrever os testes que falham:**
  - `test_desenhar_exemplo` (fixture `tela`): `desenhar_retrato(sup, Retrato.exemplo(), posições de descanso, fontes())` não levanta; a superfície não é toda da cor `FUNDO` depois.
  - `test_cor_cozinheiro_cicla` *(Review Focus 1)*: `cor_cozinheiro(1) != cor_cozinheiro(2)`; `cor_cozinheiro(n)` funciona para `n` de 1 a 20.
  - `test_cor_paciencia`: `cor_paciencia(1.0) == PACIENCIA_ALTA`, `cor_paciencia(0.4) == PACIENCIA_MEDIA`, `cor_paciencia(0.1) == PACIENCIA_BAIXA` (limiares 0,5 e 0,25, em `layout.py`).
  - `test_cartoes_cabem` *(Review Focus 3)*: com 6 `PedidoView`, `cartoes_pedidos` devolve 6 retângulos dentro de `pygame.Rect((0, 0), JANELA)` e sem interseção entre eles.
  - `test_estacoes_nao_se_sobrepoem`: os retângulos de todas as estações da `Config()` (balcão contado uma vez) ficam dentro da janela e não se sobrepõem.
  - `test_desempenho`: um retrato com 4 cozinheiros e 6 pedidos (derive do `Retrato.exemplo()` com `dataclasses.replace`); 600 chamadas de `desenhar_retrato` + `pygame.display.flip()` levam menos de 10 s.
- [ ] **Step 2: Rodar** `pytest tests/ui -v` → FAIL.
- [ ] **Step 3: Implementar** seguindo o desenho da spec 08: HUD no topo (tempo `mm:ss`, pontos/meta com barra, "meta batida!", perdidos/limite como bolinhas), faixa de pedidos (cartão com id, receita, barra de paciência na cor de `cor_paciencia`, contorno da cor do cozinheiro quando EM_PREPARO, número do cozinheiro quando `reservado_para`, contador `len/tamanho_max_fila`), estações (cinza livre, cor do dono quando ocupada; balcão com uma caixinha por vaga), cozinheiros (círculo da cor com o número; contorno grosso quando selecionado; ESPERANDO com a estação e `esperando_ha` em `ALERTA`, e as estações que segura) e painel inferior com uma linha por cozinheiro.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(ui): layout e desenho a partir do retrato`.

### Task 2: `animacao.py`

**Files:**
- Create: `cozinha/ui/animacao.py`
- Test: `tests/ui/test_animacao.py`

**Interfaces:**
- Consumes: `layout.retangulo_estacao`, `layout.posicao_espera`, `layout.posicao_descanso`.
- Produces: `alvo(cozinheiro: CozinheiroView, retrato: Retrato) -> tuple[float, float]`; `mover(atual: tuple[float, float], destino: tuple[float, float], velocidade: float, dt: float) -> tuple[float, float]`; `class Animacao` com `atualizar(retrato: Retrato, dt: float) -> None` e `posicoes -> dict[int, tuple[float, float]]` (cozinheiro novo nasce no descanso). `VELOCIDADE` (pixels/s) em `layout.py`.

- [ ] **Step 1: Escrever os testes que falham** (sem janela, só `pygame.Rect`):
  - `test_alvo_livre`: cozinheiro LIVRE → `posicao_descanso(id)`.
  - `test_alvo_trabalhando`: TRABALHANDO segurando `(TABUA, 1)` → centro de `retangulo_estacao(TABUA, 1, …)`; segurando duas (empratar) → a estação de maior tipo (o balcão).
  - `test_alvo_esperando`: C4 do `Retrato.exemplo()` (esperando BALCÃO, primeiro da `fila_espera`) → `posicao_espera(BALCAO, 0)`.
  - `test_mover_velocidade`: de `(0, 0)` para `(100, 0)` com velocidade 50 e `dt=1` → `(50, 0)`.
  - `test_mover_nao_passa` *(Review Focus 2)*: com `dt=2` e velocidade 500 → exatamente `(100, 0)`.
  - `test_animacao_chega`: `Animacao.atualizar` repetido com o mesmo retrato chega aos alvos e para lá.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** `mover` anda `min(distância, velocidade × dt)` em linha reta.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(ui): cozinheiros se movendo ate as estacoes`.

### Task 3: Telas, `rodar` e `__main__`

**Files:**
- Create: `cozinha/ui/telas.py`, `cozinha/ui/app.py`, `cozinha/__main__.py`
- Test: `tests/ui/test_telas.py`, `tests/test_main.py`

**Interfaces:**
- Consumes: `desenho`, `animacao`, `Jogo`.
- Produces: `SAIR`; `TelaInicio(config)`, `TelaJogo(config, jogo: Jogo | None = None)` (cria e inicia o `Jogo` se não receber um), `TelaResultado(config, retrato)`; todas com `evento(e)`, `atualizar(dt)`, `desenhar(sup)`, `fechar()`. `rodar(config) -> None` exatamente como o esboço da spec 08. `__main__.main(argv: list[str] | None = None) -> None` com `argparse` e a flag `--demo-deadlock`.

Para os testes da `TelaJogo` com `Jogo` real, use uma config rápida (`duracao_partida=3`, `tick=0.005`, `tempo_retirada=0`, `intervalo_inicial=0.1`, `intervalo_minimo=0.05`, receitas de teste de etapas de 0,01 s).

- [ ] **Step 1: Escrever os testes que falham** (eventos com `pygame.event.Event(pygame.KEYDOWN, key=...)`):
  - `test_inicio_enter_comeca`: `TelaInicio.evento(Enter)` devolve uma `TelaJogo` cujo jogo está RODANDO; `fechar()` dela encerra as threads.
  - `test_inicio_esc_sai`: `Esc` → `SAIR`.
  - `test_jogo_primeiro_quadro`: `TelaJogo.desenhar` logo depois de criada não levanta (meta e tempo vêm do retrato desde o primeiro quadro).
  - `test_jogo_p_pausa`: `P` → `retrato().estado is PAUSADA`; `P` de novo → RODANDO.
  - `test_foco_pausa` *(Review Focus 5)*: `WINDOWFOCUSLOST` pausa; com a partida já pausada, continua pausada; `WINDOWFOCUSGAINED` não retoma.
  - `test_jogo_termina_no_resultado`: `atualizar(1/60)` em laço (prazo de 6 s) até `proxima()` devolver algo; o que ela devolve é uma `TelaResultado` cujo retrato tem `estado` VITORIA ou DERROTA.
  - `test_resultado`: `Enter` → nova `TelaJogo` (jogo novo); `Esc` → `SAIR`.
  - `test_erro_de_thread_sobe` *(Review Focus 4)*: `TelaJogo` com jogo real, `jogo._cozinheiros[0].erro = ValueError()` → `atualizar(0.016)` levanta `RuntimeError`; depois `fechar()` não levanta e `jogo.encerrar() == []`.
  - `test_main_args` (em `tests/test_main.py`, com `monkeypatch` de `cozinha.ui.app.rodar` gravando a config): `main([])` passa uma `Config()` válida; `main(["--demo-deadlock"])` passa `Config.demo_deadlock()`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** Para a troca para o resultado sem esperar um evento, a `rodar` da spec 08 só troca de tela por `evento`; acrescente ao protocolo `proxima() -> Tela | object | None`, chamada pelo `rodar` depois de `atualizar`, e use-a na `TelaJogo` (VITORIA/DERROTA → `TelaResultado`). Registre a mudança na spec 08 no mesmo PR. `TelaJogo.fechar()` chama `jogo.encerrar()` e loga se a lista não vier vazia. `__main__` chama `validar_para_jogo()` só na config normal.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(ui): telas, loop principal e python -m cozinha`.

### Task 4: README e conferência manual

**Files:**
- Modify: `README.md`, `docs/specs/08-interface.md`

- [ ] **Step 1: Atualizar o README:** "Como rodar" com Python 3.11–3.13 (avisar que o pygame 2.6.1 não tem pacote pronto para 3.14) e `python -m cozinha` / `--demo-deadlock`; nova seção "Como jogar" com o objetivo e a tabela de controles da spec 09; tirar a frase "por enquanto o repositório tem só a documentação".
- [ ] **Step 2: Conferência manual** (rodar o jogo de verdade): abre a tela de início; Enter começa; meta e tempo aparecem no primeiro quadro; cozinheiros andam até as estações e voltam ao descanso; balcão com N vagas; barra de paciência muda de cor e o cartão some; tirar o foco pausa; a partida termina sozinha no resultado; Enter joga de novo; Esc sai; fechar a janela no meio da partida encerra o processo em menos de 2 s (`time python -m cozinha`). Anote no PR o que foi conferido.
- [ ] **Step 3: Marcar os critérios** da spec 08 e mudar o Status para "feita".
- [ ] **Step 4: Commit** `docs: como rodar e como jogar` e abra o PR 1.

### Task 5: `entrada.traduzir`

**Files:**
- Create: `cozinha/ui/entrada.py`
- Test: `tests/ui/test_entrada.py`

**Interfaces:**
- Produces: as dataclasses `Selecionar(cozinheiro_id)`, `Atribuir(pedido_id)`, `AlternarPausa()`, `AlternarDebug()`, `PedirSaida()`, `Confirmar()`; `Acao`; `traduzir(e, retrato, cursor, cartoes) -> tuple[Acao | None, int | None]`.

`Confirmar()` é acrescentada à spec 09 neste PR: o `Enter` sem cursor (e o `Enter` na caixa de confirmação) precisa chegar à `TelaJogo` como uma ação.

- [ ] **Step 1: Escrever os testes que falham** (sem janela; `retrato = Retrato.exemplo()`, `cartoes = layout.cartoes_pedidos(retrato.pedidos, retrato.tamanho_max_fila)`):
  - `test_teclas`: `1`…`4` → `Selecionar(n)`; `P` → `AlternarPausa()`; `D` → `AlternarDebug()`; `Esc` → `PedirSaida()`; uma tecla qualquer → `(None, cursor)`.
  - `test_clique`: clique (`MOUSEBUTTONDOWN`, botão 1) no centro do cartão do pedido 6 → `Atribuir(6)`; clique fora de qualquer cartão → `None`.
  - `test_cursor_setas`: cursor `None` + `→` → primeiro pedido; `→` anda para o próximo id; `←` volta; nas pontas, fica.
  - `test_enter_atribui`: cursor em 5 + `Enter` → `Atribuir(5)`; cursor `None` + `Enter` → `Confirmar()`.
  - `test_cursor_some`: cursor em 9 (não existe no retrato) + `→` → não levanta e o novo cursor é um id que existe (o mais próximo); com o retrato sem pedidos → `None`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** como a spec 09 (cursor é `pedido_id`, nunca índice).
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(ui): traducao de teclas e mouse em acoes`.

### Task 6: Controles na `TelaJogo`, caixa de saída e modo debug

**Files:**
- Modify: `cozinha/ui/telas.py`, `cozinha/ui/desenho.py`, `cozinha/ui/layout.py`, `tests/ui/test_telas.py`

**Interfaces:**
- Consumes: `entrada.traduzir` (Task 5).
- Produces: `desenhar_debug(sup, retrato, fontes, fps: float, threads_vivas: int)` e `desenhar_confirmacao(sup, fontes)` em `desenho.py`; `TelaJogo` com `debug: bool`, `confirmando: bool` e `cursor`.

- [ ] **Step 1: Escrever os testes que falham** (config rápida, jogo real):
  - `test_ordem_do_jogador`: 2 cozinheiros com etapas de 0,3 s; espere C2 ocupado e um pedido AGUARDANDO; `evento(tecla 2)` e depois um clique no cartão desse pedido → C1 livre não o pega; quando C2 fica livre, pega exatamente esse pedido.
  - `test_esc_pergunta_e_cancela`: `Esc` → partida PAUSADA e `confirmando`; `Esc` de novo → RODANDO e sem caixa.
  - `test_esc_com_pausa_manual`: `P`, `Esc`, `Esc` → continua PAUSADA.
  - `test_esc_enter_volta_ao_inicio`: `Esc` + `Enter` → `evento` devolve uma `TelaInicio` e `jogo.encerrar() == []` (as threads já saíram).
  - `test_debug_alterna`: `D` liga, `D` desliga; `desenhar` com o debug ligado não levanta; o estado do jogo não muda.
  - `test_desenhar_debug_exemplo`: `desenhar_debug` com `Retrato.exemplo()` não levanta.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** a caixa de saída como a spec 09 (guarda se já estava pausada antes de abrir) e o modo debug: por estação, quem está dentro e a fila de espera com `esperando_ha`; por cozinheiro, estado, `segurando`, `esperando` e `espera_total`; contadores (fila/máximo, FPS do `Clock`, `threading.active_count()`); legenda TÁBUA → PIA → FOGÃO → BALCÃO. O FPS chega à tela por `TelaJogo.fps`, atualizado pelo `rodar` com `clock.get_fps()`.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(ui): controles do jogador, saida e modo debug`.

### Task 7: Demonstração de deadlock

**Files:**
- Modify: `tests/test_jogo.py` (ou `tests/ui/test_demo.py`), `docs/specs/09-controles.md`

- [ ] **Step 1: Escrever o teste** (`@pytest.mark.demo`): `Jogo(replace(Config.demo_deadlock(), tick=0.005))` iniciado, `atualizar()` em laço; em até 30 s, C1 aparece com `segurando == ((FOGAO, 0),)` e `esperando is BALCAO`, e C2 com `segurando == ((BALCAO, 0),)` e `esperando is FOGAO`; continua assim por mais 2 s; `encerrar(timeout=2) == []`.
- [ ] **Step 2: Rodar** `pytest -m demo -v` → passa (a lógica da trava é da spec 02; este teste prova que ela aparece pelo `Jogo` e pelo `Retrato`). Para provar que ele pode falhar, rode-o uma vez com `ordem_fixa=True` e veja o vermelho.
- [ ] **Step 3: Conferência manual:** `python -m cozinha --demo-deadlock`, `D` ligado: a trava aparece e se mantém por 30 s; fechar a janela encerra em menos de 2 s. Conferir também `P`, `D` e `Esc` numa partida normal.
- [ ] **Step 4: Marcar os critérios** da spec 09, tirar o aviso "os controles precisam ser validados com o grupo", registrar `Confirmar()` na interface e mudar o Status para "feita".
- [ ] **Step 5: Commit** `test: demonstracao de deadlock pelo jogo` e abra o PR 2.
