
# Concorrência — threads e semáforos

> Como os requisitos de concorrência ([Requisitos](requisitos.md), RC01–RC07) viram código. É o desenho inicial: muda se a implementação mostrar algo melhor.

## Threads

| Thread | Quantas | O que faz |
| --- | --- | --- |
| Principal (interface) | 1 | Loop do Pygame: lê teclado, tira uma cópia do estado e desenha. Não executa lógica de cozinha. |
| `GeradorDePedidos` | 1 | Cria pedidos em intervalos cada vez menores e põe na fila (produtor). |
| `Cozinheiro` | 3–4 | Pega um pedido da fila (consumidor) e executa cada etapa da receita na estação certa. |
| `Relogio` **(opcional)** | 0–1 | Desconta a paciência dos clientes. Pode ficar dentro do gerador ou da thread principal. |

Todas são `daemon` e olham um `threading.Event` de parada (`jogo.parar`) em cada volta do loop. Ao fim da partida: `parar.set()` e `join()` em todas (RC07).

## Recursos compartilhados e o que protege cada um

| Recurso | Proteção | Por quê |
| --- | --- | --- |
| Cada estação (fogão 1, fogão 2, tábua 1, tábua 2, pia) | Semáforo binário justo (um por estação) | Um cozinheiro por vez (RC02). |
| Tipo de estação (fogões, tábuas) | Semáforo contador (valor 2) | Cozinheiro espera "qualquer fogão livre" em vez de um fogão específico. |
| Balcão de entrega | Semáforo contador com a capacidade | Balcão cheio bloqueia a entrega (RF13). |
| Fila de pedidos | Semáforo binário (mutex) + semáforo `pedidos_disponiveis` (contador) + `vagas` (contador) | Produtor-consumidor clássico (RC03). |
| Pontuação | Semáforo binário | Dois cozinheiros entregando juntos não perdem pontos (RC03). |
| Estado do jogo para a tela | Lock curto só para copiar | Interface não segura ninguém (RC06). |

### Fila de pedidos (produtor-consumidor)

```python
vagas = Semaphore(TAMANHO_MAX_FILA)
pedidos_disponiveis = Semaphore(0)
mutex_fila = Semaphore(1)

# gerador
vagas.acquire()
with mutex_fila: fila.append(pedido)
pedidos_disponiveis.release()

# cozinheiro
pedidos_disponiveis.acquire()
with mutex_fila: pedido = escolher(fila)   # o escolhido pelo jogador ou o mais antigo
vagas.release()
```

Os `acquire` usam `timeout` curto para conseguir checar `parar` e não travar no fim da partida.

## Os quatro desafios da pergunta 10

### 1. Deadlock

**Quando acontece:** uma etapa precisa de duas estações (ex.: montar no balcão segurando a panela do fogão). O cozinheiro A pega o fogão e espera o balcão; o B pega o balcão e espera o fogão. Os dois param para sempre.

**Como resolver — ordem fixa de aquisição:** todas as estações têm um número (`TABUA=1, PIA=2, FOGAO=3, BALCAO=4`). Quem precisa de mais de uma pega **sempre em ordem crescente** e solta em ordem inversa. Sem ciclo na espera, não há deadlock.

Regra complementar: etapas de uma estação só soltam a estação antes de ir para a próxima (não segura o que não está usando).

**Teste:** estresse com muitos cozinheiros, tempos de etapa zero e receitas que pegam duas estações; o teste falha se não terminar em N segundos.

### 2. Condição de corrida (fila e pontuação)

**Quando acontece:** dois cozinheiros leem a fila ao mesmo tempo e pegam o mesmo pedido; ou dois somam pontos ao mesmo tempo e uma soma se perde (`pontos += x` não é atômico).

**Como resolver:** semáforo binário em volta de toda leitura+escrita da fila e da pontuação. Nada de mexer nelas fora do `with`.

**Teste:** 1000 entregas concorrentes; a pontuação final tem que ser exatamente a soma esperada, e nenhum pedido sai da fila duas vezes.

### 3. Inanição

**Quando acontece:** o `threading.Semaphore` do Python não garante ordem de chegada. Um cozinheiro pode perder a vez no fogão repetidamente.

**Como resolver — semáforo justo (FIFO):** uma classe `SemaforoJusto` com `Condition` e uma fila de "senhas". Quem chega pega a senha do fim da fila e só passa quando é a primeira da fila e há vaga.

```python
class SemaforoJusto:
    def __init__(self, valor): self._valor, self._fila, self._cond = valor, deque(), Condition()
    def acquire(self, timeout=None):
        with self._cond:
            senha = object(); self._fila.append(senha)
            ok = self._cond.wait_for(lambda: self._fila[0] is senha and self._valor > 0, timeout)
            if not ok: self._fila.remove(senha); self._cond.notify_all(); return False
            self._fila.popleft(); self._valor -= 1; self._cond.notify_all(); return True
    def release(self):
        with self._cond: self._valor += 1; self._cond.notify_all()
```

A fila de espera de cada estação também alimenta a tela (RF18) e o modo debug (RF19).

**Teste:** contar quantas vezes cada cozinheiro usou o fogão num estresse; a diferença entre o que mais usou e o que menos usou fica dentro de um limite.

### 4. Sincronização interface ↔ threads

**Quando acontece:** a tela lê o estado enquanto um cozinheiro está no meio de uma atualização (desenha um estado inconsistente) ou segura um lock enquanto desenha (cozinheiros param).

**Como resolver — cópia do estado:** a cada quadro, a thread principal pega o lock do estado, copia o necessário para um objeto imutável (`Retrato`) e solta. Desenhar acontece fora do lock, a partir da cópia. Comandos do jogador (selecionar cozinheiro, escolher pedido) viram mensagens numa `queue.Queue` que os cozinheiros leem; a interface nunca muda o estado diretamente.

## Estrutura de código **(proposta)**

```
cozinha/
├── __main__.py        # python -m cozinha
├── config.py          # tempos, quantidades, meta (RNF03)
├── sync.py            # SemaforoJusto e helpers de aquisição ordenada
├── modelo/            # Pedido, Receita, Etapa, Estacao, Pontuacao, Retrato
├── threads/           # Cozinheiro, GeradorDePedidos
├── jogo.py            # monta tudo, inicia e para as threads
└── ui/                # loop do Pygame, desenho das estações, HUD, telas de início/fim
tests/                 # pytest da lógica sem Pygame
```

`modelo`, `sync` e `threads` não importam Pygame: assim dá para testar a concorrência sem abrir janela.
