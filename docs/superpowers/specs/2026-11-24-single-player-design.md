# Single player: você é um dos cozinheiros — Design

**Data:** 2026-11-24
**Status:** proposta, aguardando aprovação (revisada por um leitor-construtor)

## Por quê

Hoje o jogo se joga sozinho: os cozinheiros (threads) pegam o pedido mais antigo e fazem tudo; o jogador só "reserva" pedidos que eles já iam fazer. Uma partida inteira termina sem tocar em nada. Além disso, a tela parece um painel de depuração (retângulos e texto).

O jogador deve **receber o pedido e interagir com os elementos da cozinha**: andar, ir às estações e preparar o prato ele mesmo, sentindo na pele a disputa por equipamentos — que é exatamente o tema do trabalho (concorrência).

## Objetivos

- O jogador controla **um** cozinheiro com o teclado: anda pela cozinha, pega pedidos, usa as estações na ordem da receita e entrega no balcão.
- Os outros cozinheiros continuam **threads automáticas** (colegas de equipe) disputando as **mesmas** estações pelo mesmo `SemaforoJusto` e pela mesma ordem fixa. Se o fogão está ocupado, o jogador entra na fila de espera do fogão e espera a vez, igual a eles.
- O cozinheiro do jogador **também é uma thread**, que executa os comandos vindos da tela. A tela continua sem tocar em semáforo nem em fila (RC06): fala só com o `Jogo`.
- UI nova, com cara de jogo: cozinha vista de cima (piso, bancadas, estações desenhadas como objetos reconhecíveis), cozinheiros com chapéu, comandas de pedido com as etapas, feedback claro do que fazer em seguida.

## Não-objetivos

- Multiplayer, sprites/arte externa, som, música, mapas diferentes, salvar recorde.
- Física ou caminho com obstáculos inteligente para os cozinheiros automáticos (eles continuam deslizando até a estação, só na tela).

## Anti-objetivos (seria fracasso mesmo funcionando)

- O jogador "fura a fila" das estações ou usa uma estação ocupada: a exclusão mútua e a justiça FIFO valem para ele também.
- A tela segura um lock ou trava esperando uma estação (o loop tem que continuar a 60 FPS enquanto o jogador espera).
- A demonstração de deadlock e os testes de concorrência atuais deixam de funcionar.

## Abordagens consideradas

1. **Você é um dos cozinheiros (escolhida pelo usuário).** Avatar controlado por WASD/setas, `E` interage com a estação próxima; os outros cozinheiros são threads. A disputa por estações é vivida pelo jogador. Mais trabalho: movimento, colisão simples e UI nova.
2. **Chefe que despacha.** Cozinheiros não pegam nada sozinhos; o jogador arrasta pedidos e clica nas estações na ordem. Mais barata, reaproveita a UI atual, mas parece um painel de controle.
3. **Só o cozinheiro do jogador.** Simples, mas sem threads disputando nada: perde o tema do trabalho. Descartada.

## Como funciona

### Modos

- `Config.jogador: bool = True`. Com `True`, o cozinheiro **1** é o do jogador e os ids `2..n_cozinheiros` são automáticos. Com `False`, o comportamento atual (todos automáticos e controles de reserva da spec 09).
- `Config.demo_deadlock()` usa `jogador=False` (a demo continua igual).
- `validar_para_jogo`: continua 3 a 4 cozinheiros **no total**, contando o do jogador.

### O cozinheiro do jogador (thread `CozinheiroJogador`, `cozinha/threads/jogador.py`)

- Subclasse de `Cozinheiro`: reaproveita `_fazer_etapa`, `_trabalhar`, `_ao_mudar`, `view`, `pedido_view` e o tratamento de exceção (o `erro` aparece no `Jogo.atualizar` como hoje).
- Recebe comandos por uma `queue.Queue` (thread-safe, sem lock nosso):
  - `PegarPedido(pedido_id)`: reserva esse pedido para si (`fila.reservar`) e o retira (`fila.retirar`). Se outro cozinheiro levou antes, o comando falha e a tela mostra um aviso.
  - `UsarEstacao(tipo)`: se `tipo` pertence à etapa atual do pedido, executa a etapa com o mesmo código dos automáticos: `cozinha.ocupar_todas` (espera na fila do semáforo, estado ESPERANDO) → trabalha a duração → solta. Estação errada: falha com o motivo ("precisa da TÁBUA").
  - `Descartar()`: joga fora o pedido atual (conta como perdido) — saída para não ficar preso a um pedido impossível.
- Enquanto espera comando, checa `parar` a cada `tick` (RC07) e a expiração do pedido: se a paciência acabar com o pedido na mão, ele é perdido, como para os automáticos.
- Durante a pausa, comandos ficam na fila e só são executados ao retomar.
- O resultado de cada comando (ok / motivo da falha) fica num campo `mensagem` do estado, lido pela tela no retrato (sem callback para a thread da tela).

### O `Jogo`

- Cria `CozinheiroJogador` como cozinheiro 1 quando `config.jogador`.
- Novos comandos, todos sem bloquear (só colocam na fila de comandos): `pegar_pedido(pedido_id)`, `usar_estacao(tipo)`, `descartar()`.
- `CozinheiroView` ganha campos com valor padrão (compatível): `jogador: bool = False`, `proxima: tuple[TipoEstacao, ...] = ()` (estações da etapa que falta fazer) e `mensagem: str | None = None`.

### Os cozinheiros automáticos

- Continuam iguais, mas **não pegam pedidos reservados para o jogador** (já é a regra da fila: reserva vale contra todos).
- Pegam qualquer outro pedido, então o jogador compete por pedidos também — quem chega primeiro leva.

### A tela (UI nova)

Cozinha vista de cima, 1280×720:

```
┌───────────────────────────────────────────────────────────────┐
│ ⏱ 2:41   ★ 120/300 ███████░░░   ✗ ● ○ ○ ○ ○         ⏸ P  ? D │  HUD
├───────────────────────────────────────────────────────────────┤
│ [#7 Sopa  ▓▓▓▓░  🔪→🔥→🍽] [#8 Salada ▓▓░░ 🔪→🍽] ...          │  comandas
├───────────────────────────────────────────────────────────────┤
│   ┌QUADRO┐                                                     │
│   │ pega │   [TÁBUA][TÁBUA]   [PIA]    [FOGÃO][FOGÃO]  [BALCÃO]│
│   └──────┘                                                     │
│        (1)← você          piso de cozinha            (3)       │
│                    (2)                                         │
│  "Pegue um pedido no quadro (E)"              mensagem / dica  │
└───────────────────────────────────────────────────────────────┘
```

- **Estações desenhadas como objetos:** tábua com faca, pia com torneira, fogão com bocas (acesas quando em uso), balcão com pratos. Barra de progresso em cima da estação em uso; fila de espera ao lado, como hoje.
- **Cozinheiros:** círculo com chapéu de chef e número; o do jogador maior, com contorno e o rótulo "VOCÊ".
- **Quadro de pedidos (passa-pratos):** ponto da cozinha onde o jogador pega pedidos. Perto dele, `E` pega o pedido mais antigo disponível; clicar numa comanda pega aquela.
- **Comandas:** cada pedido mostra as etapas como uma trilha de ícones (estação de cada etapa), com a etapa atual destacada no pedido do jogador.
- **Guia:** a estação da próxima etapa do jogador pisca/brilha, e uma linha de dica diz o que fazer ("Vá ao FOGÃO e aperte E"). Mensagens de falha aparecem ali por 2 s.
- **Movimento:** WASD/setas a velocidade fixa, preso ao piso, colisão simples com as estações (retângulos). "Perto" de uma estação = dentro de uma área de interação em volta dela. Usar uma estação prende o avatar nela até a etapa acabar (ou até a desistência por expiração).
- Telas de início e resultado redesenhadas no mesmo estilo (resultado com 0 a 3 estrelas pela fração da meta).

### Controles (modo jogador)

| Tecla | Faz |
| --- | --- |
| WASD / setas | anda |
| `E` / Espaço | interage: no quadro pega pedido; na estação certa, faz a etapa |
| clique numa comanda (perto do quadro) | pega aquele pedido |
| `Q` | descarta o pedido na mão |
| `P` | pausa |
| `D` | modo debug |
| `Esc` | sair da partida (com confirmação) |

## Restrições

- Só `cozinha/ui` e `__main__.py` importam pygame; só a thread principal desenha (RC06).
- Nenhum método do `Jogo` chamado pela tela bloqueia (comandos vão para uma `queue.Queue`).
- A lógica continua sem coordenadas: posição, colisão e "perto de" são só da tela.
- Demo de deadlock (`--demo-deadlock`) e toda a suíte atual continuam passando.
- Python 3.12 / pygame 2.6; formas desenhadas com `pygame.draw`, sem arquivos de imagem.

## Decisões de detalhe (chamadas do Claude, revise)

1. **Empratar (FOGÃO + BALCÃO):** um `E` em qualquer uma das duas estações da etapa pede as duas de uma vez, pelo mesmo `ocupar_todas` dos automáticos (fogão antes do balcão). O jogador nunca segura uma estação enquanto anda até outra: isso traria de volta o risco de deadlock que a ordem fixa evita. Na tela, o avatar vai para o balcão (a estação de maior tipo), como os automáticos.
2. **Tipo, não estação específica:** o `E` pede o *tipo* (TÁBUA, FOGÃO...). O semáforo entrega a primeira livre, como para todos; o avatar desliza até a estação que recebeu. Pedir por índice mexeria na justiça FIFO da spec 01.
3. **Desistir da espera:** `Q` enquanto espera na fila de uma estação sai da fila (o pedido continua na mão; o `cancelar` do `ocupar_todas` passa a olhar também um "desistir" do jogador). `Q` com o pedido na mão e parado descarta o pedido (perdido). Trabalhando, não dá para interromper (a etapa dura poucos segundos).
4. **Modo sem jogador:** `jogador=False` só existe para os testes e para `--demo-deadlock`. A UI nova desenha os dois modos; sem jogador, não há avatar nem dica, e valem só `P`, `D` e `Esc`. Os controles de reserva da spec 09 (1–4, clique para atribuir) saem; a spec 09 é atualizada.
5. **Balanceamento:** um humano andando é mais lento que uma thread. No modo jogador a meta passa a ser 200 pontos (e 2 cozinheiros automáticos + você). O ajuste fino fica para uma rodada de teste jogando, no fim da implementação. Testes que dependem de `Config()` não mudam (a meta nova vale só com `jogador=True`, via `Config.single_player()` ou o padrão — o plano decide qual, mantendo os testes atuais).

## O que fica para quem construir

- Paleta, tamanhos, posições exatas, desenho de cada estação e do chapéu.
- Formato exato das mensagens e do tempo que ficam na tela.
- Como dividir em tarefas e PRs (sugestão: lógica do jogador → UI do jogo → telas de início/resultado).
