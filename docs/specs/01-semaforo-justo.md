# 01 — Semáforo justo

**Status:** proposta
**Cobre:** RC05 (inanição), base de RC02
**Depende de:** 00
**Arquivo:** `cozinha/sync.py`

## Objetivo

Um semáforo contador que atende **na ordem de chegada** (FIFO). O `threading.Semaphore` do Python não garante ordem: uma thread pode perder a vez para sempre. Este semáforo é a base das estações (spec 02), e a fila de espera dele aparece na tela.

## Interface

```python
class SemaforoJusto:
    def __init__(self, valor: int) -> None: ...      # valor >= 1

    def acquire(self, dono: int, timeout: float | None = None) -> bool: ...
    def release(self) -> None: ...

    @property
    def disponivel(self) -> int: ...                  # vagas livres agora
    def esperando(self) -> tuple[int, ...]: ...       # donos na fila, na ordem de chegada
```

`dono` é o id do cozinheiro. Serve para a tela (quem está esperando) e para depuração.

## Comportamento

- Implementado com `threading.Condition` e um `deque` de senhas. Cada `acquire` cria uma senha com o `dono` e entra no fim da fila.
- Uma thread só passa quando **a senha dela é a primeira da fila e há vaga**. Ao passar, sai da fila e decrementa o valor.
- `release` incrementa o valor e acorda todo mundo (`notify_all`). Só a primeira da fila consegue passar.
- **Timeout:** se o tempo acaba, a senha sai da fila (mesmo do meio), o método devolve `False` e acorda todo mundo, porque a próxima da fila pode estar liberada agora.
- `release` acima do valor inicial levanta `ValueError`: é sinal de bug (liberou o que não pegou).
- `esperando()` e `disponivel` leem sob a `Condition` e devolvem cópias.

Esboço:

```python
def acquire(self, dono, timeout=None):
    with self._cond:
        senha = _Senha(dono)
        self._fila.append(senha)
        pode = lambda: self._fila[0] is senha and self._valor > 0
        if not self._cond.wait_for(pode, timeout):
            self._fila.remove(senha)
            self._cond.notify_all()
            return False
        self._fila.popleft()
        self._valor -= 1
        self._cond.notify_all()   # a próxima pode passar se ainda houver vaga
        return True
```

## Casos de borda

- `valor > 1` (dois fogões): duas threads passam seguidas se há duas vagas, sem esperar uma pela outra.
- Timeout zero: tenta uma vez e não espera.
- Quem desiste por timeout não "fura" a fila na próxima tentativa: entra no fim de novo.

## Fora do escopo

- Prioridade (todo mundo é igual), reentrância (o mesmo dono pegando duas vezes conta como dois).

## Critérios de aceite (pytest)

- [ ] **Exclusão:** com `valor=1` e 8 threads fazendo 200 voltas de pegar/soltar, nunca há duas dentro ao mesmo tempo (contador interno protegido, máximo observado = 1).
- [ ] **Capacidade:** com `valor=2`, o máximo observado dentro é exatamente 2.
- [ ] **FIFO:** com o semáforo ocupado, threads que chegam em sequência controlada (A, B, C) entram na ordem A, B, C.
- [ ] **Justiça:** 4 threads disputando por 2 s; a diferença de usos entre a que mais usou e a que menos usou é menor que 10% do total.
- [ ] **Timeout:** `acquire(timeout=0.05)` com o semáforo ocupado devolve `False` em ~0,05 s e a senha some de `esperando()`.
- [ ] **Timeout no meio da fila** não trava quem está atrás.
- [ ] `release` sobrando levanta `ValueError`.
- [ ] `esperando()` mostra os donos na ordem de chegada.
