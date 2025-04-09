# CincoCincoJAM 2.0

Plataforma completa para gestão de cursos online, possibilitando a interação entre administradores, professores e alunos em um ambiente educacional digital integrado.

## Visão Geral

CincoCincoJAM 2.0 é uma plataforma LMS (Learning Management System) desenvolvida em Django para a criação, gestão e distribuição de conteúdo educacional online. O sistema permite a administração completa de cursos, matrículas de alunos e acompanhamento de progresso, com interfaces personalizadas para cada tipo de usuário.

## Stack Tecnológica

### Backend
- **Python 3.12**: Linguagem de programação principal
- **Django 4.2.10**: Framework web para desenvolvimento rápido e limpo
- **SQLite** (desenvolvimento) / **PostgreSQL** (produção): Sistemas de banco de dados

### Frontend
- **Bootstrap 5**: Framework CSS para design responsivo
- **Font Awesome 6**: Biblioteca de ícones vetoriais
- **JavaScript**: Para interatividade no lado do cliente
- **Crispy Forms + Bootstrap5**: Para renderização de formulários elegantes

### Ferramentas & Bibliotecas
- **python-decouple**: Gerenciamento de configurações e variáveis de ambiente
- **Pillow**: Processamento de imagens para upload de perfil e cursos
- **Django TemplateView**: Sistema de templates para renderização das páginas

## Funcionalidades Principais

### Sistema de Usuários
- Três tipos de perfis: Administrador, Professor e Aluno
- Autenticação via email como identificador principal
- Sistema de redirecionamento inteligente após login baseado no tipo de usuário
- Gerenciamento de perfis com informações personalizadas

### Assistente IA
- Chatbot inteligente integrado com a API da OpenAI
- Interface de chat acessível em todas as páginas da plataforma
- Consultas contextuais ao banco de dados para responder perguntas sobre cursos e matrículas
- Personalização do comportamento do assistente através de interface amigável.
- Acesso rápido às configurações do assistente via ícone na barra de navegação.
- Diferentes permissões de visualização e edição para administradores e usuários comuns.

### Área do Administrador
- Dashboard com estatísticas gerais do sistema
- Gerenciamento completo de usuários (CRUD)
- Visão geral de cursos e matrículas
- Relatórios de atividades

### Área do Professor
- Dashboard com estatísticas dos seus cursos
- Criação e edição de cursos com múltiplas aulas
- Sistema de ordenação de aulas via drag-and-drop
- Gestão de publicação de cursos
- Monitoramento de alunos matriculados

### Área do Aluno
- Catálogo de cursos disponíveis com sistema de busca e filtros
- Dashboard personalizado com cursos matriculados
- Interface de aprendizado com progresso das aulas
- Sistema para marcar aulas como concluídas
- Acompanhamento de progresso em tempo real

## Estrutura do Projeto

O projeto está organizado em quatro aplicações principais:

- **core**: Gerencia o modelo de usuário personalizado e funcionalidades centrais
- **users**: Implementa a área administrativa e gerenciamento de usuários
- **courses**: Contém toda a lógica de cursos, aulas, matrículas e progresso
- **assistant**: Implementa o Assistente IA com integração à OpenAI e consultas contextuais ao banco de dados

## Instalação e Configuração

### Requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Ambiente virtual (recomendado)
- Chave de API da OpenAI (para o Assistente IA)

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone <url-do-repositorio>
   cd cincocincojam2
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure o arquivo `.env` na raiz do projeto:**
   ```
   DEBUG=True
   SECRET_KEY=sua-chave-secreta-aqui
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   # Configurações do Assistente IA
   OPENAI_API_KEY=sua-chave-api-openai
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_MAX_TOKENS=150
   OPENAI_TEMPERATURE=0.7
   ```

5. **Execute as migrações:**
   ```bash
   python manage.py migrate
   ```

6. **Crie os usuários padrão:**
   ```bash
   python manage.py create_default_users
   ```

7. **Inicie o servidor de desenvolvimento:**
   ```bash
   python3 manage.py runserver
   ```
   
   Alternativamente, use o script de inicialização que gerencia automaticamente a porta:
   ```bash
   ./start_server.sh
   ```
   Este script verifica se há algum processo usando a porta 8000 e o encerra antes de iniciar o servidor.

8. **Acesse a aplicação:**
   Abra o navegador e acesse `http://127.0.0.1:8000/`

## Usuários de Demonstração

Para facilitar os testes, o sistema vem pré-configurado com três usuários padrão:

| Tipo | Email | Senha |
|------|-------|-------|
| Aluno | aluno@example.com | aluno123 |
| Professor | professor@example.com | prof123 |
| Admin | admin@example.com | admin123 |

Utilize os botões de login rápido na página de login para acessar facilmente cada tipo de usuário.

## Navegação no Sistema

### Fluxo do Administrador
1. Login → Redirecionado para Dashboard Administrativo
2. Acesso a gerenciamento de usuários
3. Consulta de estatísticas gerais

### Fluxo do Professor
1. Login → Redirecionado para Dashboard do Professor
2. Criação/Edição de cursos
3. Adição e ordenação de aulas
4. Publicação do curso

### Fluxo do Aluno
1. Login → Redirecionado para Catálogo de Cursos
2. Exploração de cursos disponíveis
3. Matrícula em cursos
4. Acesso ao conteúdo e marcação de progresso

## Modelos de Dados Principais

- **User**: Modelo personalizado com tipos (ADMIN, PROFESSOR, STUDENT)
- **Course**: Cursos com título, descrição, professor, status
- **Lesson**: Aulas associadas a cursos, com ordem e conteúdo
- **Enrollment**: Matrícula de alunos em cursos com status e progresso
- **LessonProgress**: Rastreamento de progresso em aulas específicas
- **ChatSession**: Sessões de chat com histórico de interações do usuário com o assistente
- **Message**: Mensagens trocadas entre usuários e o assistente
- **AssistantBehavior**: Configurações de comportamento do assistente IA

## Deploy em Produção

Para ambiente de produção, recomenda-se:

1. Configurar `DEBUG=False` no arquivo `.env`
2. Migrar para PostgreSQL definindo as configurações no `.env`
3. Configurar um servidor web como Nginx ou Apache
4. Utilizar Gunicorn como servidor WSGI
5. Configurar HTTPS com certificado SSL

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.

## Contribuição

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie sua branch de feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

TESTE: teste
