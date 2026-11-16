# 08 — Interface (Pygame)

**Status:** proposta
**Cobre:** RF01, RF05, RF08, RF17, RF18, RC06, RNF02, RNF05
**Depende de:** 00 (Retrato), 07 (Jogo)
**Arquivos:** `cozinha/ui/`

## Objetivo

Mostrar a cozinha funcionando de um jeito que deixe a concorrência **visível**: quem está usando cada estação, quem está esperando e há quanto tempo. Visual simples (formas e texto), a 60 FPS.

## Estrutura

```
cozinha/ui/
├── app.py         # rodar(): janela, loop principal, troca de telas
├── telas.py       # TelaInicio, TelaJogo, TelaResultado
├── desenho.py     # funções puras: desenhar_estacao, desenhar_cozinheiro, barra...
├── layout.py      # posições e tamanhos (constantes), cores
└── entrada.py     # teclas → comandos (spec 09)
```

## Loop principal (`app.py`)

```python
def rodar(config: Config = Config()) -> None:
    pygame.init(); tela = pygame.display.set_mode((1280, 720)); relogio = pygame.time.Clock()
    atual = TelaInicio(config)
    while atual is not None:
        for evento in pygame.event.get(): atual = atual.evento(evento) or atual
        atual.atualizar()          # TelaJogo chama jogo.atualizar()
        atual.desenhar(tela)       # TelaJogo desenha jogo.retrato()
        pygame.display.flip(); relogio.tick(config.fps)
```

- Fechar a janela em qualquer tela → `jogo.encerrar()` e sair. Nunca deixar processo pendurado.
- **Só esta thread** chama Pygame. Os cozinheiros nunca desenham nem leem eventos.
- A tela lê **um** `Retrato` por quadro e desenha tudo a partir dele (RC06).

## Telas

### Início

Nome do jogo, uma frase do objetivo, os controles (spec 09) e "Enter para começar". Enter → cria `Jogo(config)`, `iniciar()`, vai para a TelaJogo.

### Jogo (1280×720) **(proposta de layout)**

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⏱ 2:41      Pontos 120 / 300 ████████░░░░        Perdidos ● ● ○ ○ ○  │  HUD
├──────────────────────────────────────────────────────────────────────┤
│ Pedidos:  [#7 Sopa ▓▓▓▓░] [#8 Salada ▓▓░░░] [#9 Prato ▓▓▓▓▓]  ...    │  fila
├──────────────────────────────────────────────────────────────────────┤
│  TÁBUA 1   TÁBUA 2    PIA      FOGÃO 1   FOGÃO 2    BALCÃO  BALCÃO   │
│  [ C1 ]    [    ]    [ C3 ]    [ C2 ]    [    ]     [    ]  [    ]   │  estações
│            espera:            espera: C4                             │
│                                                                      │
│  C1 cortando #7 ▓▓▓░░   C2 cozinhando #5 ▓░░░░   C3 lavando #8 ▓▓░░░  │  cozinheiros
│  C4 ESPERANDO FOGÃO (2,3 s)                                          │
└──────────────────────────────────────────────────────────────────────┘
```

- **Estação:** retângulo; cinza livre, cor do cozinheiro quando ocupada, com o número dele. Abaixo, a fila de espera do grupo (`GrupoView.fila_espera`) com as cores de quem espera.
- **Cozinheiro:** cada um tem uma cor fixa. Mostra estado, pedido, etapa e barra de progresso. **ESPERANDO** em destaque (cor de alerta + nome da estação), que é o que mostra a disputa na apresentação (RF18). O selecionado tem contorno (spec 09).
- **Pedido:** cartão com id, receita e barra de paciência (verde → amarelo → vermelho, RF08). Em preparo mostra a cor do cozinheiro. Os cartões são clicáveis (spec 09).
- **HUD:** tempo restante (mm:ss), pontos/meta com barra, perdidos/limite como bolinhas.
- **Pausa:** véu escuro com "PAUSADO — P para continuar".

### Resultado (RF05)

VITÓRIA ou DERROTA, pontos/meta, pratos entregues, clientes perdidos. "Enter para jogar de novo" (novo `Jogo`) e "Esc para sair".

## Regras

- Cores, tamanhos e posições em `layout.py`, sem número solto nas funções de desenho.
- Funções de `desenho.py` recebem a superfície e uma View: sem estado, sem acesso ao `Jogo`.
- Uma fonte só (a padrão do Pygame), em 2 ou 3 tamanhos.
- Sprites são opcionais: formas primeiro. Se der tempo, trocar por sprites simples sem mudar a lógica.

## Fora do escopo

- Animação de caminhada, som, redimensionar a janela, temas.

## Critérios de aceite

- [ ] `python -m cozinha` abre a tela de início; Enter começa; a partida termina sozinha na tela de resultado; Enter joga de novo.
- [ ] Mantém ~60 FPS com 4 cozinheiros (mostrar FPS no modo debug, spec 09).
- [ ] Toda estação ocupada mostra quem está nela; todo cozinheiro esperando aparece na fila de espera da estação certa.
- [ ] Barra de paciência muda de cor e o cartão some quando o cliente vai embora.
- [ ] Fechar a janela no meio da partida encerra o processo em menos de 2 s.
- [ ] Teste automático (sem janela, `SDL_VIDEODRIVER=dummy`): desenhar um `Retrato` de exemplo não levanta exceção.
