# 🍔 Big Mac World Ranking

Um ranking coletivo dos Big Macs pelo mundo, construído a partir de experiências reais de quem os comeu.

O projeto nasceu de um hábito: visitar o McDonald's durante viagens, pedir um Big Mac e comparar com os anteriores. Aqui, essa curiosidade vira um registro aberto, com critérios comuns e contribuições da comunidade. Todas as avaliações têm o mesmo peso, inclusive as de quem criou o projeto.

## O que avaliamos

Cada avaliação representa **um Big Mac consumido em uma loja, em determinada data**. Uma experiência em uma filial não representa, sozinha, um país inteiro.

A comparação principal considera o **Big Mac com a receita padrão local, sem personalizações**. Diferenças entre as receitas locais fazem parte da experiência; versões especiais e pedidos personalizados podem ser relatados, mas ficam fora da média principal.

## Critérios

Dê uma nota inteira de **1 a 5** para cada critério e justifique brevemente o que observou.

| Critério | O que observar |
| --- | --- |
| Sabor e equilíbrio | Carne, molho, queijo e vegetais combinam bem? Há excesso ou falta de algum ingrediente? |
| Textura | O pão está macio, a alface crocante e a carne sem estar seca ou borrachuda? |
| Temperatura | O sanduíche chegou na temperatura esperada para comer? |
| Frescor percebido | Pão e vegetais parecem frescos? Há sinais de que o sanduíche ficou esperando pronto? Avalie apenas sua percepção, sem presumir condições da cozinha. |
| Montagem | Os ingredientes estão bem distribuídos, em proporções adequadas, e o sanduíche é fácil de comer? |

Use a mesma escala em todos os critérios:

| Nota | Referência |
| --- | --- |
| 1 | Muito ruim: problemas marcantes que prejudicam bastante a experiência. |
| 2 | Abaixo do esperado: problemas perceptíveis que prejudicam a experiência. |
| 3 | Bom/padrão: atende ao esperado para um Big Mac. |
| 4 | Muito bom: se destaca positivamente no critério. |
| 5 | Excepcional: uma experiência de destaque, com uma justificativa concreta. |

**Preço, atendimento e ambiente não entram na nota do sanduíche.** Você pode registrá-los como contexto, separadamente.

## Como calcular o ranking

A nota de cada avaliação é a média simples dos cinco critérios:

`Nota final = (sabor + textura + temperatura + frescor + montagem) / 5`

Exemplo: notas 4, 3, 4, 3 e 5 resultam em **3,8/5**.

O ranking coletivo de uma loja, cidade ou país usa a média das notas finais das avaliações elegíveis daquele local. Cada avaliação aceita tem o mesmo peso. Calculamos com os valores sem arredondar e exibimos duas casas decimais; médias exatas iguais ficam empatadas.

Toda média publicada deve acompanhar o **número de avaliações e de pessoas que contribuíram**, além do período das visitas. Uma média baseada em uma única visita ainda é uma amostra inicial, e deve ser interpretada assim.

Consumo no salão, retirada e delivery são aceitos, desde que identificados. Ao comparar resultados, mantenha essa informação visível: transporte e tempo até o consumo podem afetar a experiência.

## Como contribuir

1. Abra um pull request usando o [template de contribuição](.github/pull_request_template.md).
2. Use o título `Avaliação: cidade, país — AAAA-MM-DD`.
3. Preencha uma avaliação por PR, incluindo todos os campos obrigatórios e as cinco notas com justificativas.
4. Aguarde a revisão. Podemos pedir informações que faltaram ou esclarecer a aplicação dos critérios antes de aceitar a contribuição.

**Nesta fase, as avaliações ficam registradas no corpo dos PRs aceitos e mesclados.** Não é necessário criar um arquivo de dados para contribuir; abra o PR com uma pequena alteração no repositório, como adicionar uma linha à lista abaixo, e preencha o template no corpo do PR. O ranking consolidado ainda não é gerado automaticamente.

### Índice de avaliações

Ao contribuir, acrescente aqui uma linha no formato `- Cidade, país — data da visita — @usuario`. O PR associado à alteração contém a avaliação completa.

<!-- Adicione as avaliações abaixo desta linha. -->

### Informações obrigatórias

- Seu usuário do GitHub, como identificação pública da pessoa que avaliou.
- País, cidade e identificação da loja (endereço ou link do mapa que permita distingui-la).
- Data da visita, no formato `AAAA-MM-DD`.
- Modalidade: salão, retirada ou delivery.
- Confirmação da receita padrão local ou descrição das alterações/versão especial.
- As cinco notas e suas justificativas, para entrar no ranking principal.
- Um comentário geral sobre a experiência.

Fotos são opcionais. Se incluir uma, use uma foto sua ou que tenha permissão para compartilhar e evite expor outras pessoas. Preço e moeda local também são opcionais; indique se o valor é do sanduíche avulso ou do combo.

### Regras para manter a comparação útil

- Avalie apenas o que você consumiu pessoalmente. Não envie notas em nome de outras pessoas.
- Registre uma avaliação por pessoa e por visita. Não divida o mesmo sanduíche em várias contribuições suas nem duplique avaliações.
- Novas visitas à mesma loja são bem-vindas: registre a data de cada uma.
- Baseie as notas na experiência observada e justifique-as. Discordar de uma avaliação não é motivo para rejeitá-la.
- A revisão verifica completude, coerência com os critérios e duplicações; não exige concordância com seu gosto.
- Para corrigir uma avaliação aceita, abra um PR indicando o PR original e o que mudou. A correção substitui a avaliação anterior e não conta como uma nova visita.
- Mantenha os comentários respeitosos e focados na experiência.

### Avaliações de memória

Histórias antigas também são bem-vindas, mesmo sem data exata ou lembrança suficiente para dar notas detalhadas. Marque a contribuição como **relato de memória**, informe apenas o que lembra e deixe as incertezas explícitas.

Esses relatos ficam registrados, mas **não entram nas médias do ranking**. Não invente datas ou notas para completar o formulário.

## Independência

Este é um projeto independente da comunidade, sem afiliação com o McDonald's. Big Mac e McDonald's são marcas de seus respectivos titulares.
