# 06 — Relógio, pontuação e partida

**Status:** proposta
**Cobre:** RF01–RF04, RF09, RF14, RF16 (pausa), RC03 (corrida na pontuação)
**Depende de:** 00
**Arquivos:** `cozinha/modelo/relogio.py`, `pontuacao.py`, `partida.py`

## Objetivo

O tempo de jogo (que para na pausa e congela no fim), o placar protegido contra corrida e as regras de vitória e derrota.

## Relogio

```python
class Relogio:
    def __init__(self, fonte: Callable[[], float] = time.monotonic) -> None: ...
    def iniciar(self) -> None: ...
    def agora(self) -> float: ...          # segundos de jogo; 0 antes de iniciar
    def pausar(self) -> None: ...
    def retomar(self) -> None: ...
    def congelar(self) -> None: ...        # fim da partida: agora() para de andar para sempre
    @property
    def pausado(self) -> bool: ...
    def esperar_rodando(self, parar: Event, fatia: float) -> None: ...
```

- Guarda o início e o total de tempo pausado, sob um `Lock`. `agora()` = `fonte() - inicio - total_pausado`, parado durante a pausa e depois de `congelar`.
- Antes de `iniciar`, `agora()` devolve 0.
- `rodando` é um `Event`: setado quando rodando, limpo na pausa. `esperar_rodando` espera esse evento em fatias de `fatia` (`config.tick`), voltando assim que `parar` for setado.
- `congelar` também seta `rodando`: ninguém fica preso na pausa depois do fim.
- `fonte` injetável: os testes passam um relógio falso e avançam o tempo na mão.
- Pausar já pausado ou retomar já rodando não faz nada.

## Pontuacao

```python
class Pontuacao:
    def __init__(self, config: Config) -> None: ...
    def registrar_entrega(self, pedido: Pedido, agora: float) -> int: ...  # pontos ganhos
    def registrar_perda(self, pedido: Pedido) -> None: ...
    def fechar(self) -> None: ...
    def valores(self) -> tuple[int, int, int]: ...  # (pontos, entregues, perdidos)
```

- Um **semáforo binário** (`Semaphore(1)`) protege pontos, entregues, perdidos e o conjunto de ids registrados (RC03, como o grupo respondeu). Ler, somar e escrever acontece inteiro dentro dele.
- **Pontos da entrega (RF14):** `receita.pontos + round(config.bonus_maximo * pedido.paciencia_restante(agora))`.
- **É a única que marca estados finais** (spec 00): `registrar_entrega` marca ENTREGUE, `registrar_perda` marca PERDIDO, dentro do semáforo.
- **Registrar o mesmo pedido duas vezes levanta `ValueError`.** Pelas regras de dono (spec 00) isso nunca acontece; se acontecer, é bug e precisa aparecer, não ser escondido.
- **`fechar()`** é chamado pela `Partida` no instante do fim. Depois disso, registros são ignorados (devolvem 0 e não mudam nada). Assim uma entrega que chega milissegundos depois do fim não muda o resultado ("DERROTA — 325/300" não acontece).

## Partida

```python
class Partida:
    def __init__(self, config: Config, relogio: Relogio, pontuacao: Pontuacao) -> None: ...
    def iniciar(self) -> None: ...                # PRONTA → RODANDO
    def pausar(self) -> None: ...                 # RODANDO → PAUSADA
    def retomar(self) -> None: ...                # PAUSADA → RODANDO
    def verificar_fim(self) -> EstadoPartida: ... # chamado 1x por quadro
    def tempo_restante(self) -> float: ...        # nunca negativo
    @property
    def estado(self) -> EstadoPartida: ...
    @property
    def terminou(self) -> bool: ...               # VITORIA ou DERROTA
    @property
    def meta_batida(self) -> bool: ...
```

Máquina de estados:

```
PRONTA ──iniciar──▶ RODANDO ◀──retomar── PAUSADA
                       │  └────pausar────▶
                       ├─ perdidos ≥ limite ─────────────▶ DERROTA
                       └─ tempo acabou ─┬─ pontos ≥ meta ▶ VITORIA
                                        └─ senão ────────▶ DERROTA
```

- **Ao terminar**, na mesma chamada e nesta ordem: `pontuacao.fechar()`, `relogio.congelar()`, e o estado muda. Placar e tempo ficam congelados para a tela de resultado.
- **Derrota por clientes perdidos (RF04)** é imediata, assim que `perdidos >= limite_perdidos`.
- **Bater a meta antes do tempo não encerra.** O jogo segue até o fim e a vitória é decidida aí (RF03: "até o fim do tempo"). `meta_batida` fica verdadeiro para a tela mostrar "meta batida!".
- Transição inválida (pausar em PRONTA, iniciar duas vezes) não faz nada.
- `estado` protegido por `Lock`. Quem escreve é só a thread da interface (via `Jogo`); as outras leem.

## Fora do escopo

- Ranking, recorde salvo, níveis com metas diferentes.

## Critérios de aceite (pytest)

- [ ] `Relogio` com fonte falsa: avança 10 s, pausa, avança 5 s, retoma, avança 2 s → `agora() == 12`.
- [ ] `agora()` antes de `iniciar` é 0; depois de `congelar`, não muda mais.
- [ ] `esperar_rodando` volta em menos de 2 × `fatia` quando `parar` é setado durante a pausa.
- [ ] **Sem corrida:** 8 threads × 500 `registrar_entrega` de pedidos diferentes → `pontos` é exatamente a soma esperada.
- [ ] Bônus: com paciência cheia dá `pontos + bonus_maximo`; no fim da paciência, só `pontos`.
- [ ] Registrar o mesmo pedido duas vezes levanta `ValueError`.
- [ ] Depois de `fechar`, `registrar_entrega` devolve 0 e `valores()` não muda.
- [ ] Partida: tempo acaba com pontos ≥ meta → VITORIA; abaixo → DERROTA; perdidos atinge o limite antes → DERROTA na hora.
- [ ] Depois do fim, `tempo_restante()` fica fixo (≥ 0) e o placar não muda.
- [ ] Pausar e retomar não mudam o tempo restante enquanto pausado.
