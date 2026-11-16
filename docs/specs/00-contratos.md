# 00 — Contratos

**Status:** proposta, validar com o grupo antes de qualquer código
**Cobre:** RNF01, RNF03, RC06
**Depende de:** nada. Todas as outras specs dependem desta.

## Objetivo

Fixar os tipos e as fronteiras que ligam as partes do jogo, para a lógica (threads) e a interface (Pygame) serem feitas em paralelo. Se algo daqui mudar, avisar o grupo: muda o trabalho de todo mundo.

## Estrutura do pacote

```
cozinha/
├── __main__.py          # python -m cozinha  → ui.app.rodar()
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
```

**Regra de importação:** só `cozinha/ui/` e `__main__.py` importam `pygame`. Tudo o resto roda e é testado sem janela.

## Convenções

- Nomes de domínio em português, sem acento no código (`Cozinheiro`, `fila`, `paciencia`).
- Tipagem em tudo (`from __future__ import annotations`). Dataclasses `frozen=True` para o que é valor.
- Tempo sempre em **segundos de jogo** (`float`), lido de `Relogio.agora()` (spec 06). Nunca `time.time()` direto na lógica: a pausa tem que congelar tudo.
- Nenhuma thread chama `acquire()` sem `timeout`. O loop olha o `Event` de parada a cada volta (RC07).
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

@dataclass(frozen=True)
class Receita:
    nome: str
    etapas: tuple[Etapa, ...]
    pontos: int        # base por entrega a tempo
    paciencia: float   # segundos que o cliente espera
```

`__post_init__` de `Etapa` ordena `estacoes` por valor e rejeita repetidas. Assim quem adquire nunca precisa ordenar.

Receitas iniciais **(proposta, balancear no M5)**:

| Receita | Etapas (estação, segundos) | Pontos | Paciência |
| --- | --- | --- | --- |
| Salada | cortar (TÁBUA, 2) → entregar (BALCÃO, 0) | 20 | 25 |
| Sopa | cortar (TÁBUA, 2) → cozinhar (FOGÃO, 4) → empratar (FOGÃO + BALCÃO, 1) | 35 | 35 |
| Prato do dia | lavar (PIA, 2) → cortar (TÁBUA, 2) → cozinhar (FOGÃO, 5) → empratar (FOGÃO + BALCÃO, 1) | 50 | 45 |

A última etapa de toda receita usa o BALCÃO: é a entrega. "Empratar" usa fogão e balcão juntos de propósito: é a etapa que pode dar deadlock sem a ordem fixa.

## Pedido (`modelo/pedido.py`)

```python
@dataclass
class Pedido:
    id: int
    receita: Receita
    criado_em: float                       # Relogio.agora()
    estado: EstadoPedido = AGUARDANDO
    cozinheiro_id: int | None = None

    def prazo(self) -> float: ...           # criado_em + receita.paciencia
    def paciencia_restante(self, agora) -> float: ...  # fração 0..1, nunca negativa
    def expirou(self, agora) -> bool: ...
```

`Pedido` é mutável, mas **só quem tem o pedido muda o estado**: a fila enquanto está AGUARDANDO, o cozinheiro enquanto está EM_PREPARO. Ninguém mais escreve nele.

## Config (`config.py`)

```python
@dataclass(frozen=True)
class Config:
    duracao_partida: float = 180.0
    meta_pontos: int = 300
    limite_perdidos: int = 5
    n_cozinheiros: int = 3                 # 3 ou 4
    quantidade: Mapping[TipoEstacao, int] = {TABUA: 2, PIA: 1, FOGAO: 2, BALCAO: 2}
    tempo_retirada: float = 1.0            # cliente pegando o prato no balcão
    tamanho_max_fila: int = 6
    intervalo_inicial: float = 8.0         # entre pedidos
    intervalo_minimo: float = 3.0
    bonus_maximo: int = 15
    receitas: tuple[Receita, ...] = RECEITAS
    ordem_fixa: bool = True                # False só no modo demonstração de deadlock (spec 09)
    tick: float = 0.05                     # granularidade dos loops das threads
    timeout_aquisicao: float = 0.1
    fps: int = 60
    semente: int | None = None             # aleatoriedade reproduzível nos testes
```

`quantidade[BALCAO]` é a capacidade do balcão. Os testes criam `Config(...)` com tempos pequenos. Nada de número mágico fora daqui.

## Retrato (`modelo/retrato.py`)

O único jeito de a interface ler o jogo (RC06). Tudo imutável: a interface pode guardar e desenhar à vontade.

```python
@dataclass(frozen=True)
class PedidoView:
    id: int
    receita: str
    estado: EstadoPedido
    paciencia: float               # fração 0..1
    cozinheiro_id: int | None

@dataclass(frozen=True)
class CozinheiroView:
    id: int
    estado: EstadoCozinheiro
    pedido_id: int | None
    etapa: str | None              # nome da etapa atual
    progresso: float               # 0..1 da etapa atual
    estacoes: tuple[tuple[TipoEstacao, int], ...]   # (tipo, índice) que está segurando
    esperando: TipoEstacao | None  # estação que está esperando, se ESPERANDO

@dataclass(frozen=True)
class EstacaoView:
    tipo: TipoEstacao
    indice: int                    # 0..quantidade-1
    ocupada_por: int | None        # id do cozinheiro

@dataclass(frozen=True)
class GrupoView:
    tipo: TipoEstacao
    fila_espera: tuple[int, ...]   # ids dos cozinheiros, na ordem de chegada

@dataclass(frozen=True)
class Retrato:
    estado: EstadoPartida
    tempo_restante: float
    pontos: int
    meta: int
    perdidos: int
    limite_perdidos: int
    entregues: int
    pedidos: tuple[PedidoView, ...]        # AGUARDANDO e EM_PREPARO, do mais antigo ao mais novo
    cozinheiros: tuple[CozinheiroView, ...]
    estacoes: tuple[EstacaoView, ...]
    grupos: tuple[GrupoView, ...]
    selecionado: int | None                # cozinheiro selecionado pelo jogador (spec 09)
```

**Consistência:** cada parte é copiada sob o próprio lock, uma de cada vez. O retrato inteiro pode ficar "desalinhado" por alguns milissegundos (um pedido que acabou de sair da fila e ainda não aparece no cozinheiro). Isso é aceito: some no quadro seguinte. Nunca segurar todos os locks ao mesmo tempo para fazer o retrato.

## Fachada para a interface (`jogo.py`, detalhe na spec 07)

A interface só fala com isto:

```python
class Jogo:
    def __init__(self, config: Config): ...
    def iniciar(self) -> None: ...
    def atualizar(self) -> None: ...       # 1x por quadro: expira pedidos, checa fim de partida
    def retrato(self) -> Retrato: ...
    def selecionar(self, cozinheiro_id: int) -> None: ...
    def atribuir(self, pedido_id: int) -> None: ...   # ao cozinheiro selecionado
    def pausar(self) -> None: ...
    def retomar(self) -> None: ...
    def encerrar(self) -> None: ...        # para e junta todas as threads
```

Nenhum desses métodos pode bloquear mais que um lock curto: são chamados da thread da interface.

## Critérios de aceite

- [ ] Os arquivos de `modelo/tipos.py`, `receita.py`, `pedido.py`, `retrato.py` e `config.py` existem com os tipos acima.
- [ ] `Etapa(estacoes=(BALCAO, FOGAO))` vira `(FOGAO, BALCAO)`; estação repetida levanta `ValueError`.
- [ ] `Pedido.paciencia_restante` vai de 1 a 0 e não fica negativa; `expirou` é verdadeiro a partir do prazo.
- [ ] Toda receita de `RECEITAS` termina numa etapa que usa BALCÃO.
- [ ] Um teste garante que nada fora de `cozinha/ui` importa `pygame`.
