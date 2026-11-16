
# Respostas do formulário

O que o grupo respondeu no formulário da disciplina. É a fonte dos [Requisitos](requisitos.md). As perguntas 1 e 9 não vieram nos prints.

**2. Qual será o tema central do jogo?**
Faremos um jogo de restaurante em tempo real, em que o jogador comanda uma cozinha movimentada onde vários cozinheiros trabalham ao mesmo tempo. Os pedidos chegam sem parar e é preciso cortar, cozinhar, montar e entregar cada prato antes que os clientes percam a paciência. O desafio está no caos: os equipamentos são poucos, como fogões, tábuas de corte e balcão de entrega, e todo mundo quer usar ao mesmo tempo. Cabe ao jogador organizar a equipe, evitar os gargalos e manter a cozinha funcionando para conquistar a maior pontuação possível.

**3. Terminal ou interface gráfica?**
Interface gráfica (GUI) em Python com Pygame. Num jogo de cozinha em tempo real, o que torna a ideia fácil de entender é ver os cozinheiros se movendo, as estações ocupadas e os pedidos chegando; permite mostrar na apresentação quando alguém está esperando por um equipamento livre. Gráficos simples (formas e sprites básicos), para o foco ficar na concorrência e caber no prazo. Ferramentas: Python (módulo `threading`), Pygame, Claude e Codex como apoio no desenvolvimento e na revisão.

**4. Quantos personagens ou entidades principais?**
3 a 4 cozinheiros, clientes que chegam com pedidos ao longo da partida e 6 estações de trabalho (2 fogões, 2 tábuas de corte, 1 pia e 1 balcão de entrega). O principal obstáculo é a falta de equipamentos e o tempo limite dos pedidos.

**5. As entidades funcionarão de forma concorrente?**
Sim. Cada cozinheiro será uma thread independente, além de uma thread que gera os pedidos dos clientes e a thread principal da interface, que atualiza a tela. Todos rodam ao mesmo tempo e disputam as estações (fogões, tábuas, pia e balcão), cujo acesso é controlado por semáforos para que duas threads nunca usem o mesmo equipamento simultaneamente.

**6. Quais recursos serão compartilhados?**
As estações da cozinha: 2 fogões, 2 tábuas de corte, 1 pia e o balcão de entrega, que tem capacidade limitada. Além deles, a fila de pedidos e a pontuação do jogo também são usadas por todos os cozinheiros ao mesmo tempo.

**7. Qual será a principal mecânica?**
Atender o maior número de pedidos antes que os clientes percam a paciência. O jogador coordena os cozinheiros e disputa os equipamentos limitados da cozinha para entregar os pratos a tempo e somar pontos, em um ritmo que acelera ao longo da partida.

**8. Pontuação, tempo ou condição de vitória/derrota?**
Sim. Cada prato entregue a tempo soma pontos, com bônus para entregas rápidas. A partida tem tempo limitado (3 a 5 minutos) e cada cliente tem um cronômetro de paciência. Vence quem atingir a meta de pontos até o fim do tempo; perde quem deixar clientes demais irem embora ou não alcançar a meta.

**10. Desafio técnico com threads ou semáforos?**
Sim. Os principais desafios são o deadlock (dois cozinheiros esperando recursos um do outro), que resolveremos com uma ordem fixa de uso das estações; a condição de corrida na fila de pedidos e na pontuação, resolvida com semáforos binários; a inanição de threads, evitada com filas de espera justas; e a sincronização entre a interface e as threads, em que a tela lê uma cópia do estado do jogo sem bloquear os cozinheiros.
