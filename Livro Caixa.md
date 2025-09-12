Livro Caixa - Sistema de Gestão Financeira
Bem-vindo ao projeto Livro Caixa! Esta é uma aplicação web completa desenvolvida em Python com o micro-framework Flask, desenhada para o controlo financeiro pessoal ou de pequenas empresas.

Funcionalidades Principais
O sistema oferece uma gama completa de funcionalidades para uma gestão financeira eficaz:

Autenticação Segura: Sistema de login com utilizador e palavra-passe. As palavras-passe são armazenadas de forma segura utilizando hash.

Gestão de Utilizadores:

Um utilizador Administrador (admin) é criado por defeito.

O administrador pode criar, visualizar e apagar outros utilizadores.

Cada utilizador tem os seus próprios dados financeiros privados.

Recuperação de Palavra-passe: Funcionalidade de "Esqueceu a palavra-passe" que permite aos utilizadores redefinir a sua palavra-passe através do e-mail.

Dashboard Interativo:

Visão geral do Saldo Atual, Total de Entradas e Total de Saídas.

Gráficos dinâmicos para visualização de dados, incluindo despesas por categoria e fluxo de caixa mensal.

Gestão de Lançamentos:

Registo completo de contas a pagar e a receber.

Opção de editar e apagar lançamentos existentes.

Funcionalidade para marcar um lançamento como pago ou recebido.

Cadastros Flexíveis:

Criação de Categorias, Clientes e Fornecedores.

Novos utilizadores começam com uma lista de categorias padrão para facilitar o início.

Relatórios Financeiros:

Relatório de Entradas e Saídas por período.

Relatório Detalhado com todas as transações.

Opção de impressão formatada para os relatórios.

Backup da Base de Dados: Administradores podem descarregar um backup completo da base de dados com um único clique.

Tecnologias Utilizadas
Backend: Python 3

Framework Web: Flask

Base de Dados: SQLite 3

Frontend: HTML5, Tailwind CSS

Gráficos: Chart.js

Segurança: Werkzeug (para hashing de palavras-passe)

Como Configurar e Executar o Projeto
Siga estes passos para colocar a aplicação a funcionar no seu ambiente local.

Pré-requisitos
Python 3.6 ou superior instalado.

Estrutura de Ficheiros
Certifique-se de que o seu projeto está organizado com a seguinte estrutura de pastas e ficheiros:

/livrocaixa/
|-- app.py
|-- /templates/
|   |-- layout.html
|   |-- login.html
|   |-- forgot_password.html
|   |-- reset_password.html
|   |-- users.html
|   |-- index.html
|   |-- reports.html
|   |-- detailed_report.html
|   |-- schema.sql

Passos de Instalação
Crie um Ambiente Virtual (Recomendado):

python -m venv .venv

Ative o ambiente virtual:

No Windows: .\.venv\Scripts\activate

No macOS/Linux: source .venv/bin/activate

Instale as Dependências:
A única dependência externa é o Flask. Instale-o com o pip:

pip install Flask

Apague a Base de Dados Antiga (se existir):
Se já tiver um ficheiro livro_caixa.db na sua pasta, apague-o para garantir que a estrutura mais recente seja criada.

Execute a Aplicação:
No seu terminal, a partir da pasta principal do projeto (/livrocaixa/), execute o seguinte comando:

python app.py

Na primeira vez que executar, o programa irá automaticamente:

Criar o ficheiro da base de dados livro_caixa.db.

Criar as tabelas necessárias a partir do ficheiro schema.sql.

Criar o utilizador administrador padrão.

Aceda à Aplicação:
Abra o seu navegador e aceda a:
http://127.0.0.1:5000

Credenciais Padrão
Utilizador: admin

Palavra-passe: admin

Próximos Passos e Melhorias
Implementar a edição e exclusão dos itens de cadastro (Categorias, Clientes, etc.).

Adicionar paginação à tabela de lançamentos para melhor desempenho com grandes volumes de dados.

Criar mais tipos de relatórios, como fluxo de caixa projetado.

Migrar de SQLite para uma base de dados mais robusta como PostgreSQL para um ambiente de produção.
