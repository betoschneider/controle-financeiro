# Nova funcionalidade

## Carteira de Investimentos
- Quero salvar no banco de dados o preço de compra de cada ativo.
- Ao confirmar aporte, é necessário gravar em uma tabela de transações o preço de compra e a quantidade de cada ativo.
- Quero adicionar abaixo do valor total do patrimônio, na mesma métrica 'Patrimônio Total', o percentual de rendimento da carteira.
  - Memória de cálculo:
    - O percentual de rendimento é calculado com base na diferença entre o valor atual e o valor de compra.
    - $$C_{total} = (n \cdot x) + (m \cdot y)$$, onde $C_{total}$ é o valor total do patrimônio, $n$ e $m$ são as quantidades de ativos, e $x$ e $y$ são os preços de compra.
    - $$V_{atual} = (n + m) \cdot z$$, onde $V_{atual}$ é o valor atual do patrimônio, $n$ e $m$ são as quantidades de ativos, e $z$ é o preço atual.
    - $$R_{\%2} = \left( \frac{V_{atual}}{C_{total}} - 1 \right) \cdot 100$$, onde $R_{\%2}$ é o percentual de rendimento.
  - Se o rendimento for positivo, exibir em verde; se for negativo, exibir em vermelho.
- Se o ativo não tiver valor de compra, gravar o valor da primeira consulta de preço.
- Na página 'Gerenciar Carteira', quero adicionar uma tabela que exiba o percentual de rendimento de cada ativo.
  - A tabela deve conter as colunas: 'Ativo', 'Quantidade', 'Preço de Compra (média)', 'Preço Atual', 'Rendimento (%)'.
