# Cozinha Concorrente

Jogo de restaurante em tempo real feito para a disciplina, em Python + Pygame. O jogador comanda uma cozinha onde 3 a 4 cozinheiros trabalham ao mesmo tempo e disputam poucos equipamentos (2 fogões, 2 tábuas, 1 pia e o balcão de entrega) para entregar os pratos antes que os clientes percam a paciência.

Cada cozinheiro é uma **thread** e cada equipamento é um **recurso compartilhado protegido por semáforo**. O foco do trabalho é a concorrência: evitar deadlock, condição de corrida e inanição, e manter a interface fluida sem travar os cozinheiros.

> Nome provisório. O projeto está no começo: por enquanto o repositório tem só a documentação.

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [Requisitos](docs/requisitos.md) | O que o jogo faz: requisitos funcionais, de concorrência e não funcionais |
| [Concorrência](docs/concorrencia.md) | Threads, recursos compartilhados e como resolvemos cada problema |
| [Specs](docs/specs/README.md) | Uma spec por parte do jogo: interface, comportamento e critérios de aceite |
| [Planejamento](docs/planejamento.md) | Marcos, cronograma, divisão de trabalho, fluxo no Git e apresentação |
| [Respostas do formulário](docs/respostas-do-formulario.md) | As respostas do grupo que deram origem a tudo |

## Como rodar

Requer Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m cozinha                # inicia o jogo (quando o código existir)
pytest                           # testes da lógica de concorrência
```

## Como contribuir

- `main` recebe só o que está pronto para apresentar; `develop` é a integração.
- Antes de codar uma parte, leia a spec dela em `docs/specs/`.
- Cada tarefa numa branch `feature/<descricao>` saindo de `develop`, com PR de volta para `develop`.
- Commits em Conventional Commits: `feat(threads): cozinheiro pega pedido da fila`.
- PR só entra com o `pytest` passando.
