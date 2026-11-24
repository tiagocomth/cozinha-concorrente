# Single player — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O jogador controla o cozinheiro 1 (anda, pega pedidos, usa estações), disputando estações com cozinheiros-thread automáticos, numa UI nova com cara de jogo.

**Architecture:** Lógica: `CozinheiroJogador` é uma subclasse de `Cozinheiro` que, em vez de tirar pedidos sozinho, executa comandos de uma `queue.Queue` (`PegarPedido`, `UsarEstacao`, `Desistir`) usando o mesmo `_fazer_etapa`/`ocupar_todas` dos automáticos. O `Jogo` expõe comandos que só enfileiram. UI: um mapa de cozinha vista de cima (`layout`), um `Avatar` com movimento e colisão só de tela, desenhos de estações como objetos e uma `TelaJogo` que lê teclas pressionadas a cada quadro.

**Tech Stack:** Python 3.12, `threading`, `queue`, pygame 2.6, pytest (+ `SDL_VIDEODRIVER=dummy`).

**Spec:** [docs/superpowers/specs/2026-11-24-single-player-design.md](../specs/2026-11-24-single-player-design.md). Leia o design inteiro, incluindo "Decisões de detalhe".

## Branches

| PR | Branch | Sai de | Tarefas |
| --- | --- | --- | --- |
| 1 | `feature/single-player` (já tem o design) | `develop` | 1–3 |
| 2 | `feature/ui-cozinha` | `feature/single-player` | 4–7 |

## Decisão deste plano (desvio do design, registrada)

- **`Config.jogador` tem padrão `False`**, e o modo jogador vem de `Config.single_player()` (`jogador=True`, `meta_pontos=200`), que o `__main__` usa por padrão. Assim `Config()` continua igual e nenhum teste atual muda de significado. O design dizia padrão `True`; o efeito para quem joga é o mesmo.

## Global Constraints

- Só `cozinha/ui` e `cozinha/__main__.py` importam pygame; só a thread principal desenha (RC06).
- Nenhum método do `Jogo` chamado pela tela bloqueia: comandos do jogador vão para uma `queue.Queue` (`put_nowait`).
- A lógica não tem coordenadas: posição, colisão e "perto de" são só da tela.
- Toda espera acorda a cada `config.tick` e olha o `parar` (RC07).
- O jogador usa o mesmo `ocupar_todas` (ordem fixa, semáforo justo) que os automáticos: nunca segura estação entre etapas, nunca fura fila.
- `--demo-deadlock` (com `jogador=False`) e a suíte atual continuam passando.
- Formas desenhadas com `pygame.draw`; cores, tamanhos e posições em `layout.py`.
- `from __future__ import annotations` em todo módulo novo; Conventional Commits; PR só com `pytest` verde.

## Review Focus

1. **`E` na estação certa com ela ocupada:** o jogador entra na fila do semáforo (estado ESPERANDO, aparece em `fila_espera`), o avatar vai para o lugar de espera; `Q` sai da fila e mantém o pedido na mão. → Tarefa 2.
2. **Pegar um pedido que um automático levou entre um quadro e outro:** mensagem "já saiu", sem exceção e sem reserva pendurada que bloqueie o pedido para os outros. → Tarefa 2.
3. **Paciência acaba com o pedido na mão do jogador parado:** vira PERDIDO, conta perdido, o jogador fica livre e recebe mensagem. → Tarefa 2.
4. **Comandos durante a pausa:** ficam na fila e são executados ao retomar (nenhum se perde, nenhum roda pausado). → Tarefa 2.
5. **Teclas seguradas com a partida pausada ou com o avatar ocupado numa estação:** o avatar não anda. → Tarefa 6.

---

### Task 1: `Config.single_player()` e campos novos no `CozinheiroView`

**Files:**
- Modify: `cozinha/config.py`, `cozinha/modelo/retrato.py`, `tests/test_config.py`, `tests/modelo/test_retrato.py`, `docs/specs/00-contratos.md`

**Interfaces:**
- Produces: `Config.jogador: bool = False`; `Config.single_player() -> Config` (`jogador=True`, `meta_pontos=200`); `CozinheiroView` ganha, com padrão (ao final da dataclass): `jogador: bool = False`, `proxima: tuple[TipoEstacao, ...] = ()`, `mensagem: str | None = None`. `Retrato.exemplo()` marca o cozinheiro 1 como `jogador=True`, com `proxima=(TABUA,)` e uma `mensagem`.

- [ ] **Step 1: Testes que falham:** `test_single_player` (`jogador is True`, `meta_pontos == 200`, `validar_para_jogo()` passa, `Config().jogador is False`, `Config.demo_deadlock().jogador is False`); `test_exemplo_tem_jogador` (exatamente um cozinheiro com `jogador=True`, e ele tem `proxima` não vazia).
- [ ] **Step 2: Rodar** `pytest tests/test_config.py tests/modelo/test_retrato.py -v` → FAIL.
- [ ] **Step 3: Implementar.** Atualizar a spec 00 (campos e `single_player`).
- [ ] **Step 4: Rodar a suíte inteira** → verde.
- [ ] **Step 5: Commit** `feat: config single player e campos do jogador no retrato`.

### Task 2: `CozinheiroJogador`

**Files:**
- Create: `cozinha/threads/jogador.py`
- Modify: `cozinha/threads/cozinheiro.py` (só o `_fazer_etapa`)
- Test: `tests/threads/test_jogador.py`

**Interfaces:**
- Consumes: `Cozinheiro`, `FilaDePedidos.reservar/retirar/views`, `Cozinha.ocupar_todas`.
- Produces: comandos `@dataclass(frozen=True)`: `PegarPedido(pedido_id: int | None = None)` (None = o mais antigo da fila não reservado para outro), `UsarEstacao(tipo: TipoEstacao)`, `Desistir()`. `CozinheiroJogador(id, fila, cozinha, pontuacao, relogio, config, parar)` com `comandar(comando) -> None` (não bloqueia) e `view()` preenchendo `jogador=True`, `proxima` (estações da etapa que falta, `()` sem pedido ou ocupado numa etapa) e `mensagem`.
- Mudança em `Cozinheiro._fazer_etapa(pedido, etapa, desistir: Callable[[], bool] = lambda: False) -> bool`: o `cancelar` passa a ser `parar or expirou or desistir()`; se `ocupar_todas` devolver `None` por `desistir()`, **não** registra perda.

Montagem dos testes: igual a `tests/threads/test_cozinheiro.py` (relógio real, `tick=0.005`, `tempo_retirada=0`, receitas de teste de etapas de 0,05 s e paciência 60 s); `esperar(cond)` com prazo.

- [ ] **Step 1: Testes que falham:**
  - `test_parado_sem_comando`: com um pedido na fila, o jogador não o pega sozinho em 0,2 s.
  - `test_pegar_e_fazer_salada`: `PegarPedido()`; `UsarEstacao(TABUA)`; espera a etapa terminar; `UsarEstacao(BALCAO)` → pedido ENTREGUE, pontos > 0, `view().pedido_id is None`.
  - `test_estacao_errada`: com Salada na mão, `UsarEstacao(FOGAO)` → `mensagem` cita "TÁBUA"; nada ocupado.
  - `test_empratar_pega_as_duas`: Sopa; depois de cortar e cozinhar, `UsarEstacao(BALCAO)` (ou `FOGAO`) ocupa FOGÃO e BALCÃO juntos e entrega.
  - `test_proxima`: com Salada na mão, `view().proxima == (TABUA,)`; depois de cortar, `(BALCAO,)`.
  - `test_espera_e_desiste` *(Review Focus 1)*: TÁBUA (quantidade 1) ocupada pelo teste; `UsarEstacao(TABUA)` → `view().estado is ESPERANDO` e o id aparece na `fila_espera` da TÁBUA; `comandar(Desistir())` → sai da fila, pedido continua na mão (`view().pedido_id` igual), nenhuma perda registrada.
  - `test_descartar`: parado com pedido, `Desistir()` → pedido PERDIDO, `perdidos == 1`, jogador livre.
  - `test_pedido_ja_saiu` *(Review Focus 2)*: `PegarPedido(99)` (inexistente) → mensagem "já saiu"; depois um automático (Cozinheiro 2) consegue pegar normalmente os pedidos da fila.
  - `test_expira_na_mao` *(Review Focus 3)*: receita de paciência 0,2 s; pega e fica parado → PERDIDO em até 1 s, `perdidos == 1`, `mensagem` avisa, `view().pedido_id is None`.
  - `test_comando_na_pausa` *(Review Focus 4)*: relógio pausado; `PegarPedido()` → depois de 0,2 s nada pegou; retoma → pegou.
  - `test_parar`: `parar.set()` → `join(timeout=1)` termina, com ou sem pedido na mão, nada ocupado.
  - `test_automatico_nao_pega_o_do_jogador`: pedidos 1 e 2; jogador `PegarPedido(1)`; um automático na mesma cozinha só pega o 2.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.** Loop: `esperar_rodando`; `comando = fila_de_comandos.get(timeout=tick)`; sem comando, checa expiração do pedido na mão (perda + mensagem). `PegarPedido`: escolhe o id (o mais antigo de `fila.views(agora)` com `reservado_para in (None, self.id)` quando `None`); `fila.reservar(id, self.id)`; falhou → mensagem "Pedido #id já saiu"; ok → `retirar(self.id, tick)` em laço até receber o pedido ou ele sumir da fila (expirou), olhando `parar`. `UsarEstacao`: valida que `tipo in etapa.estacoes`; chama `_fazer_etapa(..., desistir=self._desistir.is_set)`; avança o índice da etapa se deu certo; terminou a receita → livre + mensagem de entrega. `comandar(Desistir())`: se o estado atual é ESPERANDO, só seta `_desistir` (é lido pelo `cancelar`); senão enfileira o `Desistir` (descartar). Limpe `_desistir` antes de cada `UsarEstacao`. Mensagens em português, curtas.
- [ ] **Step 4: Rodar** `pytest tests/threads -v` (inclui os do cozinheiro, que não podem quebrar) → verde; repetir `test_jogador.py` 10 vezes.
- [ ] **Step 5: Commit** `feat(threads): cozinheiro do jogador por comandos`.

### Task 3: `Jogo` com jogador

**Files:**
- Modify: `cozinha/jogo.py`, `tests/test_jogo.py`, `docs/specs/07-jogo.md`

**Interfaces:**
- Produces: com `config.jogador`, `_cozinheiros[0]` é `CozinheiroJogador(1, ...)`. `Jogo.pegar_pedido(pedido_id: int | None = None)`, `Jogo.usar_estacao(tipo: TipoEstacao)`, `Jogo.desistir()` — não bloqueiam; sem jogador, não fazem nada. `retrato().cozinheiros[0].jogador is True`.

- [ ] **Step 1: Testes que falham:** `test_jogo_com_jogador` (config rápida com `jogador=True`: threads `cozinheiro-1..n` e `gerador` sobem; `retrato().cozinheiros[0].jogador`); `test_jogador_faz_pedido_pelo_jogo` (`pegar_pedido()`, `usar_estacao(TABUA)`, espera, `usar_estacao(BALCAO)` com Salada → `entregues >= 1` e o pedido entregue era o do jogador); `test_comandos_sem_jogador_ignorados` (`jogador=False`: os três métodos não levantam); `test_encerrar_com_jogador` (com pedido na mão e esperando estação, `encerrar() == []`).
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** e documentar na spec 07.
- [ ] **Step 4: Rodar a suíte inteira** (e `pytest -m demo`) → verde.
- [ ] **Step 5: Commit** `feat: jogo com cozinheiro do jogador` e abrir o **PR 1**.

### Task 4: Mapa da cozinha e `Avatar`

**Files:**
- Modify: `cozinha/ui/layout.py`
- Create: `cozinha/ui/avatar.py`
- Test: `tests/ui/test_avatar.py`, `tests/ui/test_desenho.py` (testes de layout)

**Interfaces:**
- Produces (`layout`): `PISO: pygame.Rect` (área andável da cozinha); `mapa_estacoes(grupos) -> MapaEstacoes` reposicionado na cozinha (estações encostadas na parede de cima, balcão na parede direita), com `MapaEstacoes.areas_interacao: dict[TipoEstacao | str, list[pygame.Rect]]` (retângulo em volta de cada estação; a chave `"quadro"` é o quadro de pedidos) e `MapaEstacoes.obstaculos: list[pygame.Rect]`; `QUADRO: pygame.Rect` (parede esquerda); `INICIO_JOGADOR: Ponto`; `VELOCIDADE_JOGADOR = 260.0`.
- Produces (`avatar`): `class Avatar` com `pos: Ponto`, `andar(direcao: tuple[float, float], dt: float, mapa: MapaEstacoes) -> None` (normaliza a diagonal; preso ao `PISO`; colisão eixo a eixo com `obstaculos`, raio `COZINHEIRO_RAIO`), `perto(mapa) -> TipoEstacao | str | None` (o alvo cuja área de interação contém `pos`; o mais próximo se houver dois).

- [ ] **Step 1: Testes que falham:** `test_anda` (direita por 1 s anda `VELOCIDADE_JOGADOR`, salvo parede); `test_diagonal_normalizada`; `test_nao_sai_do_piso`; `test_nao_atravessa_estacao` (andando contra um obstáculo, o círculo nunca intercepta o retângulo); `test_perto` (no centro da área da TÁBUA → `TABUA`; da área do quadro → `"quadro"`; no meio do piso → `None`); `test_mapa_cabe` (com `Config()` e `Config.demo_deadlock()`: obstáculos dentro do `PISO`, sem sobreposição, áreas de interação alcançáveis — o centro de cada área fica no piso e fora dos obstáculos).
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar** `pytest tests/ui -v` → os testes antigos de layout que dependem de posições antigas são atualizados para o novo mapa (sem afrouxar o que verificam).
- [ ] **Step 5: Commit** `feat(ui): mapa da cozinha e avatar do jogador`.

### Task 5: Desenho novo

**Files:**
- Modify: `cozinha/ui/desenho.py`, `cozinha/ui/layout.py`, `tests/ui/test_desenho.py`

**Interfaces:**
- Produces: `desenhar_retrato(sup, retrato, posicoes, fontes, jogador_pos: Ponto | None = None, perto: TipoEstacao | str | None = None)`; funções por objeto: `desenhar_piso`, `desenhar_tabua`, `desenhar_pia`, `desenhar_fogao(acesso: bool)`, `desenhar_balcao`, `desenhar_quadro`, `desenhar_chef(sup, view, pos, fontes, jogador: bool)`, `desenhar_comanda(sup, pedido_view, receita_etapas, rect, fontes, do_jogador: bool)`, `desenhar_dica(sup, texto, fontes)`. As comandas precisam das etapas: `PedidoView` ganha `etapas: tuple[tuple[TipoEstacao, ...], ...] = ()` e `etapa_atual: int = 0` (preenchidos por `fila.views` e `pedido_view`; documentar na spec 00).

- [ ] **Step 1: Testes que falham:** `test_desenhar_exemplo_novo` (não levanta, com `jogador_pos` e `perto=TABUA`); `test_fogao_aceso` (pixel no centro de uma boca muda de cor com o fogão em uso); `test_chef_jogador_maior` (área pintada do chef do jogador > a de um automático); `test_comanda_mostra_etapas` (uma Sopa desenha 3 ícones de etapa: contar pixels nas três posições); `test_desempenho` mantido (600 quadros < 10 s); `test_pedido_view_etapas` em `tests/modelo/test_fila.py` e `tests/threads/test_cozinheiro.py` (`etapas` da Sopa == `((TABUA,), (FOGAO,), (FOGAO, BALCAO))`).
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** seguindo o desenho do design: piso em ladrilhos, estações como objetos (tábua com faca, pia com água e torneira, fogão com 4 bocas acesas quando em uso, balcão com um prato por vaga, quadro de cortiça), barra de progresso em cima da estação em uso, fila de espera ao lado, chef com chapéu (o do jogador maior, contorno e rótulo "VOCÊ"), comandas de papel com trilha de etapas e a atual destacada, a estação da próxima etapa do jogador com brilho, linha de dica embaixo. Conferir renderizando PNGs (exemplo, partida no meio, demo) e olhando cada um.
- [ ] **Step 4: Rodar** → PASS.
- [ ] **Step 5: Commit** `feat(ui): cozinha desenhada como jogo`.

### Task 6: Controles do jogador na `TelaJogo`

**Files:**
- Modify: `cozinha/ui/entrada.py`, `cozinha/ui/telas.py`, `tests/ui/test_entrada.py`, `tests/ui/test_telas.py`, `docs/specs/09-controles.md`

**Interfaces:**
- Produces (`entrada`): ações `Interagir()`, `Desistir()`, `ClicarComanda(pedido_id)`, `AlternarPausa()`, `AlternarDebug()`, `PedirSaida()`, `Confirmar()`; `traduzir(e, cartoes) -> Acao | None` (`E`/Espaço → Interagir; `Q` → Desistir; clique esquerdo numa comanda → ClicarComanda; `P`, `D`, `Esc`, `Enter`); `direcao(teclas: Sequence[bool]) -> tuple[float, float]` (WASD e setas). Saem `Selecionar`, `Atribuir` e o cursor.
- `TelaJogo(config, jogo=None, teclas: Callable[[], Sequence[bool]] = pygame.key.get_pressed)`: em `atualizar(dt)`, se há jogador, a partida está RODANDO e o cozinheiro do jogador não está ESPERANDO/TRABALHANDO, anda o `Avatar` com `direcao(teclas())`; ocupado, o avatar desliza até `alvo(view)` como os automáticos. `Interagir`: perto do quadro → `jogo.pegar_pedido()`; perto de uma estação → `jogo.usar_estacao(tipo)`; longe de tudo → mensagem "Chegue perto de uma estação". `ClicarComanda` só vale perto do quadro.

- [ ] **Step 1: Testes que falham:** `test_traduzir` (cada tecla/clique → ação; tecla qualquer → `None`); `test_direcao` (`W`+`D` → diagonal; setas iguais a WASD); `test_andar_com_teclas` (teclas falsas segurando `D`: depois de 10 quadros o avatar andou para a direita); `test_nao_anda_pausado` *(Review Focus 5)*; `test_nao_anda_ocupado` *(Review Focus 5)*: com o jogador ESPERANDO, segurar `D` não tira o avatar do lugar de espera; `test_interagir_no_quadro_pega` (avatar posto no quadro + `E` → em até 1 s `cozinheiros[0].pedido_id` não é `None`); `test_interagir_na_estacao` (com pedido, avatar na TÁBUA + `E` → o jogador fica TRABALHANDO ou ESPERANDO na TÁBUA); `test_sem_jogador` (`config` da demo: `E`/`Q` não levantam, `P`/`D`/`Esc` funcionam). Manter os testes de `Esc`/confirmação e foco.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** e atualizar a spec 09 (controles do modo jogador; os de reserva saem).
- [ ] **Step 4: Rodar** `pytest tests/ui -v` → verde.
- [ ] **Step 5: Commit** `feat(ui): jogador anda e interage com a cozinha`.

### Task 7: Início, resultado, `__main__` e conferência

**Files:**
- Modify: `cozinha/ui/telas.py`, `cozinha/ui/desenho.py`, `cozinha/__main__.py`, `README.md`, `docs/specs/08-interface.md`, `tests/ui/test_telas.py`, `tests/test_main.py`

- [ ] **Step 1: Testes que falham:** `test_estrelas` (`estrelas(pontos, meta) -> int`: 0 abaixo de 50 %, 1 de 50 %, 2 de 80 %, 3 com a meta); `test_main_padrao_single_player` (`main([])` passa `Config.single_player()`; `--demo-deadlock` continua `Config.demo_deadlock()`); `test_inicio_e_resultado_desenham`.
- [ ] **Step 2: Rodar** → FAIL.
- [ ] **Step 3: Implementar** a tela de início (título, chef desenhado, teclas como "teclinhas", "Enter para começar") e a de resultado (VITÓRIA/DERROTA, estrelas, pontos, entregues, perdidos, quantos pratos foram seus). README "Como jogar" com os controles novos; spec 08 com o layout novo.
- [ ] **Step 4: Rodar** `pytest` e `pytest -m demo` → verde. Smoke headless do `rodar` real (início → partida com um "bot" que anda até o quadro, pega e faz uma Salada → resultado) e PNGs de cada tela conferidos. **Rodada de teste com o usuário** numa janela real para ajustar `meta_pontos`/paciência de `single_player()`; registrar os valores finais.
- [ ] **Step 5: Commit** `feat(ui): telas de inicio e resultado do single player` e abrir o **PR 2**.
