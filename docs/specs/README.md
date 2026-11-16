# Specs

Cada spec descreve uma parte do jogo antes do código: a interface (classes e assinaturas), o comportamento, os casos de borda e os **critérios de aceite**, que viram os testes. Uma spec = uma branch `feature/...` = um PR. O PR entra quando os critérios de aceite passam.

Tudo está como **proposta**. A `00-contratos` precisa ser validada pelo grupo antes de qualquer código, porque é ela que deixa a tela e a lógica serem feitas em paralelo.

## Índice

| # | Spec | O que é | Depende de | Marco |
| --- | --- | --- | --- | --- |
| 00 | [Contratos](00-contratos.md) | Pastas, tipos, `Config`, `Retrato`, fachada do `Jogo` | — | M1 |
| 01 | [Semáforo justo](01-semaforo-justo.md) | Semáforo FIFO contra inanição | 00 | M1 |
| 02 | [Estações](02-estacoes.md) | Fogões, tábuas, pia, balcão; ordem fixa contra deadlock | 00, 01 | M2 |
| 03 | [Fila de pedidos](03-fila-de-pedidos.md) | Produtor-consumidor com semáforos | 00 | M2 |
| 04 | [Cozinheiro](04-cozinheiro.md) | A thread que prepara os pratos | 00, 02, 03, 06 | M2 |
| 05 | [Gerador de pedidos](05-gerador-de-pedidos.md) | A thread que cria clientes, com aceleração | 00, 03, 06 | M2 |
| 06 | [Relógio, pontuação e partida](06-partida-e-pontuacao.md) | Tempo pausável, placar sem corrida, vitória/derrota | 00 | M2 / M4 |
| 07 | [Jogo](07-jogo.md) | Integração: monta, inicia, encerra, faz o `Retrato` | 00–06 | M2 / M4 |
| 08 | [Interface](08-interface.md) | Telas em Pygame | 00, 07 | M3 / M4 |
| 09 | [Controles e debug](09-controles.md) | Teclas, mouse, modo debug, demonstração de deadlock | 07, 08 | M3 / M5 |

## Ordem e paralelismo

```
00 ──┬── 01 ── 02 ──┐
     ├── 03 ────────┼── 04 ──┐
     ├── 06 ────────┴── 05 ──┼── 07 ──┐
     └── 08 (com Retrato falso) ──────┴── 09
```

Depois da 00 fechada, quatro pessoas começam juntas:

- **Concorrência:** 01 → 02
- **Modelo e regras:** 03 e 06
- **Interface:** 08, desenhando um `Retrato` de exemplo escrito à mão, sem esperar a lógica
- **Integração:** testes de estresse comuns, depois 04/05 com quem terminar primeiro, e por fim a 07

## Como usar uma spec

1. Leia a spec inteira e tire dúvidas antes de codar. Se mudar algo, mude a spec no mesmo PR.
2. Escreva os testes a partir dos **critérios de aceite** primeiro.
3. Implemente até os testes passarem.
4. Marque os critérios no PR e mude o **Status** da spec para "feita".

## Decisões em aberto

- Controles do jogador (09): clique + teclas está bom?
- Receitas, pontos e paciência (00): balancear no M5.
- `ocupar` em loop de timeouts curtos pode fazer o cozinheiro perder a posição na fila de espera (02). Aceitar ou trocar?
- Bater a meta antes do tempo encerra a partida ou não (06)? Hoje, não.
