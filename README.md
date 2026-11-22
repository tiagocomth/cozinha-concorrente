# Cozinha Concorrente

Jogo de restaurante em tempo real feito para a disciplina, em Python + Pygame. O jogador comanda uma cozinha onde 3 a 4 cozinheiros trabalham ao mesmo tempo e disputam poucos equipamentos (2 fogões, 2 tábuas, 1 pia e o balcão de entrega) para entregar os pratos antes que os clientes percam a paciência.

Cada cozinheiro é uma **thread** e cada equipamento é um **recurso compartilhado protegido por semáforo**. O foco do trabalho é a concorrência: evitar deadlock, condição de corrida e inanição, e manter a interface fluida sem travar os cozinheiros.

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [Requisitos](docs/requisitos.md) | O que o jogo faz: requisitos funcionais, de concorrência e não funcionais |
| [Concorrência](docs/concorrencia.md) | Threads, recursos compartilhados e como resolvemos cada problema |
| [Specs](docs/specs/README.md) | Uma spec por parte do jogo: interface, comportamento e critérios de aceite |
| [Planejamento](docs/planejamento.md) | Marcos, cronograma, divisão de trabalho, fluxo no Git e apresentação |
| [Respostas do formulário](docs/respostas-do-formulario.md) | As respostas do grupo que deram origem a tudo |

## Como rodar

Requer **Python 3.11, 3.12 ou 3.13**. O pygame 2.6.1 ainda não tem pacote pronto para o Python 3.14: nele, o `pip` tenta compilar o pygame e falha por falta do SDL.

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

```bash
python -m cozinha                # o jogo
python -m cozinha --demo-deadlock  # demonstração: a cozinha trava sem a ordem fixa
pytest                           # testes (sem abrir janela)
pytest -m demo                   # testes de demonstração, que travam de propósito
```

## Como jogar

Os pedidos chegam cada vez mais rápido. Cada cozinheiro pega sozinho o pedido mais antigo, mas você pode dar ordens. Faça a meta de pontos antes do tempo acabar, sem perder clientes demais. Entregas rápidas valem bônus.

| Tecla / ação | Faz |
| --- | --- |
| `1` `2` `3` `4` | Seleciona o cozinheiro |
| Clique num pedido | Manda o selecionado fazer esse pedido |
| `←` `→` + `Enter` | Navega pelos pedidos e atribui (alternativa ao mouse) |
| `P` | Pausa / continua |
| `D` | Liga / desliga o modo debug (filas de espera, FPS, threads) |
| `Esc` | Sai da partida (pede confirmação) |

Uma ordem vira uma **reserva**: nenhum outro cozinheiro pega aquele pedido, e o escolhido o faz assim que terminar o que está fazendo.

## Como contribuir

- `main` recebe só o que está pronto para apresentar; `develop` é a integração.
- Antes de codar uma parte, leia a spec dela em `docs/specs/`.
- Cada tarefa numa branch `feature/<descricao>` saindo de `develop`, com PR de volta para `develop`.
- Commits em Conventional Commits: `feat(threads): cozinheiro pega pedido da fila`.
- PR só entra com o `pytest` passando.
