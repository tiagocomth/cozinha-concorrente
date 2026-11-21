# 09 — Controles e modo debug

**Status:** proposta, os controles precisam ser validados com o grupo
**Cobre:** RF15, RF16, RF19
**Depende de:** 07 (Jogo), 08 (Interface)
**Arquivo:** `cozinha/ui/entrada.py`

## Objetivo

Como o jogador coordena os cozinheiros, e o modo debug que mostra a concorrência por dentro na apresentação.

## Controles

| Tecla / ação | Faz | Chama |
| --- | --- | --- |
| `1` `2` `3` `4` | Seleciona o cozinheiro | `jogo.selecionar(n)` |
| Clique num pedido | Manda o selecionado fazer esse pedido | `jogo.atribuir(pedido_id)` |
| `←` `→` + `Enter` | Navega pelos pedidos e atribui (alternativa ao mouse) | `jogo.atribuir(pedido_id)` |
| `P` | Pausa / continua | `jogo.pausar()` / `jogo.retomar()` |
| `D` | Liga / desliga o modo debug | só na interface |
| `Esc` | Pede confirmação para sair da partida (abaixo) | — |

**Como a ordem funciona (specs 03 e 07):** a ordem vira uma **reserva** do pedido para aquele cozinheiro. Nenhum outro cozinheiro pega um pedido reservado. Se o escolhido está ocupado, a reserva espera ele terminar o pedido atual; não interrompe o que ele está fazendo. Uma ordem nova para o mesmo cozinheiro substitui a anterior. Cozinheiro sem ordem pega sozinho o pedido mais antigo que não está reservado. Se o cliente for embora antes, a reserva some e o pedido conta como perdido.

**Feedback:** o cozinheiro selecionado tem contorno; o pedido reservado mostra o número do cozinheiro (`PedidoView.reservado_para`) até ser pego.

### Sair da partida (`Esc`, RF16)

- Na partida (rodando ou pausada com `P`): `Esc` pausa (se não estava) e abre a caixa "Sair da partida? Enter = sim · Esc = não".
  - `Enter` → `jogo.encerrar()` e volta para a tela de início.
  - `Esc` → fecha a caixa e retoma **só se** a partida não estava pausada antes.
- Na tela de início e na de resultado: `Esc` fecha o programa.
- Fechar a janela sai sem perguntar, em qualquer tela (spec 08).

## `entrada.py`

```python
@dataclass(frozen=True)
class Selecionar: cozinheiro_id: int
@dataclass(frozen=True)
class Atribuir: pedido_id: int
@dataclass(frozen=True)
class AlternarPausa: ...
@dataclass(frozen=True)
class AlternarDebug: ...
@dataclass(frozen=True)
class PedirSaida: ...
Acao = Selecionar | Atribuir | AlternarPausa | AlternarDebug | PedirSaida

def traduzir(e: pygame.event.Event, retrato: Retrato,
             cursor: int | None, cartoes: Mapping[int, pygame.Rect]) -> tuple[Acao | None, int | None]: ...
```

- Função pura: recebe o evento, o retrato atual, o cursor e os retângulos dos cartões de pedido (calculados pelo `layout.py`), e devolve a ação e o novo cursor. A `TelaJogo` executa a ação no `Jogo` e cuida da caixa de confirmação. Assim dá para testar os controles sem janela.
- **O cursor é um `pedido_id`, não um índice.** A lista de pedidos muda a cada quadro; índice apontaria para outro pedido ou para fora da lista. `←`/`→` movem para o pedido anterior/seguinte em `retrato.pedidos`. Se o pedido do cursor sumiu, o cursor vai para o pedido mais próximo ou vira `None`.

## Modo debug (RF19), para a apresentação

Ligado com `D`, por cima da tela normal:

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

- [ ] `traduzir` testado sem janela: `1` → `Selecionar(1)`; `P` → `AlternarPausa()`; `D` → `AlternarDebug()`; `Esc` → `PedirSaida()`; clique dentro do cartão do pedido 7 → `Atribuir(7)`; clique fora → `None`.
- [ ] Cursor no pedido 9 e o pedido 9 some do retrato: o próximo `→` não levanta exceção e aponta para um pedido que existe.
- [ ] Na partida: selecionar C2 ocupado e clicar no pedido 7 com C1 livre; C1 não pega o 7; quando C2 fica livre, pega exatamente o 7.
- [ ] `P` pausa tudo (tempo, paciência, progresso) e `P` de novo retoma.
- [ ] `Esc` na partida pausa e pergunta; `Esc` de novo retoma; `Esc` + `Enter` volta ao início com as threads encerradas.
- [ ] `Esc` com a partida já pausada por `P`: cancelar a saída mantém pausado.
- [ ] `D` mostra e esconde o debug sem afetar o jogo.
- [ ] `--demo-deadlock`: em até 30 s, os dois cozinheiros ficam travados (cada um segurando o que o outro espera) e continuam assim por mais 30 s; fechar a janela encerra o processo em menos de 2 s.
