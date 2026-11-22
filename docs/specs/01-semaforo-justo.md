# 01 — Semáforo justo

**Status:** feita
**Cobre:** RC05 (inanição), base de RC02
**Depende de:** 00
**Arquivo:** `cozinha/sync.py`

## Objetivo

Um semáforo contador que atende **na ordem de chegada** (FIFO). O `threading.Semaphore` do Python não garante ordem: uma thread pode perder a vez para sempre. Este semáforo é a base das estações (spec 02), e a fila de espera dele aparece na tela.

## Interface

```python
class SemaforoJusto:
    def __init__(self, valor: int) -> None: ...      # valor >= 1

    def acquire(self, dono: int, timeout: float | None = None,
                cancelar: Callable[[], bool] | None = None,
                fatia: float = 0.05) -> bool: ...
    def release(self) -> None: ...

    @property
    def disponivel(self) -> int: ...                  # vagas livres agora
    @property
    def capacidade(self) -> int: ...
    def esperando(self) -> tuple[int, ...]: ...       # donos na fila, na ordem de chegada
```

`dono` é o id do cozinheiro. Serve para a tela (quem está esperando) e para depuração.

## Comportamento

- Implementado com `threading.Condition` e um `deque` de senhas. `_Senha` é `@dataclass(eq=False)` (comparação por identidade: o mesmo dono pode ter duas senhas).
- Cada `acquire` cria uma senha e entra no fim da fila. Uma thread só passa quando **a senha dela é a primeira da fila e há vaga**. Ao passar, sai da fila e decrementa o valor.
- **Espera em fatias, sem sair da fila.** A thread espera no máximo `fatia` segundos por vez e, a cada volta, consulta `cancelar()`. Isso permite parar o jogo ou desistir de um pedido vencido **sem perder a posição** enquanto continua esperando. Sair e entrar de novo na fila a cada fatia acabaria com a ordem de chegada.
- Desiste (sai da fila, acorda todo mundo e devolve `False`) quando `timeout` acaba ou quando `cancelar()` fica verdadeiro.
- `release` incrementa o valor e acorda todo mundo (`notify_all`). Só a primeira da fila consegue passar.
- `release` acima da capacidade levanta `ValueError`: é sinal de bug (liberou o que não pegou).
- `esperando()` e `disponivel` leem sob a `Condition` e devolvem cópias.

Esboço:

```python
def acquire(self, dono, timeout=None, cancelar=None, fatia=0.05):
    limite = None if timeout is None else time.monotonic() + timeout
    with self._cond:
        senha = _Senha(dono)
        self._fila.append(senha)
        while not (self._fila[0] is senha and self._valor > 0):
            restante = None if limite is None else limite - time.monotonic()
            if (restante is not None and restante <= 0) or (cancelar and cancelar()):
                self._fila.remove(senha)        # por identidade
                self._cond.notify_all()          # quem estava atrás pode passar agora
                return False
            self._cond.wait(fatia if restante is None else min(fatia, restante))
        self._fila.popleft()
        self._valor -= 1
        self._cond.notify_all()                  # a próxima pode passar se ainda houver vaga
        return True
```

O `timeout` aqui é tempo real (`time.monotonic`), não tempo de jogo: serve para testes e para não travar. A pausa do jogo é tratada por quem chama (spec 04).

## Casos de borda

- `valor > 1` (dois fogões): duas threads passam seguidas se há duas vagas, sem esperar uma pela outra.
- `timeout=0`: tenta uma vez e não espera.
- Quem desistiu e tenta de novo entra no fim da fila. Desistir é só para parar ou abandonar o pedido, nunca parte da espera normal.

## Fora do escopo

- Prioridade (todo mundo é igual), reentrância (o mesmo dono pegando duas vezes conta como dois).

## Critérios de aceite (pytest)

- [x] **Exclusão:** com `valor=1` e 8 threads fazendo 200 voltas de pegar e soltar, nunca há duas dentro ao mesmo tempo (máximo observado = 1).
- [x] **Capacidade:** com `valor=2`, o máximo observado dentro é exatamente 2.
- [x] **FIFO:** com o semáforo ocupado, threads que chegam em sequência controlada (A, B, C, esperando cada uma aparecer em `esperando()` antes de soltar a próxima) entram na ordem A, B, C.
- [x] **FIFO com espera longa:** com o semáforo ocupado por 1 s e `fatia=0.01`, A, B e C esperando entram na ordem de chegada. Esse critério pega o bug de "sair e voltar para a fila".
- [x] **Sem inanição:** com 4 threads disputando em laço, uma thread que chega é atendida antes de qualquer uma que chegou depois dela. A justiça é medida pela ordem de chegada, não por igualdade de usos (decisão do grupo).
- [x] **Timeout:** `acquire(timeout=0.05)` com o semáforo ocupado devolve `False` entre 0,04 e 0,5 s, e a senha some de `esperando()`.
- [x] **Cancelar:** com `cancelar` virando verdadeiro depois de 0,1 s, `acquire` devolve `False` em menos de 0,1 + 2 × `fatia` s.
- [x] **Desistência no meio da fila** não trava quem está atrás.
- [x] Duas senhas do mesmo dono: cancelar uma não tira a outra.
- [x] `release` sobrando levanta `ValueError`.
