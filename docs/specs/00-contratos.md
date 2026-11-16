# 00 — Contratos

**Status:** proposta, validar com o grupo antes de qualquer código
**Cobre:** RNF01, RNF03, RNF04 (infra de testes), RC06
**Depende de:** nada. Todas as outras specs dependem desta.

## Objetivo

Fixar os tipos e as fronteiras que ligam as partes do jogo, para a lógica (threads) e a interface (Pygame) serem feitas em paralelo. Se algo daqui mudar, avisar o grupo: muda o trabalho de todo mundo.

## Estrutura do pacote

```
cozinha/
├── __main__.py          # python -m cozinha [--demo-deadlock] → ui.app.rodar(config)
├── config.py            # Config (spec 00)
├── sync.py              # SemaforoJusto (spec 01)
├── modelo/
│   ├── tipos.py         # TipoEstacao, EstadoPedido, EstadoCozinheiro, EstadoPartida (spec 00)
│   ├── receita.py       # Etapa, Receita, RECEITAS (spec 00)
│   ├── pedido.py        # Pedido (spec 00)
│   ├── retrato.py       # Retrato e as Views (spec 00)
│   ├── estacoes.py      # GrupoDeEstacoes, Cozinha (spec 02)
│   ├── fila.py          # FilaDePedidos (spec 03)
│   ├── relogio.py       # Relogio (spec 06)
│   ├── pontuacao.py     # Pontuacao (spec 06)
│   └── partida.py       # Partida (spec 06)
├── threads/
│   ├── cozinheiro.py    # Cozinheiro (spec 04)
│   └── gerador.py       # GeradorDePedidos (spec 05)
├── jogo.py              # Jogo, a fachada que a interface usa (spec 07)
└── ui/                  # Pygame (specs 08 e 09)
tests/                   # pytest, espelhando cozinha/
pyproject.toml           # requires-python, pytest (spec 00)
```

**Regra de importação:** só `cozinha/ui/` e `__main__.py` importam `pygame`. Tudo o resto roda e é testado sem janela.

## Convenções

- Nomes de domínio em português, sem acento no código (`Cozinheiro`, `fila`, `paciencia`).
- Tipagem em tudo (`from __future__ import annotations`). Dataclasses `frozen=True` para o que é valor.
- Tempo sempre em **segundos de jogo** (`float`), lido de `Relogio.agora()` (spec 06). Nunca `time.time()` direto na lógica: a pausa tem que congelar tudo.
- **Nenhuma espera sem fim.** Toda espera que pode demorar (estação, fila, pausa) acorda pelo menos a cada `config.tick` para olhar o `Event` de parada (RC07). A exceção são as seções críticas curtas (`with mutex:` em volta de poucas linhas, sem esperar nada lá dentro).
- **Nunca segurar um lock e esperar outro**, exceto na aquisição de estações, que segue a ordem fixa (spec 02).
- Toda estrutura compartilhada protege o próprio estado. Quem usa não segura o lock de outro.

## Enums (`modelo/tipos.py`)

```python
class TipoEstacao(IntEnum):
    # O valor É a ordem global de aquisição (RC04). Não reordenar.
    TABUA = 1
    PIA = 2
    FOGAO = 3
    BALCAO = 4

class EstadoPedido(Enum):
    AGUARDANDO = auto()   # na fila
    EM_PREPARO = auto()   # com um cozinheiro
    ENTREGUE = auto()
    PERDIDO = auto()      # a paciência acabou

class EstadoCozinheiro(Enum):
    LIVRE = auto()        # sem pedido
    ESPERANDO = auto()    # parado na fila de uma estação
    TRABALHANDO = auto()  # usando uma estação

class EstadoPartida(Enum):
    PRONTA = auto()
    RODANDO = auto()
    PAUSADA = auto()
    VITORIA = auto()
    DERROTA = auto()
```

## Receitas (`modelo/receita.py`)

```python
@dataclass(frozen=True)
class Etapa:
    nome: str                          # "cortar", "cozinhar", "empratar"...
    estacoes: tuple[TipoEstacao, ...]  # quase sempre 1; empratar usa 2
    duracao: float                     # segundos de jogo

    @property
    def entrega(self) -> bool: ...     # True se usa BALCAO

@dataclass(frozen=True)
class Receita:
    nome: str
    etapas: tuple[Etapa, ...]
    pontos: int        # base por entrega a tempo
    paciencia: float   # segundos que o cliente espera
```

- `Etapa.__post_init__` ordena `estacoes` por valor (com `object.__setattr__`, porque é frozen) e rejeita repetidas. Quem adquire nunca precisa ordenar.
- `Receita.__post_init__` exige que só a **última** etapa use BALCAO: é a entrega.

Receitas iniciais **(proposta, balancear no M5)**:

| Receita | Etapas (estação, segundos) | Pontos | Paciência |
| --- | --- | --- | --- |
| Salada | cortar (TÁBUA, 2) → entregar (BALCÃO, 0) | 20 | 25 |
| Sopa | cortar (TÁBUA, 2) → cozinhar (FOGÃO, 4) → empratar (FOGÃO + BALCÃO, 1) | 35 | 35 |
| Prato do dia | lavar (PIA, 2) → cortar (TÁBUA, 2) → cozinhar (FOGÃO, 5) → empratar (FOGÃO + BALCÃO, 1) | 50 | 45 |

"Empratar" usa fogão e balcão juntos de propósito: é a etapa que pode dar deadlock sem a ordem fixa.

## Pedido (`modelo/pedido.py`)

```python
@dataclass(eq=False)            # identidade, não valor
class Pedido:
    id: int
    receita: Receita
    criado_em: float            # Relogio.agora()
    estado: EstadoPedido = EstadoPedido.AGUARDANDO
    cozinheiro_id: int | None = None

    def prazo(self) -> float: ...                       # criado_em + receita.paciencia
    def paciencia_restante(self, agora) -> float: ...   # fração 0..1, nunca negativa
    def expirou(self, agora) -> bool: ...
```

**Quem escreve no pedido** (uma regra só, as outras specs seguem esta):

| Transição | Quem faz | Onde |
| --- | --- | --- |
| criado (AGUARDANDO) | gerador, via fila | `FilaDePedidos.colocar` (spec 03) |
| AGUARDANDO → EM_PREPARO, `cozinheiro_id` | fila | `FilaDePedidos.retirar`, sob o mutex da fila |
| → ENTREGUE / PERDIDO | **só a `Pontuacao`** | `registrar_entrega` / `registrar_perda` (spec 06) |

Os outros só leem. Ler `estado` sem lock é aceito: é uma referência só, e quem lê (o `Retrato`) tolera um quadro de atraso.

## Config (`config.py`)

```python
@dataclass(frozen=True)
class Config:
    duracao_partida: float = 180.0
    meta_pontos: int = 300
    limite_perdidos: int = 5
    n_cozinheiros: int = 3
    quantidade: Mapping[TipoEstacao, int] = field(
        default_factory=lambda: MappingProxyType({TABUA: 2, PIA: 1, FOGAO: 2, BALCAO: 2}))
    tempo_retirada: float = 1.0            # cliente pegando o prato no balcão
    tamanho_max_fila: int = 6
    intervalo_inicial: float = 8.0         # entre pedidos
    intervalo_minimo: float = 3.0
    bonus_maximo: int = 15
    receitas: tuple[Receita, ...] = RECEITAS
    expiracao: bool = True                 # False só na demonstração de deadlock
    ordem_fixa: bool = True                # False só na demonstração de deadlock
    tick: float = 0.05                     # granularidade de toda espera
    fps: int = 60
    semente: int | None = None             # aleatoriedade reproduzível nos testes

    def validar_para_jogo(self) -> None: ...   # chamado por __main__, não pelos testes

    @classmethod
    def demo_deadlock(cls) -> Config: ...
```

- `quantidade` usa `default_factory` + `MappingProxyType`: dict como valor padrão de dataclass dá erro ao importar, e um dict comum seria mutável dentro de um objeto "frozen".
- `quantidade[BALCAO]` é a **capacidade** do balcão. É um balcão só, com N vagas (o formulário fala em 6 estações: 2 fogões, 2 tábuas, 1 pia, 1 balcão).
- `__post_init__` valida o básico (tempos > 0, quantidades ≥ 1, `n_cozinheiros` ≥ 1). `validar_para_jogo` valida as faixas do jogo de verdade: duração entre 180 e 300 s (RF01) e 3 a 4 cozinheiros. Os testes podem usar 1 cozinheiro e partidas de 3 s.
- `demo_deadlock()`: `ordem_fixa=False`, `expiracao=False`, 1 fogão, balcão de capacidade 1, só a receita Sopa, 2 cozinheiros, `limite_perdidos` alto. Usada por `--demo-deadlock` (spec 09).
- Os testes criam configs com `dataclasses.replace(Config(), ...)`. Nada de número mágico fora daqui (exceto layout da tela, que fica em `ui/layout.py`).

## Retrato (`modelo/retrato.py`)

O único jeito de a interface ler o jogo (RC06). Tudo imutável: a interface pode guardar e desenhar à vontade.

```python
@dataclass(frozen=True)
class PedidoView:
    id: int
    receita: str
    estado: EstadoPedido               # só AGUARDANDO ou EM_PREPARO aparecem
    paciencia: float                   # fração 0..1
    cozinheiro_id: int | None          # quem está preparando
    reservado_para: int | None         # ordem do jogador ainda não cumprida (spec 03)

@dataclass(frozen=True)
class CozinheiroView:
    id: int
    estado: EstadoCozinheiro
    pedido_id: int | None
    etapa: str | None
    progresso: float                   # 0..1 da etapa atual
    segurando: tuple[tuple[TipoEstacao, int], ...]   # (tipo, índice) das estações que já pegou
    esperando: TipoEstacao | None      # estação que está esperando agora
    esperando_ha: float                # segundos esperando a estação atual (0 se não espera)
    espera_total: float                # segundos esperando na partida inteira

@dataclass(frozen=True)
class EstacaoView:
    tipo: TipoEstacao
    indice: int                        # para o balcão, é a vaga
    ocupada_por: int | None

@dataclass(frozen=True)
class GrupoView:
    tipo: TipoEstacao
    capacidade: int
    fila_espera: tuple[int, ...]       # ids dos cozinheiros, na ordem de chegada

@dataclass(frozen=True)
class Retrato:
    estado: EstadoPartida
    tempo_restante: float              # nunca negativo; congela no fim
    pontos: int
    meta: int
    meta_batida: bool
    perdidos: int
    limite_perdidos: int
    entregues: int
    tamanho_max_fila: int
    pedidos: tuple[PedidoView, ...]    # sem ids repetidos, ordenados por id
    cozinheiros: tuple[CozinheiroView, ...]
    estacoes: tuple[EstacaoView, ...]
    grupos: tuple[GrupoView, ...]
    selecionado: int | None            # cozinheiro selecionado pelo jogador (spec 09)

    @classmethod
    def exemplo(cls) -> Retrato: ...   # retrato fixo, para a interface trabalhar sem a lógica
```

**Consistência:** cada parte é copiada sob o próprio lock, uma de cada vez. O retrato pode ficar "desalinhado" por alguns milissegundos (um pedido que saiu da fila e ainda não aparece no cozinheiro, ou aparece nos dois). O `Jogo` tira os ids repetidos (spec 07); o resto some no quadro seguinte. Nunca segurar todos os locks ao mesmo tempo para fazer o retrato.

## Fachada para a interface (`jogo.py`, detalhe na spec 07)

A interface só fala com isto:

```python
class Jogo:
    def __init__(self, config: Config, fonte_tempo: Callable[[], float] = time.monotonic): ...
    def iniciar(self) -> None: ...
    def atualizar(self) -> None: ...       # 1x por quadro: expira pedidos, checa fim de partida
    def retrato(self) -> Retrato: ...
    def selecionar(self, cozinheiro_id: int) -> None: ...
    def atribuir(self, pedido_id: int) -> None: ...   # ao cozinheiro selecionado
    def pausar(self) -> None: ...
    def retomar(self) -> None: ...
    def encerrar(self, timeout: float = 2.0) -> list[str]: ...  # para e espera as threads
```

Fora o `encerrar`, nenhum desses métodos pode bloquear mais que um lock curto: são chamados da thread da interface.

## Infra de testes

- `pyproject.toml` com `requires-python = ">=3.11"` e:
  ```toml
  [tool.pytest.ini_options]
  markers = ["demo: demonstrações que travam de propósito (fora da suíte padrão)"]
  addopts = "-m 'not demo'"
  timeout = 30
  ```
- `requirements.txt` com versões mínimas: `pygame>=2.5`, `pytest>=8`, `pytest-timeout>=2.3`.
- **Teste de concorrência nunca pode travar o pytest:** threads de teste são `daemon`, todo `join` tem `timeout` e é seguido de `assert not t.is_alive()`. O `pytest-timeout` é a rede de segurança.
- Tolerâncias de tempo sempre com folga explícita (ex.: "entre 0,04 e 0,5 s"), nunca "~".

## Critérios de aceite

- [ ] `Config()` e `dataclasses.replace(Config(), n_cozinheiros=1)` funcionam; `Config().quantidade[TABUA] = 3` levanta `TypeError`.
- [ ] `Config(duracao_partida=60).validar_para_jogo()` levanta `ValueError`; `Config()` passa.
- [ ] `Config.demo_deadlock()` tem `ordem_fixa=False`, `expiracao=False`, 1 fogão e balcão de capacidade 1.
- [ ] `Etapa(estacoes=(BALCAO, FOGAO))` vira `(FOGAO, BALCAO)`; estação repetida levanta `ValueError`.
- [ ] Receita com BALCÃO fora da última etapa levanta `ValueError`; toda receita de `RECEITAS` passa.
- [ ] `Pedido.paciencia_restante` vai de 1 a 0 e não fica negativa; `expirou` é verdadeiro a partir do prazo.
- [ ] `Retrato.exemplo()` existe e tem pelo menos um cozinheiro em cada estado.
- [ ] Um teste garante que nada fora de `cozinha/ui` e `__main__.py` importa `pygame`.
- [ ] `pytest` roda a suíte sem os testes `demo`; `pytest -m demo` roda só eles.
