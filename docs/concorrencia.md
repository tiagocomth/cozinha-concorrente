# Concorrência — threads e semáforos

> Visão geral de como os requisitos de concorrência ([Requisitos](requisitos.md), RC01–RC07) viram código. É o documento para a apresentação. O detalhe de cada parte, com interface e critérios de aceite, está nas [specs](specs/README.md).

## Threads

| Thread | Quantas | O que faz |
| --- | --- | --- |
| Principal (interface) | 1 | Loop do Pygame: lê teclado e mouse, chama `jogo.atualizar()` e desenha uma cópia do estado. Só faz tarefas curtas de manutenção (vencer pedidos na fila, checar o fim da partida), sempre com locks curtos. Nunca prepara pratos nem espera estação. |
| `GeradorDePedidos` | 1 | Cria pedidos em intervalos cada vez menores e põe na fila (produtor). |
| `Cozinheiro` | 3–4 | Pega um pedido da fila (consumidor) e executa cada etapa da receita na estação certa. |

Todas são `daemon` e olham um `threading.Event` de parada a cada `tick` (RC07). Ao fim da partida o `Event` é setado, o relógio congela e o `Jogo.encerrar` faz `join` em todas.

## Recursos compartilhados e o que protege cada um

| Recurso | Proteção | Spec |
| --- | --- | --- |
| Estações de um tipo (2 fogões, 2 tábuas, 1 pia) | Um `SemaforoJusto` por tipo (contador, FIFO) + um lock curto para escolher qual estação livre | 01, 02 |
| Balcão de entrega | O mesmo esquema; a quantidade é a capacidade (vagas) | 02 |
| Fila de pedidos | Semáforos `vagas` e `disponiveis` (contadores) + `mutex` (binário) | 03 |
| Pontuação | Semáforo binário | 06 |
| Estado de cada cozinheiro (para a tela) | Lock do próprio cozinheiro, só ele escreve | 04 |
| Estado da partida e relógio | Lock curto | 06 |

## Os quatro desafios da pergunta 10

### 1. Deadlock

**Quando acontece:** na etapa "empratar", o cozinheiro precisa do fogão (a panela) e do balcão ao mesmo tempo. O cozinheiro A pega o fogão e espera o balcão; o B pega o balcão e espera o fogão. Os dois param para sempre.

**Como resolvemos: ordem fixa de aquisição.** Cada tipo de estação tem um número (`TABUA=1, PIA=2, FOGAO=3, BALCAO=4`). Quem precisa de mais de uma pega **sempre em ordem crescente**. Sem ciclo na espera, não há deadlock. Além disso, o cozinheiro solta tudo ao fim de cada etapa: nunca segura uma estação que não está usando.

**Como mostramos:** `python -m cozinha --demo-deadlock` desliga a ordem fixa para metade dos cozinheiros, com 1 fogão e balcão de 1 vaga. A cozinha trava, e o modo debug mostra cada um segurando o que o outro espera. Há também um teste de estresse que trava sem a ordem e termina com ela.

### 2. Condição de corrida (fila e pontuação)

**Quando acontece:** dois cozinheiros leem a fila ao mesmo tempo e pegam o mesmo pedido; ou dois somam pontos ao mesmo tempo e uma soma se perde (`pontos += x` não é atômico).

**Como resolvemos:** semáforo binário em volta de toda leitura e escrita da fila e da pontuação. A fila é o produtor-consumidor clássico:

```python
# gerador                                   # cozinheiro
vagas.acquire()                             disponiveis.acquire()
pedido = criar()        # só com vaga       with mutex: pedido = escolher(fila)   # reservado p/ mim ou o mais antigo
with mutex: fila.append(pedido)             vagas.release()
disponiveis.release()
```

Quando um cliente desiste, o pedido sai da fila e libera a vaga, mas a ficha em `disponiveis` fica: o próximo cozinheiro acorda, acha a fila vazia e tenta de novo ("ficha fantasma"). Isso evita disputar o semáforo com quem já está retirando.

**Como testamos:** 1000 entregas concorrentes resultam exatamente na soma esperada, e nenhum pedido sai da fila duas vezes.

### 3. Inanição

**Quando acontece:** o `threading.Semaphore` do Python não garante ordem de chegada. Um cozinheiro pode perder a vez no fogão repetidamente.

**Como resolvemos: semáforo justo (FIFO).** A classe `SemaforoJusto` usa uma `Condition` e uma fila de senhas. Quem chega pega senha no fim da fila e só passa quando é o primeiro e há vaga. A espera acontece em fatias curtas **sem sair da fila**: a cada fatia a thread confere se precisa parar ou se o cliente foi embora, mas não perde a posição.

**Como testamos:** com o fogão ocupado, três cozinheiros que chegam em sequência recebem o fogão na ordem de chegada; num estresse, a diferença de usos entre eles fica abaixo de 10%.

### 4. Sincronização interface ↔ threads

**Quando acontece:** a tela lê o estado enquanto um cozinheiro está no meio de uma atualização (desenha algo inconsistente), ou segura um lock enquanto desenha (os cozinheiros param).

**Como resolvemos: cópia do estado.** A cada quadro a interface pede ao `Jogo` um `Retrato`: cada parte (fila, cozinheiros, estações, placar) é copiada sob o próprio lock, uma de cada vez, para um objeto imutável. O desenho acontece fora de qualquer lock, a partir da cópia. Os comandos do jogador são chamadas curtas: "fazer o pedido 7" vira uma reserva na fila, que só o cozinheiro escolhido pode retirar.

## Estrutura de código

Detalhada em [specs/00-contratos.md](specs/00-contratos.md). `modelo`, `sync` e `threads` não importam Pygame, então a concorrência é testada sem abrir janela.
