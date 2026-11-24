# 09 — Controles e modo debug

**Status:** feita (controles validados no plano da equipe), com a demo pendente de conferência numa janela real
**Cobre:** RF15, RF16, RF19
**Depende de:** 07 (Jogo), 08 (Interface)
**Arquivo:** `cozinha/ui/entrada.py`

## Objetivo

Como o jogador coordena os cozinheiros, e o modo debug que mostra a concorrência por dentro na apresentação.

## Controles

### Modo single player (o jogo de verdade, `Config.single_player()`)

Você é o cozinheiro 1. Os outros são automáticos e disputam as mesmas estações.

| Tecla / ação | Faz | Chama |
| --- | --- | --- |
| WASD / setas | anda pela cozinha (colide com os móveis) | só na interface |
| `E` / Espaço | perto do quadro: pega o pedido mais antigo livre; perto de uma estação: faz a etapa atual | `jogo.pegar_pedido()` / `jogo.usar_estacao(tipo)` |
| clique numa comanda (perto do quadro) | pega aquele pedido | `jogo.pegar_pedido(id)` |
| `Q` | na fila de uma estação: desiste da espera; parado com pedido: descarta | `jogo.desistir()` |
| `P` | pausa / continua | `jogo.pausar()` / `jogo.retomar()` |
| `D` | modo debug | só na interface |
| `Esc` | sair da partida (pede confirmação) | — |

Usando uma estação (ou na fila dela), o avatar vai até ela e não anda até a etapa acabar. Na linha de baixo, uma dica diz o que fazer agora e mostra o resultado de cada comando por alguns segundos. A próxima estação do seu pedido brilha.

### Modo sem jogador (`--demo-deadlock` e testes)

Os cozinheiros são todos automáticos; valem só `P`, `D` e `Esc`. Os controles de reserva antigos (1–4 e clique para atribuir) saíram junto com o modo single player.

### Sair da partida (`Esc`, RF16)

- Na partida (rodando ou pausada com `P`): `Esc` pausa (se não estava) e abre a caixa "Sair da partida? Enter = sim · Esc = não".
  - `Enter` → `jogo.encerrar()` e volta para a tela de início.
  - `Esc` → fecha a caixa e retoma **só se** a partida não estava pausada antes.
- Na tela de início e na de resultado: `Esc` fecha o programa.
- Fechar a janela sai sem perguntar, em qualquer tela (spec 08).

## `entrada.py`

- `traduzir(e, cartoes) -> Acao | None`: função pura de evento → ação (`Interagir`, `Desistir`, `ClicarComanda(id)`, `AlternarPausa`, `AlternarDebug`, `PedirSaida`, `Confirmar`).
- `direcao(teclas) -> (dx, dy)`: WASD/setas seguradas, lidas a cada quadro (o movimento não é evento).

## Modo debug (RF19), para a apresentação

Ligado com `D`, por cima da tela normal:

- **Onde fica:** a parte por estação numa coluna à direita do balcão (as estações continuam visíveis); a parte por cozinheiro no lugar do painel inferior.
- **Por estação:** quem está dentro e a fila de espera completa (`GrupoView.fila_espera`), com há quanto tempo cada um espera (`esperando_ha`).
- **Por cozinheiro:** estado, o que está segurando e o que está esperando (`segurando`, `esperando`), tempo total esperando na partida (`espera_total`).
- **Contadores:** pedidos na fila / máximo, FPS (do `Clock` do Pygame), threads vivas (`threading.active_count()`).
- **Legenda** com a ordem fixa de aquisição: TÁBUA → PIA → FOGÃO → BALCÃO.

### Demonstração de deadlock

`python -m cozinha --demo-deadlock` usa `Config.demo_deadlock()` (spec 00): 2 cozinheiros, 1 fogão, balcão de capacidade 1, só sopa, sem expiração e com a ordem fixa desligada para o cozinheiro de id par (spec 02). A cozinha trava: com o debug ligado, aparece C1 segurando o fogão e esperando o balcão, e C2 segurando o balcão e esperando o fogão. Como nada expira, a trava se mantém até alguém sair.

Roteiro na apresentação: mostrar a trava, sair, e rodar a partida normal com a ordem fixa funcionando.

O `Jogo.encerrar` funciona mesmo travado: quem espera estação sai pelo `cancelar` ligado ao `parar` (specs 01 e 02).

## Fora do escopo

- Remapear teclas, controle (joystick).

## Critérios de aceite

- [x] `traduzir` testado sem janela: `1` → `Selecionar(1)`; `P` → `AlternarPausa()`; `D` → `AlternarDebug()`; `Esc` → `PedirSaida()`; clique dentro do cartão do pedido 7 → `Atribuir(7)`; clique fora → `None`.
- [x] Cursor no pedido 9 e o pedido 9 some do retrato: o próximo `→` não levanta exceção e aponta para um pedido que existe.
- [x] Na partida: selecionar C2 ocupado e clicar no pedido 7 com C1 livre; C1 não pega o 7; quando C2 fica livre, pega exatamente o 7.
- [x] `P` pausa tudo (tempo, paciência, progresso) e `P` de novo retoma.
- [x] `Esc` na partida pausa e pergunta; `Esc` de novo retoma; `Esc` + `Enter` volta ao início com as threads encerradas.
- [x] `Esc` com a partida já pausada por `P`: cancelar a saída mantém pausado.
- [x] `D` mostra e esconde o debug sem afetar o jogo.
- [ ] `--demo-deadlock`: em até 30 s, os dois cozinheiros ficam travados (cada um segurando o que o outro espera) e continuam assim por mais 30 s; fechar a janela encerra o processo em menos de 2 s. *(pendente: sem janela, trava em cerca de 10 s e o teste confere mais 2 s travado; falta a janela real por 30 s e o tempo de fechar pelo botão)*
