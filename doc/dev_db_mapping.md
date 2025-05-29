# Mapeamento do Banco de Dados - CincoCincoJAM

Este documento contém o mapeamento completo da estrutura do banco de dados da plataforma CincoCincoJAM, organizado por aplicações Django.

## Índice

- [Aplicação Core](#aplicação-core)
- [Aplicação Courses](#aplicação-courses)
- [Aplicação Payments](#aplicação-payments)
- [Aplicação Assistant](#aplicação-assistant)
- [Diagrama de Relacionamentos](#diagrama-de-relacionamentos)

## Aplicação Core

### Modelo `User`

Modelo de usuário personalizado que estende o `AbstractUser` do Django, com email como identificador principal.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|------------|
| `id` | `AutoField` | Chave primária | Primary Key, Auto-increment |
| `email` | `EmailField` | Endereço de e-mail | Unique |
| `username` | `CharField` | Nome de usuário | Unique, max_length=150 |
| `user_type` | `CharField` | Tipo de usuário | choices=['ADMIN', 'PROFESSOR', 'STUDENT'], default='STUDENT', max_length=10 |
| `bio` | `TextField` | Biografia do usuário | Opcional, blank=True |
| `profile_image` | `ImageField` | Imagem de perfil | Opcional, blank=True, null=True, upload_to='profile_images/' |
| `date_joined` | `DateTimeField` | Data de cadastro | auto_now_add=True |
| `is_staff` | `BooleanField` | Acesso ao admin | Herdado de AbstractUser |
| `is_active` | `BooleanField` | Usuário ativo | Herdado de AbstractUser |
| `is_superuser` | `BooleanField` | Permissões totais | Herdado de AbstractUser |
| `first_name` | `CharField` | Nome | Herdado de AbstractUser, max_length=150 |
| `last_name` | `CharField` | Sobrenome | Herdado de AbstractUser, max_length=150 |

**Propriedades**:
- `is_admin` - Verifica se o usuário é administrador
- `is_professor` - Verifica se o usuário é professor
- `is_student` - Verifica se o usuário é aluno

## Aplicação Courses

### Modelo `Course`

Representa um curso oferecido por um professor na plataforma.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|------------|
| `id` | `AutoField` | Chave primária | Primary Key, Auto-increment |
| `professor` | `ForeignKey` | Professor que criou o curso | FK → User, on_delete=CASCADE, limit_choices_to={'user_type': 'PROFESSOR'} |
| `title` | `CharField` | Título do curso | max_length=200 |
| `slug` | `SlugField` | Slug para URL amigável | max_length=200, unique=True, blank=True (auto-gerado) |
| `short_description` | `CharField` | Descrição curta | max_length=200, blank=True |
| `description` | `TextField` | Descrição detalhada | blank=True |
| `price` | `DecimalField` | Preço do curso | max_digits=10, decimal_places=2, default=0 |
| `status` | `CharField` | Status do curso | choices=['DRAFT', 'PUBLISHED', 'ARCHIVED'], default='DRAFT', max_length=10 |
| `image` | `ImageField` | Imagem de capa | blank=True, null=True, upload_to='course_images/' |
| `created_at` | `DateTimeField` | Data de criação | auto_now_add=True |
| `updated_at` | `DateTimeField` | Data de atualização | auto_now=True |

**Propriedades**:
- `is_published` - Verifica se o curso está publicado
- `is_draft` - Verifica se o curso está em rascunho
- `is_archived` - Verifica se o curso está arquivado

**Métodos**:
- `get_total_lessons()` - Número total de aulas
- `publish()` - Publica o curso
- `archive()` - Arquiva o curso
- `get_enrolled_students_count()` - Número de alunos matriculados

### Modelo `Lesson`

Representa uma aula dentro de um curso.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|------------|
| `id` | `AutoField` | Chave primária | Primary Key, Auto-increment |
| `course` | `ForeignKey` | Curso à qual a aula pertence | FK → Course, on_delete=CASCADE |
| `title` | `CharField` | Título da aula | max_length=200 |
| `description` | `TextField` | Descrição da aula | blank=True |
| `video_url` | `URLField` | URL do vídeo da aula | blank=True |
| `youtube_id` | `CharField` | ID do vídeo no YouTube | max_length=30, blank=True (auto-detectado se possível) |
| `order` | `PositiveIntegerField` | Ordem da aula no curso | default=0 |
| `status` | `CharField` | Status da aula | choices=['DRAFT', 'PUBLISHED'], default='DRAFT', max_length=10 |
| `created_at` | `DateTimeField` | Data de criação | auto_now_add=True |
| `updated_at` | `DateTimeField` | Data de atualização | auto_now=True |

**Meta**:
- `unique_together = [['course', 'order']]` - Garante ordem única dentro do curso

**Propriedades**:
- `is_published` - Verifica se a aula está publicada
- `is_draft` - Verifica se a aula está em rascunho

### Modelo `Enrollment`

Representa a matrícula de um aluno em um curso.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|------------|
| `id` | `AutoField` | Chave primária | Primary Key, Auto-increment |
| `student` | `ForeignKey` | Aluno matriculado | FK → User, on_delete=CASCADE |
| `course` | `ForeignKey` | Curso em que o aluno está matriculado | FK → Course, on_delete=CASCADE |
| `status` | `CharField` | Status da matrícula | choices=['ACTIVE', 'COMPLETED', 'CANCELLED'], default='ACTIVE', max_length=10 |
| `enrolled_at` | `DateTimeField` | Data da matrícula | auto_now_add=True |
| `completed_at` | `DateTimeField` | Data de conclusão | null=True, blank=True |
| `last_accessed_at` | `DateTimeField` | Último acesso | auto_now=True |

**Propriedades**:
- `is_active` - Verifica se a matrícula está ativa
- `is_completed` - Verifica se o curso foi concluído
- `is_cancelled` - Verifica se a matrícula foi cancelada

**Métodos**:
- `complete()` - Marca o curso como concluído
- `cancel()` - Cancela a matrícula
- `get_progress()` - Obtém o progresso do aluno no curso
- `get_completed_lessons_count()` - Obtém o número de aulas concluídas

### Modelo `LessonProgress`

Rastreia o progresso de um aluno em uma aula específica.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|------------|
| `id` | `AutoField` | Chave primária | Primary Key, Auto-increment |
| `enrollment` | `ForeignKey` | Matrícula relacionada | FK → Enrollment, on_delete=CASCADE |
| `lesson` | `ForeignKey` | Aula relacionada | FK → Lesson, on_delete=CASCADE |
| `is_completed` | `BooleanField` | Se a aula foi concluída | default=False |
| `completed_at` | `DateTimeField` | Data de conclusão | null=True, blank=True |
| `last_accessed_at` | `DateTimeField` | Último acesso | auto_now=True |

**Meta**:
- `unique_together = ['enrollment', 'lesson']` - Garante registro único por matrícula/aula
- `ordering = ['lesson__order']` - Ordena pelo campo 'order' da aula

**Métodos**:
- `complete()` - Marca a aula como concluída

## Aplicação Payments

### Modelo `PaymentTransaction`

Representa transações de pagamento dos alunos matriculados em cursos.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|------------|
| `id` | `AutoField` | Chave primária | Primary Key, Auto-increment |
| `enrollment` | `ForeignKey` | Matrícula relacionada ao pagamento | FK → Enrollment, on_delete=CASCADE |
| `amount` | `DecimalField` | Valor do pagamento | max_digits=10, decimal_places=2 |
| `status` | `CharField` | Status do pagamento | choices=['PENDING', 'PAID', 'REFUNDED', 'FAILED'], default='PENDING', max_length=20 |
| `payment_date` | `DateTimeField` | Data de pagamento efetivo | null=True, blank=True |
| `payment_method` | `CharField` | Método de pagamento utilizado | max_length=50, blank=True |
| `transaction_id` | `CharField` | ID da transação (do gateway) | max_length=100, blank=True |
| `created_at` | `DateTimeField` | Data de criação | auto_now_add=True |
| `updated_at` | `DateTimeField` | Data de atualização | auto_now=True |

**Métodos**:
- `mark_as_paid()` - Marca a transação como paga e registra a data
- `refund()` - Marca a transação como estornada

## Aplicação Assistant

### Modelo `ChatSession`

Armazena informações sobre sessões de chat com o assistente.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|------------|
| `id` | `AutoField` | Chave primária | Primary Key, Auto-increment |
| `user` | `ForeignKey` | Usuário associado à sessão | FK → User, on_delete=CASCADE, null=True, blank=True |
| `session_id` | `CharField` | ID único da sessão | max_length=100, unique=True |
| `created_at` | `DateTimeField` | Data de criação | auto_now_add=True |
| `updated_at` | `DateTimeField` | Data de atualização | auto_now=True |
| `is_active` | `BooleanField` | Se a sessão está ativa | default=True |

### Modelo `Message`

Armazena mensagens de chat entre usuários e o assistente.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|------------|
| `id` | `AutoField` | Chave primária | Primary Key, Auto-increment |
| `chat_session` | `ForeignKey` | Sessão de chat relacionada | FK → ChatSession, on_delete=CASCADE |
| `sender` | `CharField` | Remetente da mensagem | choices=['user', 'bot'], max_length=10 |
| `content` | `TextField` | Conteúdo da mensagem | - |
| `timestamp` | `DateTimeField` | Data e hora da mensagem | auto_now_add=True |

**Meta**:
- `ordering = ['timestamp']` - Ordena mensagens por data/hora

### Modelo `AssistantBehavior`

Armazena orientações de comportamento do assistente virtual.

| Campo | Tipo | Descrição | Constraints |
|-------|------|-----------|------------|
| `id` | `AutoField` | Chave primária | Primary Key, Auto-increment |
| `name` | `CharField` | Nome do perfil de comportamento | max_length=100 |
| `is_active` | `BooleanField` | Se o comportamento está ativo | default=True |
| `system_prompt` | `TextField` | Instruções de comportamento | - |
| `created_at` | `DateTimeField` | Data de criação | auto_now_add=True |
| `updated_at` | `DateTimeField` | Data de atualização | auto_now=True |
| `created_by` | `ForeignKey` | Usuário que criou | FK → User, on_delete=SET_NULL, null=True, blank=True |

**Meta**:
- `ordering = ['-is_active', 'name']` - Ordena por status e nome

**Métodos**:
- `get_active_behavior()` (classmethod) - Retorna o comportamento ativo atual

## Diagrama de Relacionamentos

```
User (core.User)
  |
  |---- 1:N ----> Course (courses.Course)
  |               |
  |               |---- 1:N ----> Lesson (courses.Lesson)
  |               |
  |               |---- 1:N ----> Enrollment (courses.Enrollment)
  |                               |
  |                               |---- 1:N ----> LessonProgress (courses.LessonProgress)
  |                               |
  |                               |---- 1:N ----> PaymentTransaction (payments.PaymentTransaction)
  |
  |---- 1:N ----> Enrollment (courses.Enrollment)
  |
  |---- 1:N ----> ChatSession (assistant.ChatSession)
  |               |
  |               |---- 1:N ----> Message (assistant.Message)
  |
  |---- 1:N ----> AssistantBehavior (assistant.AssistantBehavior)
```

## Notas Técnicas

1. **Autenticação e Autorização**:
   - O sistema utiliza o modelo de usuário personalizado (`core.User`) com tipos específicos (ADMIN, PROFESSOR, STUDENT)
   - Cada tipo de usuário tem permissões específicas para suas funcionalidades

2. **Fluxo de Matrículas e Pagamentos**:
   - Quando um aluno se matricula em um curso, é criado um registro em `Enrollment`
   - Para cada matrícula, pode haver uma transação de pagamento em `PaymentTransaction`
   - O progresso em cada aula é registrado em `LessonProgress`

3. **Assistente Virtual**:
   - O comportamento do assistente é configurável através de `AssistantBehavior`
   - As conversas são organizadas em `ChatSession` com várias `Message`
   - Apenas um `AssistantBehavior` pode estar ativo por vez
