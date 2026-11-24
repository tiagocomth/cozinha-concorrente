# Polimento da UI e dificuldade — Design (curto)

**Data:** 2026-11-24 · **Status:** aprovado pelo usuário na conversa

## Por quê
O jogo ficou bom de jogar, mas fácil demais e com a UI ainda crua. O usuário quer mais desafio e uma UI "um pouquinho mais trabalhada e polida", sem mudar a cara do jogo.

## Abordagens
1. **Polir o que existe + níveis de dificuldade (escolhida).** Efeitos, ícones, animações leves e três níveis com números diferentes.
2. Trocar o visual por sprites/arte externa — fora do escopo (o design anterior proíbe arquivos de imagem; o foco é concorrência).
3. Só subir os números — resolve o desafio, não a UI.

## O que muda
**Dificuldade** (escolhida na tela de início com ←/→):

| | Fácil | Normal (padrão) | Difícil |
| --- | --- | --- | --- |
| Meta | 200 | 300 | 400 |
| Paciência das receitas | ×1,0 | ×0,75 | ×0,6 |
| Intervalo entre pedidos (início → fim) | 8 → 3 s | 6 → 2 s | 5 → 1,5 s |
| Pedido só do jogador (`atraso_automaticos`) | 6 s | 4 s | 2 s |

- Pratos progressivos (`receitas_progressivas`): no início, mais receitas curtas; perto do fim, mais longas (peso pela quantidade de etapas). Desligado fora do single player — testes atuais não mudam.

**Polimento**
- Efeitos: "+N" subindo do balcão a cada entrega e pontos do HUD pulsando; "✗" vermelho onde estava a comanda de um cliente que desistiu.
- Chefs balançam ao andar; vapor saindo do fogão aceso; barras arredondadas com brilho; comanda treme com paciência no vermelho.
- Ícones desenhados por etapa (faca, gota, chama, prato) no lugar das letras; HUD com ícones de relógio, estrela e cliente.
- Fonte arredondada do sistema com fallback para a padrão; sombras suaves nos móveis.
- Fade entre telas; contagem "3, 2, 1, Já!" antes da partida (as threads só sobem no "Já!").
- Sem som.

## Restrições
- Tudo desenhado com `pygame.draw` (sem arquivos); só a thread principal desenha; `Config()` e a demo de deadlock não mudam.
- Efeitos são só da tela, deduzidos comparando um `Retrato` com o anterior (a lógica não ganha eventos novos).

## Deixado ao construtor
Paleta, tempos e tamanhos exatos de cada efeito; forma exata dos ícones.
