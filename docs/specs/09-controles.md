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
| `Esc` | Na partida: pausa e pergunta se quer sair. Na pausa: sai para o início | `jogo.encerrar()` |

**Como a ordem funciona (spec 04):** a ordem fica guardada no cozinheiro e vale **quando ele terminar o pedido atual**. Ela não interrompe o trabalho em andamento. Cozinheiro sem ordem pega sozinho o pedido mais antigo. Se o pedido escolhido sumir antes (outro pegou ou o cliente foi embora), ele pega o mais antigo.

**Feedback:** o cozinheiro selecionado tem contorno; o pedido ordenado a ele ganha uma marquinha com a cor dele até ser pego.

## `entrada.py`

```python
def traduzir(evento: pygame.event.Event, retrato: Retrato,
             cursor: int) -> tuple[Acao | None, int]: ...
```

Função pura: recebe o evento e o retrato atual e devolve uma `Acao` (`Selecionar(id)`, `Atribuir(pedido_id)`, `AlternarPausa()`, `AlternarDebug()`, `Sair()`) e o novo cursor. A `TelaJogo` executa a ação no `Jogo`. Assim dá para testar os controles sem janela.

O clique usa os retângulos dos cartões de pedido calculados pelo `layout.py`.

## Modo debug (RF19) — para a apresentação

Ligado com `D`, por cima da tela normal:

- **Por estação:** quem está dentro e a fila de espera completa, com o tempo que cada um está esperando.
- **Por cozinheiro:** estado, estações que está segurando, tempo total esperando na partida.
- **Contadores:** pedidos na fila / máximo, FPS, número de threads vivas (`threading.active_count()`).
- **Legenda** lembrando a ordem fixa de aquisição: TÁBUA → PIA → FOGÃO → BALCÃO.

### Demonstração de deadlock **(proposta)**

Rodar com `python -m cozinha --sem-ordem-fixa` liga `config.ordem_fixa=False` com a configuração de demonstração (1 fogão, balcão de capacidade 1, spec 02): metade dos cozinheiros pega as estações na ordem inversa. Com receitas que empratam (fogão + balcão), a cozinha trava. O debug mostra dois cozinheiros, cada um segurando o que o outro espera. Serve para mostrar na apresentação o problema e, em seguida, a mesma partida com a ordem fixa funcionando.

O `Jogo.encerrar` precisa funcionar mesmo travado (as threads saem pelo `parar`, spec 02).

## Fora do escopo

- Remapear teclas, controle (joystick).

## Critérios de aceite

- [ ] `traduzir` testado sem janela: `1` → `Selecionar(1)`; `P` → `AlternarPausa()`; clique dentro do cartão do pedido 7 → `Atribuir(7)`; clique fora → `None`.
- [ ] Na partida: selecionar C2, clicar num pedido; quando C2 fica livre, pega exatamente esse pedido.
- [ ] `P` pausa tudo (tempo, paciência, progresso) e `P` de novo retoma.
- [ ] `D` mostra e esconde o debug sem afetar o jogo.
- [ ] `--sem-ordem-fixa` trava a cozinha em até ~30 s com a configuração de demonstração, e fechar a janela ainda encerra o processo.
