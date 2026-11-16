# 06 — Relógio, pontuação e partida

**Status:** proposta
**Cobre:** RF01–RF04, RF09, RF14, RF16 (pausa), RC03 (corrida na pontuação)
**Depende de:** 00
**Arquivos:** `cozinha/modelo/relogio.py`, `pontuacao.py`, `partida.py`

## Objetivo

O tempo de jogo (que para na pausa), o placar protegido contra corrida e as regras de vitória e derrota.

## Relogio

```python
class Relogio:
    def __init__(self, fonte: Callable[[], float] = time.monotonic) -> None: ...
    def iniciar(self) -> None: ...
    def agora(self) -> float: ...          # segundos de jogo desde iniciar(), sem contar pausas
    def pausar(self) -> None: ...
    def retomar(self) -> None: ...
    @property
    def pausado(self) -> bool: ...
    def esperar_rodando(self, parar: Event, timeout: float = 0.1) -> None: ...
```

- Guarda o início e o total de tempo pausado, sob um `Lock`. `agora()` = `fonte() - inicio - total_pausado` (congelado durante a pausa).
- `rodando` é um `Event`: setado quando rodando, limpo na pausa. `esperar_rodando` espera esse evento em pedaços de `timeout`, voltando se `parar` for setado.
- `fonte` injetável: os testes passam um relógio falso e avançam o tempo na mão.
- Pausar já pausado ou retomar já rodando não faz nada.

## Pontuacao

```python
class Pontuacao:
    def __init__(self, config: Config) -> None: ...
    def registrar_entrega(self, pedido: Pedido, agora: float) -> int: ...  # devolve os pontos ganhos
    def registrar_perda(self, pedido: Pedido) -> None: ...
    def valores(self) -> tuple[int, int, int]: ...  # (pontos, entregues, perdidos)
```

- Um **semáforo binário** (`Semaphore(1)`) protege pontos, entregues e perdidos (RC03, como o grupo respondeu). Ler-somar-escrever acontece inteiro dentro dele.
- **Pontos da entrega (RF14):** `receita.pontos + round(config.bonus_maximo * pedido.paciencia_restante(agora))`.
- **Idempotente por pedido:** guarda os ids já registrados (entrega ou perda). Registrar o mesmo pedido duas vezes não conta de novo: protege contra o cozinheiro e o `Jogo.atualizar` marcarem o mesmo pedido.
- `registrar_entrega` marca o pedido ENTREGUE; `registrar_perda`, PERDIDO.

## Partida

```python
class Partida:
    def __init__(self, config: Config, relogio: Relogio, pontuacao: Pontuacao) -> None: ...
    def iniciar(self) -> None: ...                # PRONTA → RODANDO
    def pausar(self) -> None: ...                 # RODANDO → PAUSADA
    def retomar(self) -> None: ...                # PAUSADA → RODANDO
    def verificar_fim(self) -> EstadoPartida: ... # chamado 1x por quadro
    def tempo_restante(self) -> float: ...
    @property
    def estado(self) -> EstadoPartida: ...
    @property
    def terminou(self) -> bool: ...               # VITORIA ou DERROTA
```

Máquina de estados:

```
PRONTA ──iniciar──▶ RODANDO ◀──retomar── PAUSADA
                       │  └────pausar────▶
                       ├─ perdidos ≥ limite ─────────────▶ DERROTA
                       └─ tempo acabou ─┬─ pontos ≥ meta ▶ VITORIA
                                        └─ senão ────────▶ DERROTA
```

- **Derrota por clientes perdidos (RF04)** é imediata, assim que `perdidos >= limite_perdidos`.
- **Bater a meta antes do tempo não encerra:** o jogo continua até o fim e a vitória é decidida no fim (RF03 diz "até o fim do tempo"). **(Proposta:** mostrar "meta batida!" na tela quando acontecer.)
- Transição inválida (pausar em PRONTA, iniciar duas vezes) não faz nada.
- `estado` protegido por `Lock`: quem escreve é só a thread da interface (via `Jogo`), mas as outras leem.

## Fora do escopo

- Ranking, recorde salvo, níveis com metas diferentes.

## Critérios de aceite (pytest)

- [ ] `Relogio` com fonte falsa: avança 10 s, pausa, avança 5 s, retoma, avança 2 s → `agora() == 12`.
- [ ] `esperar_rodando` volta logo quando `parar` é setado durante a pausa.
- [ ] **Sem corrida:** 8 threads × 500 `registrar_entrega` de pedidos diferentes → `pontos` é exatamente a soma esperada.
- [ ] Bônus: entregar com paciência cheia dá `pontos + bonus_maximo`; no fim da paciência, só `pontos`.
- [ ] Registrar o mesmo pedido duas vezes conta uma.
- [ ] Partida: tempo acaba com pontos ≥ meta → VITORIA; abaixo → DERROTA; perdidos atinge o limite antes → DERROTA na hora.
- [ ] Pausar e retomar não mudam o tempo restante enquanto pausado.
