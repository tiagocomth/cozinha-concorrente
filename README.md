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

Você é o **cozinheiro 1** (o de contorno amarelo, "VOCÊ"). Os outros cozinheiros são automáticos — cada um é uma thread — e disputam as mesmas estações com você: se o fogão está ocupado, você entra na fila dele e espera a vez, como eles.

1. Vá ao **quadro de PEDIDOS** (à esquerda) e aperte `E` para pegar o pedido mais antigo (ou clique numa comanda estando perto do quadro).
2. A comanda mostra as etapas (T = tábua, P = pia, F = fogão, B = balcão) e a próxima estação **brilha**. Vá até ela e aperte `E`.
3. A última etapa é no **balcão**: o prato é entregue e você ganha pontos (com bônus se o cliente ainda estava paciente).

Faça a meta antes do tempo acabar sem deixar clientes demais irem embora. Um pedido novo fica alguns segundos só para você antes que um colega possa pegá-lo.

| Tecla | Faz |
| --- | --- |
| WASD / setas | anda |
| `E` / Espaço | pega pedido no quadro / usa a estação |
| `Q` | sai da fila da estação / descarta o pedido na mão |
| `P` | pausa |
| `D` | modo debug: filas de espera, threads vivas, FPS |
| `Esc` | sai da partida (pede confirmação) |

## Como contribuir

- `main` recebe só o que está pronto para apresentar; `develop` é a integração.
- Antes de codar uma parte, leia a spec dela em `docs/specs/`.
- Cada tarefa numa branch `feature/<descricao>` saindo de `develop`, com PR de volta para `develop`.
- Commits em Conventional Commits: `feat(threads): cozinheiro pega pedido da fila`.
- PR só entra com o `pytest` passando.
