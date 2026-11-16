
# Planejamento — Cozinha Concorrente

> O prazo ainda não está definido aqui. O plano está em semanas relativas; quando a data de entrega estiver confirmada, trocar "Semana 1" pelas datas reais.

## Marcos

| Marco | O que existe ao final | Requisitos |
| --- | --- | --- |
| **M1 — Base** | Repo com estrutura, config, modelos (Pedido, Receita, Estação) e `SemaforoJusto` com testes. | RNF01, RNF03, RNF04, RC05 |
| **M2 — Cozinha sem tela** | Cozinheiros e gerador rodando como threads, recebendo e entregando pedidos, com log no terminal. Testes de corrida e deadlock passando. | RF07–RF14, RC01–RC05, RC07 |
| **M3 — Tela jogável** | Janela Pygame com estações, cozinheiros, fila, paciência, pontuação e tempo. Controles do jogador. | RF15–RF18, RC06 |
| **M4 — Partida completa** | Início, meta, aceleração, vitória/derrota, tela de resultado, pausa. | RF01–RF06, RF16 |
| **M5 — Entrega** | Balanceamento, modo debug, README, roteiro da apresentação, ensaio. | RF19, RNF02, RNF06 |

## Cronograma sugerido (5 semanas)

| Semana | Foco | Entregável |
| --- | --- | --- |
| 1 | M1 | Repo, `config.py`, modelos, `SemaforoJusto` + testes |
| 2 | M2 | Threads de cozinheiro e gerador, fila produtor-consumidor, pontuação protegida, testes de estresse |
| 3 | M3 | Interface Pygame lendo o `Retrato`; controles |
| 4 | M4 | Regras da partida e telas de início/fim |
| 5 | M5 | Polimento, debug, README, apresentação |

M1 e M2 são o núcleo da nota (concorrência). Se o prazo apertar, corta-se polimento visual e modo debug, nunca os testes de concorrência.

## Divisão de trabalho **(proposta, ajustar com o grupo)**

Dá para trabalhar em paralelo porque a interface só depende do `Retrato`:

- **Concorrência:** `sync.py`, threads, testes de estresse.
- **Modelo e regras:** receitas, pedidos, paciência, pontuação, vitória/derrota.
- **Interface:** Pygame, desenho, HUD, controles, telas.
- **Integração e entrega:** `jogo.py`, README, roteiro e slides da apresentação.

Combinar o formato do `Retrato` logo na semana 1: é o contrato entre quem faz a lógica e quem faz a tela.

## Fluxo no Git

- `main` só recebe o que está pronto para apresentar; `develop` é a integração.
- Cada tarefa numa branch `feature/<descricao>` saindo de `develop`, com PR de volta para `develop`.
- Commits no padrão Conventional Commits (`feat(threads): cozinheiro pega pedido da fila`).
- PR só entra com os testes passando (`pytest`).

## Roteiro da apresentação **(proposta)**

1. O jogo em 30 s: uma partida rodando.
2. Quem são as threads e o que é compartilhado (diagrama).
3. Os quatro problemas (deadlock, corrida, inanição, interface) e como cada um foi resolvido, mostrando o trecho de código.
4. Modo debug ligado: filas de espera das estações ao vivo.
5. Testes de estresse rodando.

## Riscos

| Risco | Mitigação |
| --- | --- |
| Pygame e threads: desenhar fora da thread principal quebra | Só a thread principal toca no Pygame (RC06). |
| Bug de concorrência que só aparece às vezes | Testes de estresse repetidos com tempos zerados; timeout nos `acquire`. |
| Jogo fecha e fica processo pendurado | `Event` de parada + `daemon` + `join` com timeout (RC07). |
| Escopo cresce (níveis, arte, som) | Fora do escopo está escrito em [Requisitos](requisitos.md). |
