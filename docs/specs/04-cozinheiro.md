# 04 — Cozinheiro

**Status:** feita
**Cobre:** RF11, RF12, RF13, RF14, RF15 (lado da thread), RC01, RC07
**Depende de:** 00, 02, 03, 06 (Relogio, Pontuacao)
**Arquivo:** `cozinha/threads/cozinheiro.py`

## Objetivo

A thread de cada cozinheiro: pega um pedido, executa as etapas da receita nas estações e entrega. É o consumidor da fila e quem disputa as estações.

## Interface

```python
class Cozinheiro(threading.Thread):
    def __init__(self, id: int, fila: FilaDePedidos, cozinha: Cozinha,
                 pontuacao: Pontuacao, relogio: Relogio, config: Config,
                 parar: Event) -> None: ...   # daemon=True, name=f"cozinheiro-{id}"

    def run(self) -> None: ...
    def view(self) -> CozinheiroView: ...
    def pedido_view(self, agora: float) -> PedidoView | None: ...   # o pedido em preparo
    erro: BaseException | None                                      # exceção que matou a thread
```

A ordem do jogador não passa pelo cozinheiro: fica na fila como reserva (spec 03).

## Comportamento

### Loop

```
enquanto não parar:
    relogio.esperar_rodando(parar)
    pedido = fila.retirar(id, timeout=tick)
    se não pegou: espera um tick e continua
    para cada etapa da receita:
        se expirou: perda; sai do for
        reservas = cozinha.ocupar_todas(id, etapa.estacoes,
                                        cancelar=parar ou expirou,
                                        ao_mudar=self._ao_mudar)      # estado ESPERANDO
        se None: se expirou → perda; sai do for     (se foi parar, o while termina)
        trabalha etapa.duracao (na entrega, sem checar expiração)      # estado TRABALHANDO
        se etapa.entrega:
            solta o que não é BALCÃO (o fogão, no empratar)
            espera config.tempo_retirada com o prato no balcão
            pontuacao.registrar_entrega(pedido, agora)
        solta o resto                                                  # sempre, em finally
    volta a LIVRE
```

### Regras

- **Solta tudo no fim de cada etapa**, inclusive com exceção (`try/finally`). Nunca segura estação entre etapas.
- **Entrega:** a etapa que usa o BALCÃO é a última (spec 00). Depois da `duracao`, o cozinheiro solta o fogão (se segurava) e o prato fica no balcão mais `config.tempo_retirada`. Só então o balcão é solto e a entrega registrada. É isso que faz o balcão de capacidade limitada encher (RF13).
- **Expiração:** checada antes de cada etapa, durante a espera por estação (pelo `cancelar`) e a cada tick do trabalho. **Exceção: a etapa de entrega.** Quando o cozinheiro já conseguiu o balcão, o prato está saindo e não conta mais como perda. Com `config.expiracao=False` (demo), nada expira. Expirou → solta tudo e `pontuacao.registrar_perda(pedido)`.
- **Trabalhar** = esperar em passos de `config.tick` somando o tempo de jogo de `relogio.agora()`. A cada passo checa `parar`, a pausa (`esperar_rodando`) e a expiração. Durante a pausa o progresso não anda.
- **Pausa no meio de uma espera:** o cozinheiro continua na fila de espera da estação (não perde a vez). Se conseguir a estação durante a pausa, não começa a trabalhar até retomar.
- **Saída:** com `parar` setado, **interrompe a etapa no próximo tick**, solta tudo e sai do `run` sem registrar entrega. Sai em no máximo alguns ticks.
- **Estado para a tela:** `estado`, `pedido`, `etapa`, `progresso`, `segurando`, `esperando`, `esperando_desde` e `espera_total` ficam sob um `Lock` do próprio cozinheiro. `_ao_mudar` (chamado pela `Cozinha` durante a aquisição) atualiza `segurando`, `esperando` e o tempo de espera. Ele recebe `tuple[Reserva, ...]` e converte cada uma em `(reserva.tipo, reserva.indice)` para o `segurando` do `CozinheiroView`. Só a thread do próprio cozinheiro escreve. `view()` e `pedido_view()` copiam sob esse lock. `pedido_view` devolve `None` se o pedido já está ENTREGUE ou PERDIDO.
- **Exceção inesperada:** o `run` inteiro fica num `try/except BaseException` que solta as estações, registra a perda do pedido atual, guarda a exceção em `self.erro` e loga. O `Jogo` confere `erro` a cada quadro (spec 07). Uma thread nunca morre em silêncio.

## Casos de borda

- Pedido expira enquanto o cozinheiro espera uma estação: o `cancelar` fica verdadeiro, ele sai da fila de espera, solta o que já tinha e registra a perda.
- Duas entregas no mesmo instante: a `Pontuacao` protege a soma (spec 06).
- Entrega registrada depois do fim da partida: a `Pontuacao` já está fechada e ignora (spec 06).

## Fora do escopo

- Coordenadas e caminho. A lógica não tem posição; a tela anima o cozinheiro até a estação a partir do estado (spec 08).

## Critérios de aceite (pytest, com receitas de teste de duração 0,01 s e `tempo_retirada=0`)

- [x] Um cozinheiro e um pedido de salada: o pedido termina ENTREGUE e a pontuação sobe.
- [x] Ao fim de cada etapa nenhuma estação fica com o id do cozinheiro (inspecionar `cozinha.views()`).
- [x] Empratar: o fogão é solto antes do fim da retirada (com `tempo_retirada=0,2`, o fogão fica livre enquanto o balcão ainda está ocupado).
- [x] **Balcão cheio bloqueia a entrega (RF13):** balcão de capacidade 1 ocupado por C1 na retirada; C2 fica ESPERANDO BALCÃO até C1 soltar.
- [x] Pedido que expira numa etapa normal vira PERDIDO, conta como perdido e as estações ficam livres.
- [x] Pedido que expira durante a retirada no balcão conta como ENTREGUE.
- [x] Pedido reservado para este cozinheiro na fila é o que ele pega.
- [x] Pausa: com o relógio pausado, o `progresso` não muda.
- [x] `view()` mostra `segurando=((FOGAO, 0),)` e `esperando=BALCAO` quando ele está nessa situação.
- [x] **Estresse:** 4 cozinheiros, 100 pedidos, balcão de capacidade 1; todos acabam ENTREGUE ou PERDIDO; `join(timeout=10)` sem nenhuma viva.
- [x] `parar.set()` no meio de uma etapa de 5 s: `join(timeout=1)` termina a thread e nada fica ocupado.
- [x] Exceção forçada dentro do `run` (receita com etapa inválida injetada): `erro` preenchido e estações livres.
