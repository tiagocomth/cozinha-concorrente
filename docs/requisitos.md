
# Requisitos — Cozinha Concorrente

> Fonte: as respostas que o grupo enviou no formulário da disciplina ([Respostas do formulário](respostas-do-formulario.md)). O que está aqui e não estava lá é proposta e está marcado como **(proposta)**.

## Visão

Jogo de restaurante em tempo real, em Python + Pygame. O jogador comanda uma cozinha onde 3 a 4 cozinheiros trabalham ao mesmo tempo. Os pedidos chegam sem parar e cada prato precisa ser cortado, cozido, montado e entregue antes que o cliente perca a paciência.

O objetivo da disciplina é a **concorrência**: cada cozinheiro é uma thread e os equipamentos da cozinha são recursos compartilhados, protegidos por semáforos. O visual é simples (formas e sprites básicos) para o tempo ir para a lógica de concorrência.

## Entidades

| Entidade | Quantidade | Papel |
| --- | --- | --- |
| Cozinheiro | 3 a 4 | Thread. Pega um pedido e executa as etapas da receita nas estações. |
| Cliente / pedido | Chegam ao longo da partida | Gerados por uma thread. Cada um tem um prato e um cronômetro de paciência. |
| Fogão | 2 | Estação compartilhada. |
| Tábua de corte | 2 | Estação compartilhada. |
| Pia | 1 | Estação compartilhada. |
| Balcão de entrega | 1 | Estação compartilhada, com capacidade limitada. |
| Fila de pedidos | 1 | Estrutura compartilhada por todos os cozinheiros e pelo gerador. |
| Pontuação | 1 | Estado compartilhado: pontos, clientes perdidos, tempo. |

## Requisitos funcionais

### Partida

- **RF01** — A partida dura um tempo fixo entre 3 e 5 minutos, configurável. Um relógio regressivo fica visível na tela.
- **RF02** — A partida tem uma meta de pontos, mostrada desde o início.
- **RF03** — Vitória: atingir a meta até o fim do tempo.
- **RF04** — Derrota: deixar clientes demais irem embora (limite configurável, **(proposta)** 5) ou terminar o tempo sem atingir a meta.
- **RF05** — Ao fim, uma tela de resultado mostra pontos, pratos entregues, clientes perdidos e se ganhou ou perdeu, com opção de jogar de novo.
- **RF06** — O ritmo acelera ao longo da partida: o intervalo entre pedidos diminui com o tempo.

### Pedidos e clientes

- **RF07** — Uma thread geradora cria pedidos em intervalos e os coloca na fila de pedidos.
- **RF08** — Cada pedido tem um prato (receita) e um cronômetro de paciência, visível como barra.
- **RF09** — Quando a paciência acaba, o cliente vai embora: o pedido sai da fila (ou é abandonado pelo cozinheiro) e conta como cliente perdido.
- **RF10** — A fila de pedidos tem tamanho máximo **(proposta)**. Com a fila cheia, o gerador espera uma vaga.

### Receitas e estações

- **RF11** — Cada prato é uma sequência de etapas, e cada etapa usa um tipo de estação por um tempo. Exemplo **(proposta)**: salada = cortar → montar; sopa = cortar → cozinhar → montar; prato do dia = lavar → cortar → cozinhar → montar.
- **RF12** — Uma estação só pode ser usada por um cozinheiro de cada vez. Quem chega a uma estação ocupada espera, e a espera aparece na tela.
- **RF13** — O balcão de entrega tem capacidade limitada. Com o balcão cheio, o cozinheiro espera para entregar.
- **RF14** — Entregar um prato a tempo soma pontos, com bônus para entregas rápidas (proporcional à paciência que sobrou).

### Jogador

- **RF15** — O jogador coordena os cozinheiros **(proposta para os controles)**: teclas `1`–`4` selecionam um cozinheiro e as setas/clique escolhem qual pedido ele vai preparar. Um pedido escolhido para um cozinheiro fica reservado para ele. Um cozinheiro livre e sem ordem pega sozinho o pedido mais antigo que não está reservado.
- **RF16** — O jogador pode pausar a partida (`P`) e sair (`Esc`).

### Interface

- **RF17** — A tela mostra: as estações (livre / ocupada e por quem), os cozinheiros e o que cada um está fazendo, a fila de pedidos com a paciência de cada um, a pontuação, a meta e o tempo.
- **RF18** — Quando um cozinheiro está esperando uma estação, isso fica evidente (cor ou ícone de espera), para dar para mostrar a concorrência na apresentação.
- **RF19** — **(proposta)** Um modo debug (`D`) mostra, por estação, quem está usando e quem está na fila de espera.

## Requisitos de concorrência

São o centro do trabalho. Detalhes de como implementar em [Concorrência](concorrencia.md).

- **RC01** — Cada cozinheiro roda em uma thread própria. Há também uma thread geradora de pedidos. A interface roda na thread principal (o Pygame exige isso).
- **RC02** — O acesso a cada estação é controlado por semáforo: nunca dois cozinheiros na mesma estação ao mesmo tempo.
- **RC03** — Fila de pedidos e pontuação são protegidas por semáforos binários (sem condição de corrida).
- **RC04** — Sem deadlock: quando uma etapa precisa de mais de uma estação, elas são pegas sempre na mesma ordem fixa.
- **RC05** — Sem inanição: a espera por estação é justa (ordem de chegada), então nenhum cozinheiro fica esperando para sempre.
- **RC06** — A interface não bloqueia os cozinheiros: a cada quadro ela lê uma cópia do estado do jogo, feita rapidamente sob lock, e desenha a partir da cópia.
- **RC07** — Encerramento limpo: ao fim da partida ou ao fechar a janela, todas as threads terminam (sem processo pendurado).

## Requisitos não funcionais

- **RNF01** — Python 3.11+ e Pygame. Concorrência com o módulo `threading` (`Thread`, `Semaphore`, `Lock`, `Condition`).
- **RNF02** — Roda a 60 FPS numa máquina comum, com 4 cozinheiros.
- **RNF03** — Parâmetros (tempo da partida, meta, nº de cozinheiros, tempos das etapas, paciência, capacidade do balcão) ficam num arquivo de configuração, não espalhados no código.
- **RNF04** — Testes automatizados (pytest) para a lógica de concorrência sem interface: exclusão mútua das estações, ausência de deadlock num teste de estresse, pontuação consistente.
- **RNF05** — Gráficos simples: formas e sprites básicos. Nada de arte elaborada.
- **RNF06** — Um comando para rodar (`python -m cozinha`) e instruções no README.

## Fora do escopo

- Multiplayer em rede, níveis múltiplos, loja/upgrades, salvar progresso, som elaborado.

## Em aberto

- [ ] Perguntas 1 e 9 do formulário não vieram nas imagens. Conferir se mudam algo.
- [ ] Nome final do jogo.
- [ ] Prazo de entrega e datas de apresentação.
- [ ] Membros do grupo e divisão de tarefas.
- [ ] Confirmar os controles do jogador (RF15).
