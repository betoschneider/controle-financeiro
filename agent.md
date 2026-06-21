# Melhorias sugeridas

- exigir que o nome de usuário seja um e-mail válido no cadastro e login.

- criei um usuário novo e já carregou com um valor de despesa. como se é um novo usuário, deveria começar sem nenhum lançamento.

- tentei importar um csv e deu erro:
Falha na importação: Valor inválido na linha 20: 

o arquivo que eu tentei importar:
Data,Item,Tipo,Categoria,Valor,Pago
01/01/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,True
01/02/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,True
01/03/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,True
01/04/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,True
01/05/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,True
01/06/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,793.36,False
01/07/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,False
01/08/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,False
01/09/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,False
01/10/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,False
01/11/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,False
01/12/2026,Empréstimo Suelen Nubank,Receita,Outras Receitas,0.0,False
01/01/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,532.0,True
01/02/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,532.0,True
01/03/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,532.0,True
01/04/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,532.0,True
01/05/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,532.0,True
01/06/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,532.0,False
01/07/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,,False
01/08/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,,False
01/09/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,213.0,True
01/10/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,,False
01/11/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,,False
01/12/2026,Empréstimo Suelen Clio,Receita,Outras Receitas,,False

se não te ver valor ou for null, substituir por 0.0 (zero). Se esse for o problema.
