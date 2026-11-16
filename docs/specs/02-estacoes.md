# 02 — Estações

**Status:** proposta
**Cobre:** RF12, RF13, RC02, RC04 (deadlock), RC05 (pelo caminho real)
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

AoMudar = Callable[[tuple[Reserva, ...], TipoEstacao | None], None]   # (segurando, esperando)

class GrupoDeEstacoes:
    """Todas as estações de um tipo (ex.: os 2 fogões, ou as vagas do balcão)."""
    def __init__(self, tipo: TipoEstacao, quantidade: int, fatia: float) -> None: ...
    def ocupar(self, dono: int, cancelar: Callable[[], bool]) -> Reserva | None: ...
    def liberar(self, reserva: Reserva) -> None: ...
    def views(self) -> tuple[EstacaoView, ...]: ...
    def view(self) -> GrupoView: ...

class Cozinha:
    """Todos os grupos. É por aqui que o cozinheiro pega e solta estações."""
    def __init__(self, config: Config) -> None: ...
    def ocupar_todas(self, dono: int, tipos: tuple[TipoEstacao, ...],
                     cancelar: Callable[[], bool],
                     ao_mudar: AoMudar = lambda s, e: None) -> tuple[Reserva, ...] | None: ...
    def liberar(self, reservas: Iterable[Reserva]) -> None: ...
    def views(self) -> tuple[tuple[EstacaoView, ...], tuple[GrupoView, ...]]: ...
```

## Comportamento

### `GrupoDeEstacoes`

- Um `SemaforoJusto(quantidade)` controla quantos podem estar dentro.
- `ocupar` chama `semaforo.acquire(dono, cancelar=cancelar, fatia=config.tick)`, que espera **sem sair da fila** (spec 01). Se `cancelar()` ficar verdadeiro, devolve `None`.
- Passou no semáforo → pega um `Lock` curto, escolhe a primeira estação livre (menor índice) e marca `ocupada_por = dono`. Como o semáforo garante vaga, sempre há uma livre.
- `liberar` marca a estação como livre (sob o lock) e só depois dá `release` no semáforo. Liberar uma reserva que não está ocupada levanta `ValueError`.
- O balcão é um grupo como os outros: `quantidade` = capacidade, e cada "estação" é uma vaga.

### `Cozinha.ocupar_todas`: a regra anti-deadlock

1. Os `tipos` chegam ordenados (a `Etapa` já ordena, spec 00). Com `config.ordem_fixa=True`, conferir e levantar `ValueError` se não estiverem.
2. Pegar um tipo por vez, **na ordem crescente de `TipoEstacao`**.
3. Antes de esperar cada tipo, chamar `ao_mudar(segurando_ate_agora, tipo)`. Depois de pegar, `ao_mudar(segurando_ate_agora, None)`. É assim que o cozinheiro sabe, e a tela mostra, que ele **já segura o fogão e espera o balcão** (RF18/RF19).
4. Se algum `ocupar` devolver `None` (cancelado: parar ou cliente foi embora), solta o que já pegou, chama `ao_mudar((), None)` e devolve `None`.
5. Devolve as reservas na ordem em que foram pegas.

`liberar` solta as reservas recebidas **na ordem inversa** da aquisição. Pode ser chamado com só uma parte delas: na entrega, o cozinheiro solta o fogão antes do balcão (spec 04).

**Por que não há deadlock:** deadlock exige um ciclo de espera (A segura X e espera Y, B segura Y e espera X). Se todo mundo pega em ordem crescente, quem segura Y > X nunca espera X, então não há ciclo.

### Modo demonstração (`ordem_fixa=False`)

Para a apresentação (spec 09), com `Config.demo_deadlock()`: os cozinheiros de id par pegam os tipos na ordem **inversa**. Com 1 fogão e balcão de capacidade 1, C1 segura o fogão e espera o balcão, C2 segura o balcão e espera o fogão, e a cozinha trava de verdade. Nessa config `expiracao=False`, então ninguém desiste e a trava se mantém na tela. Nunca é o padrão.

## Fora do escopo

- Escolher uma estação específica (fogão 2): o jogador escolhe o pedido, não a estação.
- Segurar estações entre etapas: o cozinheiro sempre solta tudo ao fim de cada etapa (spec 04).

## Critérios de aceite (pytest)

- [ ] **Exclusão mútua:** 4 threads × 200 usos de um grupo de 2 fogões; nunca a mesma `Reserva` com dois donos, nunca mais de 2 ocupadas.
- [ ] `ocupar` devolve índices válidos e diferentes enquanto há vaga.
- [ ] Liberar duas vezes levanta `ValueError`.
- [ ] **Balcão cheio bloqueia (RF13):** com capacidade 1 ocupada, um segundo `ocupar_todas((BALCAO,))` só retorna depois do `liberar`.
- [ ] **FIFO pelo caminho real:** fogão ocupado por 1 s; C3, C4 e C5 chamam `ocupar_todas((FOGAO,))` em sequência; recebem o fogão na ordem C3, C4, C5.
- [ ] **Sem deadlock:** 6 threads pedindo `(FOGAO, BALCAO)` repetidamente com 1 fogão, balcão de capacidade 1 e tempos zero terminam 500 voltas; `join(timeout=5)` + `assert not is_alive()`.
- [ ] **Deadlock demonstrável** (`@pytest.mark.demo`): o mesmo teste com `ordem_fixa=False` não termina em 5 s; depois, setar o cancelamento faz todas as threads saírem.
- [ ] `ocupar_todas` cancelado no meio devolve `None` e não deixa nada ocupado.
- [ ] `ao_mudar` é chamado com `((FOGAO, i),), BALCAO` quando o cozinheiro segura o fogão e espera o balcão.
- [ ] `views()` reflete quem ocupa e quem espera.
