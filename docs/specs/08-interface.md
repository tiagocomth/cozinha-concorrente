# 08 — Interface (Pygame)

**Status:** feita
**Cobre:** RF01, RF02, RF05, RF08, RF17, RF18, RC06, RNF02, RNF05, RNF06
**Depende de:** 00 (Retrato), 07 (Jogo)
**Arquivos:** `cozinha/ui/`, `cozinha/__main__.py`, README

## Objetivo

Mostrar a cozinha funcionando de um jeito que deixe a concorrência **visível**: os cozinheiros indo até as estações, quem está usando cada uma, quem está esperando e há quanto tempo. Visual simples (formas e texto), a 60 FPS.

## Estrutura

```
cozinha/ui/
├── app.py         # rodar(config): janela, loop principal, troca de telas
├── telas.py       # Tela (protocolo), SAIR, TelaInicio, TelaJogo, TelaResultado
├── desenho.py     # funções puras: desenhar_estacao, desenhar_cozinheiro, barra...
├── animacao.py    # posição atual de cada cozinheiro, interpolada até o alvo
├── layout.py      # tamanho da janela, posições, cores, fontes (constantes)
└── entrada.py     # teclas e mouse → ações (spec 09)
```

## Telas e loop principal

```python
SAIR = object()   # sentinela: fechar o programa

class Tela(Protocol):
    def evento(self, e: pygame.event.Event) -> Tela | object | None: ...  # None = continua nesta tela
    def proxima(self) -> Tela | object | None: ...  # chamada depois de atualizar: ex. partida acabou → resultado
    def atualizar(self, dt: float) -> None: ...
    def desenhar(self, superficie: pygame.Surface) -> None: ...
    def fechar(self) -> None: ...      # TelaJogo: jogo.encerrar()

def rodar(config: Config) -> None:
    pygame.init(); superficie = pygame.display.set_mode(layout.JANELA); clock = pygame.time.Clock()
    atual: Tela = TelaInicio(config)
    try:
        while True:
            dt = clock.tick(config.fps) / 1000
            proxima = None
            for e in pygame.event.get():
                proxima = SAIR if e.type == pygame.QUIT else atual.evento(e)
                if proxima is not None: break
            if proxima is None:
                atual.atualizar(dt)
                proxima = atual.proxima()
            if proxima is SAIR: break
            if proxima is not None: atual.fechar(); atual = proxima; continue
            atual.desenhar(superficie)
            pygame.display.flip()
    finally:
        atual.fechar()
        pygame.quit()
```

- `None` quer dizer "continua"; `SAIR` é um valor próprio. `proxima()` deixa a tela trocar sem esperar um evento (a partida terminou → resultado). Fechar a janela (`QUIT`) sai do loop em qualquer tela, e o `finally` sempre chama `fechar()` (que encerra as threads) e `pygame.quit()` (RC07).
- **Só esta thread** chama Pygame. Os cozinheiros nunca desenham nem leem eventos.
- A `TelaJogo` lê **um** `Retrato` por quadro (`jogo.retrato()`) e desenha tudo a partir dele (RC06).
- **Janela perde o foco** (`WINDOWFOCUSLOST`) → a `TelaJogo` pausa a partida. Arrastar a janela no Windows trava o loop, mas o relógio continua; sem isso, os clientes "somem" todos de uma vez ao soltar.
- A `TelaJogo` trata os eventos do jogo pela `entrada.traduzir` (spec 09). Até a 09 existir, trata só `P` (pausa) e `QUIT`.

## Telas

### Início

Nome do jogo, uma frase do objetivo, os controles (spec 09) e "Enter para começar · Esc para sair". Enter → cria `Jogo(config)`, `iniciar()`, vai para a TelaJogo.

### Jogo (tamanho em `layout.JANELA`, proposta 1280×720)

```
┌──────────────────────────────────────────────────────────────────────┐
│ ⏱ 2:41      Pontos 120 / 300 ████████░░░░        Perdidos ● ● ○ ○ ○  │  HUD
├──────────────────────────────────────────────────────────────────────┤
│ Pedidos:  [#7 Sopa ▓▓▓▓░ ②] [#8 Salada ▓▓░░░] [#9 Prato ▓▓▓▓▓]  ...  │  fila (3/6)
├──────────────────────────────────────────────────────────────────────┤
│  TÁBUA 1   TÁBUA 2    PIA      FOGÃO 1   FOGÃO 2    BALCÃO [■][ ]   │  estações
│    (1)                (3)        (2)                                 │
│                                  ④ ← fila de espera                  │
│                                                                      │
│  C1 cortando #7 ▓▓▓░░   C2 cozinhando #5 ▓░░░░   C3 lavando #8 ▓▓░░░  │  painel
│  C4 ESPERANDO FOGÃO há 2,3 s                                         │
└──────────────────────────────────────────────────────────────────────┘
```

- **Cozinheiros se movendo** (promessa do formulário): cada cozinheiro é um círculo da sua cor, com o número. O alvo dele vem do retrato: a estação que está usando, uma posição na fila de espera ao lado da estação que espera, ou a área de descanso quando LIVRE. `animacao.py` move a posição atual em direção ao alvo a uma velocidade fixa por segundo. Toda a animação é só da tela, a lógica não tem coordenadas.
- **Estação:** retângulo; cinza livre, cor do cozinheiro quando ocupada. O **balcão é um só**, com uma caixinha por vaga (`GrupoView.capacidade`).
- **ESPERANDO** em destaque (cor de alerta, nome da estação e há quanto tempo, de `esperando_ha`). Quem segura uma estação e espera outra mostra as duas (`segurando` + `esperando`): é o que aparece na demonstração de deadlock (RF18).
- **Pedido:** cartão com id, receita e barra de paciência (verde → amarelo → vermelho, RF08). Os da fila ficam numa linha; os em preparo, numa linha mais baixa logo abaixo, com a cor de quem está fazendo (o retrato traz até `tamanho_max_fila + n_cozinheiros` pedidos). Reservado, mostra o número do cozinheiro escolhido (②). A fila mostra `len/tamanho_max_fila`.
- **HUD:** tempo restante (mm:ss), pontos/meta com barra, "meta batida!" quando `meta_batida`, perdidos/limite como bolinhas. A meta aparece desde o primeiro quadro (RF02).
- **Pausa:** véu escuro com "PAUSADO — P para continuar".
- Partida terminou (`retrato.estado` é VITORIA ou DERROTA) → vai para a TelaResultado com o último retrato.

### Resultado (RF05)

VITÓRIA ou DERROTA, pontos/meta, pratos entregues, clientes perdidos (valores congelados, spec 06). "Enter para jogar de novo" (novo `Jogo`) e "Esc para sair do jogo".

## `__main__.py` e README

- `python -m cozinha` → `Config()`, `validar_para_jogo()`, `rodar(config)`.
- `python -m cozinha --demo-deadlock` → `Config.demo_deadlock()` (spec 09). Argumentos com `argparse`.
- O README do repositório ganha "Como jogar" (controles) e mantém "Como rodar" atualizado (RNF06).

## Regras

- Cores, tamanhos, posições e o tamanho da janela em `layout.py`, sem número solto nas funções de desenho.
- Funções de `desenho.py` recebem a superfície e uma View: sem estado, sem acesso ao `Jogo`.
- Uma fonte só (a padrão do Pygame), em 2 ou 3 tamanhos.
- Sprites são opcionais: formas primeiro. Se der tempo, trocar por sprites simples sem mudar a lógica.
- Para trabalhar antes da lógica existir: desenhar `Retrato.exemplo()` (spec 00).

## Fora do escopo

- Caminho com obstáculos, som, redimensionar a janela, temas.

## Critérios de aceite

- [x] `python -m cozinha` abre a tela de início; Enter começa; a partida termina sozinha na tela de resultado; Enter joga de novo; Esc sai.
- [x] Meta e tempo visíveis desde o primeiro quadro da partida.
- [x] Cada cozinheiro se move até a estação que usa ou espera, e volta ao descanso quando fica livre.
- [x] Toda estação ocupada mostra quem está nela; todo cozinheiro esperando aparece na fila de espera da estação certa.
- [x] O balcão aparece como uma estação com N vagas.
- [x] Barra de paciência muda de cor e o cartão some quando o cliente vai embora.
- [x] Fechar a janela no meio da partida encerra o processo em menos de 2 s. *(conferido numa janela real)*
- [x] Tirar o foco da janela pausa a partida. *(conferido numa janela real)*
- [x] **Desempenho (automático, `SDL_VIDEODRIVER=dummy`):** desenhar 600 quadros de um retrato com 4 cozinheiros e 6 pedidos leva menos de 10 s (≥ 60 FPS). O FPS real aparece no modo debug (spec 09).
- [x] Teste automático: desenhar `Retrato.exemplo()` não levanta exceção.
- [x] README tem "Como rodar" e "Como jogar" atualizados.
