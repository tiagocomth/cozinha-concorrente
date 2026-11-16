# 02 — Estações

**Status:** proposta
**Cobre:** RF12, RF13, RC02, RC04 (deadlock)
**Depende de:** 00, 01
**Arquivo:** `cozinha/modelo/estacoes.py`

## Objetivo

Controlar o uso dos equipamentos: nunca dois cozinheiros na mesma estação, espera justa quando todas do tipo estão ocupadas, e aquisição de várias estações **sempre na ordem fixa**, que é o que impede o deadlock.

## Interface

```python
@dataclass(frozen=True)
class Reserva:
    tipo: TipoEstacao
    indice: int

class GrupoDeEstacoes:
    """Todas as estações de um tipo (ex.: os 2 fogões)."""
    def __init__(self, tipo: TipoEstacao, quantidade: int) -> None: ...
    def ocupar(self, dono: int, timeout: float) -> Reserva | None: ...
    def liberar(self, reserva: Reserva) -> None: ...
    def views(self) -> tuple[EstacaoView, ...]: ...
    def view(self) -> GrupoView: ...

class Cozinha:
    """Todos os grupos. É por aqui que o cozinheiro pega e solta estações."""
    def __init__(self, config: Config) -> None: ...
    def ocupar_todas(self, dono: int, tipos: tuple[TipoEstacao, ...],
                     timeout: float, parar: Event,
                     desistir: Callable[[], bool] = lambda: False) -> tuple[Reserva, ...] | None: ...
    def liberar_todas(self, reservas: tuple[Reserva, ...]) -> None: ...
    def views(self) -> tuple[tuple[EstacaoView, ...], tuple[GrupoView, ...]]: ...
```

## Comportamento

### `GrupoDeEstacoes`

- Um `SemaforoJusto(quantidade)` controla quantos podem estar dentro.
- Passou no semáforo → pega um `Lock` curto e escolhe a primeira estação livre (menor índice), marcando `ocupada_por = dono`. Como o semáforo garante vaga, sempre há uma livre.
- `liberar` marca a estação como livre (sob o lock) e depois dá `release` no semáforo. Liberar uma reserva que não está ocupada levanta `ValueError`.
- O balcão é um grupo como os outros: `quantidade` = capacidade.

### `Cozinha.ocupar_todas` — a regra anti-deadlock

1. Os `tipos` chegam ordenados (a `Etapa` já ordena, spec 00). Com `config.ordem_fixa=True`, conferir e levantar `ValueError` se não estiverem.
2. Pegar um tipo por vez, **na ordem crescente de `TipoEstacao`**.
3. Cada `ocupar` usa `timeout` curto (`config.timeout_aquisicao`) e repete enquanto `parar` não estiver setado. Isso não é desistir: a senha volta para a fila, então o cozinheiro pode perder a posição. **(Decisão do grupo:** aceitar isso ou usar um `acquire` com timeout longo e checar `parar` via `notify_all` no encerramento.)
4. Se `parar` for setado ou `desistir()` ficar verdadeiro (o cliente foi embora, spec 04) entre uma tentativa e outra, solta o que já pegou e devolve `None`.
5. Devolve as reservas na ordem em que foram pegas.

`liberar_todas` solta **na ordem inversa**.

**Por que não há deadlock:** deadlock exige um ciclo de espera (A segura X e espera Y, B segura Y e espera X). Se todo mundo pega em ordem crescente, quem segura Y > X nunca espera X, então não há ciclo.

### Modo demonstração (`ordem_fixa=False`)

Para a apresentação (spec 09): pega os tipos na ordem **inversa** para metade dos cozinheiros (id par). A configuração de demonstração usa **1 fogão e balcão de capacidade 1**: um cozinheiro segura o fogão e espera o balcão, o outro segura o balcão e espera o fogão, e o jogo trava de verdade na tela. Com 2 fogões quase nunca trava, porque sempre sobra um. Nunca é o padrão.

## Fora do escopo

- Escolher uma estação específica (fogão 2): o jogador escolhe o pedido, não a estação.
- Segurar estações entre etapas: o cozinheiro sempre solta tudo ao fim de cada etapa (spec 04).

## Critérios de aceite (pytest)

- [ ] **Exclusão mútua:** 4 threads × 200 usos de um grupo de 2 fogões; nunca a mesma `Reserva` com dois donos, nunca mais de 2 ocupadas.
- [ ] `ocupar` devolve índices válidos e diferentes enquanto há vaga.
- [ ] Liberar duas vezes levanta `ValueError`.
- [ ] **Sem deadlock:** 6 threads pedindo `(FOGAO, BALCAO)` repetidamente com balcão de capacidade 1 e tempos zero terminam 500 voltas em menos de 5 s.
- [ ] **Deadlock demonstrável:** o mesmo teste com `ordem_fixa=False`, 1 fogão e balcão de capacidade 1 não termina no prazo (marcado `@pytest.mark.demo`, fora da suíte padrão). Encerrar setando `parar`.
- [ ] `ocupar_todas` com `parar` setado ou `desistir()` verdadeiro no meio devolve `None` e não deixa nada ocupado.
- [ ] `views()` reflete quem ocupa e quem espera.
