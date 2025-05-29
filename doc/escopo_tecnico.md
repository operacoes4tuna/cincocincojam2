# Escopo Técnico do Projeto CincoCincoJAM 2.0

Este documento apresenta o escopo técnico para o projeto CincoCincoJAM 2.0, utilizando Django (Python) com PostgreSQL e hospedagem no Vercel. O foco é manter uma arquitetura simples e modular, implementada em ciclos de desenvolvimento incrementais, onde cada etapa entrega funcionalidades completas e utilizáveis.

⸻

## 1. Visão Geral da Arquitetura

### 1.1. Backend
- **Framework**: Django para gerenciar todo o core da aplicação (CRUD de cursos, usuários, transações, etc.)
- **Banco de Dados**: PostgreSQL 
- **Módulos Separados**:
  - Integração de Pagamentos
  - Emissão de Notas Fiscais
  - Assistente de IA (Chatbot)
  - Agenda e Integração com Google Calendar

### 1.2. Front-end
- **Fase 1**: Templates Django básicos (HTML + CSS mínimo + JavaScript essencial) para validação rápida
- **Fase 2**: Evolução gradativa do front-end (implementação de Bootstrap ou Tailwind CSS)
- **Fase 3** (opcional): Componentização com React/Vue para páginas específicas que necessitem maior interatividade

### 1.3. Hospedagem
- **Plataforma**: Vercel com suporte a Python via Serverless Functions ou contêiner Docker
- **Configuração**: Adaptadores WSGI para ASGI e build step customizado
- **Segurança**: Uso de variáveis de ambiente para todas as credenciais

### 1.4. Controle de Versão
- **Estratégia**: Monorepo no GitHub/GitLab contendo todo o projeto Django, requirements e scripts de deploy

⸻

## 2. Estrutura do Projeto Django

```
cinco_cinco_jam/
│
├── app/                # Aplicações Django (apps) específicos
│   ├── core/           # App principal, contém modelos de User, Profile, etc.
│   ├── courses/        # App para cursos, aulas, etc.
│   ├── payments/       # (Futuro) Integração de pagamento
│   ├── invoices/       # (Futuro) Emissão de notas
│   ├── chatbot/        # (Futuro) Integração com IA
│   └── schedule/       # (Futuro) Agenda e integração Google Calendar
│
├── cinco_cinco_jam/    # Pasta principal de configuração
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── templates/          # HTML + includes para cada app
├── static/             # Arquivos estáticos (CSS, JS, imagens)
├── doc/                # Documentação do projeto
├── manage.py
└── requirements.txt
```

Cada app Django concentra models, views, urls e demais arquivos relacionados ao seu domínio de responsabilidade, seguindo o princípio de separação de responsabilidades.

⸻

## 3. Ciclos de Desenvolvimento

### Ciclo 1 – Fundamentos e Cadastro

**Objetivo Principal**: Implementar o sistema básico de usuários e autenticação.

**Funcionalidades**:
1. **Cadastro de Usuário (Aluno/Professor/Administrador)**
   - Formulário de registro com nome, e-mail e senha
   - Login básico (usuário/senha)
2. **Gerenciamento de Usuários (Administrador)**
   - Listagem para visualizar, editar ou remover usuários
3. **Perfil do Usuário (Professor)**
   - Formulário para edição de informações essenciais
4. **Dashboard Inicial**
   - Painéis básicos personalizados por tipo de usuário

**Implementação Técnica**:
```python
# settings.py (configuração do PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nome_do_banco',
        'USER': 'usuario',
        'PASSWORD': 'senha',
        'HOST': 'host_postgres',
        'PORT': '5432',
    }
}

# Modelo de usuário personalizado
class User(AbstractUser):
    class Types(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrador')
        PROFESSOR = 'PROFESSOR', _('Professor')
        STUDENT = 'STUDENT', _('Aluno')
    
    user_type = models.CharField(max_length=10, choices=Types.choices, default=Types.STUDENT)
    email = models.EmailField(unique=True)
    # Outros campos personalizados
```

**Resultado Esperado**:
- Sistema funcional de cadastro e autenticação
- Administradores podem gerenciar usuários
- Bases estruturais do Django + PostgreSQL operantes

⸻

### Ciclo 2 – Curso e Conteúdo

**Objetivo Principal**: Permitir a criação e visualização de cursos e aulas.

**Funcionalidades**:
1. **Cadastro e Edição de Cursos (Professor)**
   - Nome do curso, valor, descrição curta
   - Status: rascunho ou publicado
2. **Cadastro e Edição de Aulas (Professor)**
   - Inclusão de aulas com título e URL de vídeo do YouTube
   - Status: rascunho ou publicado
3. **Página de Listagem de Cursos**
   - Filtros e busca de cursos publicados
4. **Página de Detalhes/Venda do Curso**
   - Informações completas e botão de compra (placeholder)

**Implementação Técnica**:
```python
# Models de Curso e Aula
class Course(models.Model):
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=[
        ('DRAFT', 'Rascunho'),
        ('PUBLISHED', 'Publicado')
    ], default='DRAFT')
    # Outros campos

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    youtube_id = models.CharField(max_length=30, blank=True)
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=[
        ('DRAFT', 'Rascunho'),
        ('PUBLISHED', 'Publicado')
    ], default='DRAFT')
    # Outros campos
```

**Resultado Esperado**:
- Professores podem criar e publicar cursos com aulas via links do YouTube
- Alunos podem visualizar cursos publicados
- Interface para compra de cursos (sem processamento de pagamento ainda)

⸻

### Ciclo 3 – Pagamentos e Financeiro

**Objetivo Principal**: Implementar o sistema de matrículas e pagamentos.

**Funcionalidades**:
1. **Integração com Pagamento**
   - Fluxo de checkout com gateway de pagamento
   - Retorno do status de pagamento
2. **Painel Financeiro do Professor**
   - Listagem de vendas, valores recebidos e pendentes
   - Lista de alunos matriculados com status de pagamento
3. **Histórico de Pagamentos do Aluno**
   - Visualização de cursos adquiridos e status
4. **Emissão de Notas Fiscais**
   - Configuração opcional no perfil do professor
   - Emissão de nota fiscal por venda

**Implementação Técnica**:
```python
# Model de Matrícula e Transação
class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=[
        ('ACTIVE', 'Ativa'),
        ('COMPLETED', 'Concluída'),
        ('CANCELLED', 'Cancelada')
    ], default='ACTIVE')
    # Métodos para calcular progresso, etc.

class PaymentTransaction(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pendente'),
        ('PAID', 'Pago'),
        ('REFUNDED', 'Estornado'),
        ('FAILED', 'Falhou')
    ])
    payment_date = models.DateTimeField(null=True, blank=True)
    gateway_transaction_id = models.CharField(max_length=100, blank=True)
    # Outros campos relacionados ao pagamento
```

**Integração com Gateway de Pagamento**:
- Escolher um gateway (Stripe, PagSeguro, Mercado Pago)
- Criar endpoints para iniciar pagamento e receber webhooks
- Atualizar status da matrícula com base no retorno do gateway

**Resultado Esperado**:
- Fluxo completo de compra com pagamento real
- Professores têm painel para acompanhar status financeiro
- Alunos podem gerenciar suas compras e solicitar estornos

⸻

### Ciclo 4 – Agenda e Integração Google

**Objetivo Principal**: Implementar sistema de agendamento com integração ao Google Calendar.

**Funcionalidades**:
1. **Agenda do Professor**
   - Criação de compromissos (data, hora, descrição, participantes)
2. **Integração com Google Calendar**
   - Sincronização automática de eventos
3. **Listagem de Agendas e Compromissos**
   - Visualização em formato de calendário ou lista

**Implementação Técnica**:
```python
# Model de Evento/Compromisso
class Event(models.Model):
    professor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    google_event_id = models.CharField(max_length=100, blank=True)
    # Relação com alunos participantes (ManyToMany)
    participants = models.ManyToManyField(User, related_name='participating_events', blank=True)
```

**Integração com Google Calendar API**:
- Autenticação OAuth2 para acesso à conta Google do professor
- Endpoints para criar, atualizar e excluir eventos sincronizados
- Webhook para receber atualizações do Google Calendar

**Resultado Esperado**:
- Professores podem gerenciar compromissos na plataforma
- Eventos são sincronizados automaticamente com Google Calendar
- Alunos podem ver aulas agendadas em seus painéis

⸻

### Ciclo 5 – Chatbot e IA

**Objetivo Principal**: Implementar assistente virtual para consultas via chat.

**Funcionalidades**:
1. **Chatbot com Linguagem Natural**
   - Interface para consultas sobre cursos, alunos, finanças e agenda
2. **Integração com WhatsApp**
   - Uso do WhatsApp para enviar consultas ao chatbot
3. **Treinamento e Melhoria de Respostas**
   - Ajustes para interpretar e responder corretamente às perguntas

**Implementação Técnica**:
```python
# Model para histórico de chat (opcional)
class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_history')
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, choices=[
        ('WEB', 'Web Interface'),
        ('WHATSAPP', 'WhatsApp')
    ])
```

**Integração com APIs de IA**:
- OpenAI API para processamento de linguagem natural
- Twilio ou WhatsApp Cloud API para integração com WhatsApp
- Endpoints para receber mensagens e responder com dados do sistema

**Resultado Esperado**:
- Professores podem consultar informações via chat na plataforma ou WhatsApp
- Sistema fornece respostas precisas baseadas nos dados do professor
- Experiência de usuário aprimorada com assistência automatizada

⸻

## 4. Detalhes de Implementação

### 4.1. Configuração do PostgreSQL

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'cinco_cinco_jam'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

### 4.2. Deploy no Vercel

**Configuração do vercel.json**:
```json
{
  "builds": [
    { "src": "manage.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "manage.py" }
  ],
  "env": {
    "DJANGO_SETTINGS_MODULE": "cinco_cinco_jam.settings"
  }
}
```

**Considerações para ambiente serverless**:
- Lidar com limitações de tempo de execução (cold starts)
- Garantir que o banco de dados seja acessível via internet
- Configurar variáveis de ambiente no painel do Vercel

**Alternativa com Docker**:
- Criar Dockerfile para o projeto
- Configurar build e deploy no Vercel ou em outro provedor que suporte contêineres

### 4.3. Boas Práticas de Banco de Dados

1. **Índices e Consultas**:
   - Definir índices para campos frequentemente pesquisados
   - Otimizar queries com select_related e prefetch_related

2. **Migrations**:
   - Manter migrations versionadas no repositório
   - Testar migrações em ambiente de staging antes de produção

3. **Backup e Segurança**:
   - Configurar backups automáticos do PostgreSQL
   - Nunca armazenar credenciais no código-fonte

⸻

## 5. Organização do Desenvolvimento

### 5.1. Princípios de Desenvolvimento

1. **MVP Funcional em Cada Etapa**
   - Cada ciclo deve resultar em uma versão utilizável do produto
   - Priorizar funcionalidades essenciais antes de refinamentos

2. **Front-End Progressivo**
   - Iniciar com HTML simples e funcional
   - Evoluir gradualmente para um design mais elaborado

3. **Testes Contínuos**
   - Implementar testes unitários e de integração desde o início
   - Validar cada ciclo com usuários reais antes de avançar

4. **Integração Contínua**
   - Automatizar testes e deploy em cada push
   - Manter ambiente de staging para validação

### 5.2. Jornadas de Usuário vs. Implementação Técnica

A implementação técnica seguirá as jornadas de usuário definidas no escopo de negócios:

| Jornada do Usuário | Ciclo de Desenvolvimento | Apps Django Envolvidos |
|--------------------|--------------------------|------------------------|
| Administrador (Básica) | Ciclo 1 | core/ |
| Professor (Básica) | Ciclo 2 | courses/ |
| Aluno (Básica) | Ciclo 2-3 | courses/, payments/ |
| Professor (Financeiro) | Ciclo 3 | payments/, invoices/ |
| Professor (Agenda) | Ciclo 4 | schedule/ |
| Professor (Chatbot) | Ciclo 5 | chatbot/ |

⸻

## 6. Referências e Recursos

### 6.1. Django e PostgreSQL
- [Documentação oficial do Django](https://docs.djangoproject.com/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [Documentação do PostgreSQL](https://www.postgresql.org/docs/)

### 6.2. Integrações
- [Stripe Python](https://stripe.com/docs/development/quickstart/python)
- [Mercado Pago Developers](https://developers.mercadopago.com/)
- [Google Calendar API](https://developers.google.com/calendar)
- [OpenAI API](https://platform.openai.com/docs)
- [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp)

### 6.3. Deploy
- [Vercel Python](https://vercel.com/docs/functions/runtimes/python)
- [Exemplo "django-vercel"](https://github.com/juancarlopolo/django-vercel)

⸻

## 7. Conclusão

Este escopo técnico apresenta um plano detalhado para o desenvolvimento do projeto CincoCincoJAM 2.0, combinando as necessidades de negócio com uma arquitetura técnica sólida e modular. 

A abordagem adotada prioriza:
- **Entregas incrementais** funcionais em cada ciclo
- **Arquitetura monolítica** mas modular, dividida em apps Django específicos
- **Simplicidade inicial** evoluindo para maior complexidade conforme necessário
- **Integrações externas** implementadas nos ciclos posteriores

Seguindo este roteiro, o projeto evoluirá de forma consistente, permitindo validação contínua com usuários reais e ajustes graduais baseados em feedback, garantindo que o produto final atenda plenamente às necessidades dos professores, alunos e administradores da plataforma.
