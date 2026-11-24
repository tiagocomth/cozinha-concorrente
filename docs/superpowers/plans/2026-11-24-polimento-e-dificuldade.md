# Polimento e dificuldade — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Três níveis de dificuldade (Normal mais desafiador) e uma UI mais polida (efeitos, ícones, animações, transições).
**Architecture:** Níveis em `Config.single_player(nivel)`; pesos de receita no `GeradorDePedidos.sortear(decorrido)`. Efeitos em `cozinha/ui/efeitos.py`, alimentados pela diferença entre retratos. Desenho novo em `desenho.py`; contagem na `TelaJogo`; fade no `rodar`.
**Spec:** [design](../specs/2026-11-24-polimento-e-dificuldade-design.md). Branch `feature/polimento` (de `feature/ui-cozinha`), um PR.

## Global Constraints
- `Config()`, `Config.demo_deadlock()` e todos os testes atuais mantêm o sentido.
- Sem arquivos de imagem/som; só `cozinha/ui` e `__main__` importam pygame.
- Efeitos só da tela, deduzidos de retratos.

## Review Focus
1. **Fonte arredondada ausente** no sistema: cai para a fonte padrão sem erro. → Task 3.
2. **Fechar a janela durante a contagem** (threads ainda não iniciadas): `fechar()` devolve sem erro, nada fica vivo. → Task 4.
3. **Várias entregas no mesmo quadro**: um "+N" com a soma, sem exceção. → Task 2.
4. **`P`/`Esc` durante a contagem**: não iniciam nada fora de hora; Esc+Enter volta ao início. → Task 4.
5. **Nível escolhido sobrevive ao "jogar de novo"**. → Task 1.

---

### Task 1: Níveis e pratos progressivos
**Files:** `cozinha/config.py`, `cozinha/threads/gerador.py`, `cozinha/ui/telas.py`, `tests/test_config.py`, `tests/threads/test_gerador.py`, `tests/ui/test_telas.py`, spec 00/05.
**Interfaces:** `NIVEIS: tuple[str, ...] = ("Fácil", "Normal", "Difícil")`; `Config.single_player(nivel: str = "Normal") -> Config` (valores da tabela do design; paciência escalada com `dataclasses.replace` em cada `Receita`; `receitas_progressivas=True`); `Config.receitas_progressivas: bool = False`; `Config.nivel: str | None = None`; `pesos_receitas(receitas, fracao: float) -> list[float]` (peso = `(1 - fracao) / etapas + fracao * etapas`); `GeradorDePedidos.sortear(decorrido: float = 0.0)` usa `rng.choices(receitas, pesos)` só se `receitas_progressivas`. `TelaInicio`: ←/→ trocam o nível (só com `config.jogador`), Enter cria `TelaJogo(Config.single_player(nivel))`; `TelaResultado` "jogar de novo" reusa a mesma config.
- [ ] Testes: `test_niveis` (meta/fator/intervalos/atraso de cada nível; `ValueError` para nível desconhecido; `Config.single_player()` é "Normal"); `test_pesos_progressivos` (fração 0 favorece a receita de menos etapas; fração 1 a de mais etapas; soma > 0); `test_sorteio_progressivo` (com semente, 300 sorteios em `decorrido=0` têm mais Saladas que Pratos do dia; em `decorrido=duracao`, o contrário); `test_sorteio_sem_progressivo_igual` (sem a flag, mesma sequência de antes); `test_inicio_troca_nivel` (→ muda o nível mostrado; Enter cria jogo com a meta do nível); `test_jogar_de_novo_mantem_nivel` *(Review Focus 5)*.
- [ ] Rodar → FAIL; implementar; rodar → PASS; commit `feat: niveis de dificuldade e pratos progressivos`.

### Task 2: Efeitos
**Files:** Create `cozinha/ui/efeitos.py`, `tests/ui/test_efeitos.py`.
**Interfaces:** `@dataclass Efeito(texto: str, pos: Ponto, cor: Cor, idade: float, duracao: float)`; `class Efeitos` com `observar(anterior: Retrato | None, atual: Retrato, mapa: MapaEstacoes) -> None` (entregues subiu → "+Δpontos" no balcão; perdidos subiu → "✗" no lugar das comandas que sumiram estando AGUARDANDO, ou no centro da fila), `atualizar(dt)`, `ativos -> list[Efeito]` com `pos` subindo e alfa caindo pela idade; `pulso_pontos -> float` (0..1, decai em 0,4 s).
- [ ] Testes: `test_entrega_gera_mais` ("+35" perto do balcão); `test_duas_entregas_um_efeito` *(Review Focus 3)* ("+55"); `test_perda_gera_x` (posição dentro da faixa de comandas); `test_efeitos_somem` (após `duracao`, lista vazia); `test_primeiro_retrato_nao_gera`.
- [ ] Rodar → FAIL; implementar; PASS; commit `feat(ui): efeitos de entrega e cliente perdido`.

### Task 3: Polimento visual
**Files:** `cozinha/ui/desenho.py`, `cozinha/ui/layout.py`, `cozinha/ui/telas.py`, `tests/ui/test_desenho.py`.
**Interfaces:** `layout.fontes()` tenta `pygame.font.SysFont(FONTES_PREFERIDAS, tamanho)` e cai para `Font(None, ...)`; `desenhar_icone_etapa(sup, tipo, rect)` (faca, gota, chama, prato); `desenhar_vapor(sup, rect, t)`; `desenhar_chef(..., andando: bool = False, t: float = 0.0)` (balanço vertical de até 3 px); comanda treme (±2 px) com `paciencia <= LIMIAR_PACIENCIA_BAIXA`; HUD com ícones; `desenhar_efeitos(sup, efeitos, fontes)`; `desenhar_retrato(..., efeitos=None, pulso=0.0, andando=frozenset())`. A `TelaJogo` mantém `Efeitos`, calcula quem andou (posição mudou desde o quadro anterior) e passa tudo.
- [ ] Testes: `test_fonte_cai_para_padrao` *(Review Focus 1)* (monkeypatch `SysFont` levantando → `fontes()` funciona); `test_icones_etapa_distintos` (os 4 ícones desenham pixels diferentes entre si); `test_vapor_anima` (dois `t` diferentes → pixels diferentes acima do fogão); `test_chef_balanca` (andando, `t` diferentes → posição do chapéu muda); `test_desenhar_com_efeitos`; desempenho mantido (600 quadros < 10 s). Conferir PNGs.
- [ ] Rodar → FAIL; implementar; PASS; commit `feat(ui): icones, vapor, chefs andando e hud com icones`.

### Task 4: Contagem e transições
**Files:** `cozinha/ui/telas.py`, `cozinha/ui/app.py`, `cozinha/ui/desenho.py`, `tests/ui/test_telas.py`, spec 08.
**Interfaces:** `TelaJogo(config, jogo=None, teclas=..., contagem: float = 0.0)`: com contagem > 0, `jogo.iniciar()` só quando ela zera (durante a contagem desenha "3/2/1/Já!" sobre o retrato de antes de iniciar; teclas de jogo e `P` ignoradas; `Esc` abre a caixa de saída). `TelaInicio` passa `layout.CONTAGEM_SEGUNDOS = 3.0`. `rodar`: ao trocar de tela, fade de `FADE_SEGUNDOS = 0.25` (escurece a última imagem e clareia a nova).
- [ ] Testes: `test_contagem_inicia_depois` (threads não sobem antes de 3 s de `atualizar`; depois, RODANDO); `test_fechar_na_contagem` *(Review Focus 2)*; `test_teclas_na_contagem` *(Review Focus 4)*; `test_inicio_enter_comeca` atualizado.
- [ ] Rodar → FAIL; implementar; PASS; smoke do `rodar` real sem janela; commit `feat(ui): contagem 3-2-1 e fade entre telas`.
- [ ] Revisão final, correções, PR para `develop` (depende de #15), abrir o jogo para o usuário.
