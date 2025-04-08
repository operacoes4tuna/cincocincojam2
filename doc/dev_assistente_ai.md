# Plano de Implementação do Assistente IA - CincoCincoJAM 2.0

Para organizar a execução do projeto de chatbot integrado à plataforma Django 4 com PostgreSQL, as seguintes etapas foram planejadas. Este documento registra o progresso, detalhes de implementação e próximos passos.

## 1. Implementação do Widget de Chatbot com Funcionalidades Limitadas

**Status: ✅ Implementado**

**Objetivo:** Integrar e estilizar um widget de chat persistente no rodapé da plataforma.

**Implementação:**
- Criado widget de chat personalizado integrado ao layout da plataforma
- Desenvolvidos modelos de `ChatSession` e `Message` para persistência de dados
- Implementada interface de usuário responsiva que se adapta a diferentes dispositivos

**Recursos Utilizados:**
- Biblioteca Bootstrap para a estilização do widget
- Font Awesome para ícones e elementos visuais
- Django Templates para integração perfeita com o sistema existente

## 2. Integração com a OpenAI para Respostas Genéricas

**Status: ✅ Implementado**

**Objetivo:** Permitir que o chatbot responda de forma genérica às interações dos usuários utilizando a API da OpenAI.

**Implementação:**
- Criada classe `OpenAIManager` para gerenciar interações com a API da OpenAI
- Configuradas variáveis de ambiente para gerenciar chave de API e parâmetros do modelo
- Implementada formatação adequada do histórico de mensagens para obter contexto
- Adicionado suporte para utilizar diferentes modelos (atualmente usando gpt-4o-mini)

**Recursos Utilizados:**
- Biblioteca OpenAI para Python (`pip install openai`)
- Django Environ para gerenciar variáveis de ambiente sensíveis

**Configurações:**
```
OPENAI_API_KEY=sua_chave_api
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=150
OPENAI_TEMPERATURE=0.7
```

## 3. Integração com o Banco de Dados para Respostas Baseadas em Dados

**Status: ✅ Implementado**

**Objetivo:** Habilitar o chatbot a consultar o banco de dados PostgreSQL e fornecer respostas baseadas nas informações disponíveis.

**Implementação:**
- Desenvolvido módulo `DatabaseManager` para interagir com o banco de dados
- Implementadas consultas específicas para cursos, aulas e matrículas
- Adicionada lógica para verificar permissões de acesso a informações sensíveis
- Integrado com o `OpenAIManager` para processar comandos de banco de dados e humanizar as respostas

**Funcionalidades Implementadas:**
- Busca de informações sobre cursos específicos
- Lista de aulas disponíveis em um curso
- Verificação de matrículas de alunos
- Estatísticas gerais da plataforma

**Comandos Disponíveis:**
- `!DB:COURSE:id=X` ou `!DB:COURSE:slug=X` - Busca informações de um curso
- `!DB:SEARCH_COURSES:query=X` - Busca cursos por termo
- `!DB:LESSONS:course_id=X` - Lista aulas de um curso
- `!DB:ENROLLMENT:email=X:course_id=Y` - Verifica matrícula de um aluno
- `!DB:USER_ENROLLMENTS:email=X` - Lista matrículas de um aluno
- `!DB:STATS` - Obtém estatísticas da plataforma

## 4. Modelagem de Orientações para o Comportamento do Assistente

**Status: ✅ Implementado**

**Objetivo:** Permitir que as diretrizes sobre o comportamento do assistente sejam definidas através de uma interface amigável.

**Implementação:**
- Criado modelo `AssistantBehavior` para armazenar orientações do assistente
- Desenvolvida interface de configuração acessível a administradores e usuários normais
- Adicionado ícone de robô na barra de navegação para acesso rápido às configurações
- Implementada lógica para garantir que apenas um comportamento esteja ativo por vez

**Recursos da Interface:**
- Formulário para edição de orientações (apenas para administradores)
- Visualização do comportamento atual (para todos os usuários)
- Histórico de configurações anteriores
- Ativação/desativação de perfis de comportamento

**Acesso:**
- Ícone de robô na barra de navegação principal
- Opção "Assistente IA" no menu dropdown do usuário (para administradores)

## 5. Integração com o Sistema de Agendamentos de Estúdio

**Status: ✅ Implementado**

**Objetivo:** Permitir que o assistente consulte e processe informações sobre agendamentos de estúdio, incluindo listagem e cancelamento de sessões.

**Implementação:**
- Desenvolvido módulo `get_schedule_info()` para consultar agendamentos de estúdio
- Implementada função `cancel_studio_booking()` para processamento de cancelamentos
- Adicionados extratores de informação para reconhecer padrões em linguagem natural:
  - `extract_date_time()` - Reconhecimento de datas e horários
  - `extract_studio()` - Identificação de estúdios específicos
  - `extract_session_title()` - Extração de títulos de sessão
  - `extract_duration()` - Reconhecimento de duração mencionada

**Funcionalidades de Listagem:**
- Consulta de sessões agendadas por data (hoje, amanhã, datas específicas)
- Filtro por estúdio (Barra da Tijuca, Ipanema, Botafogo, etc.)
- Visualização de sessões por período (esta semana, próxima semana)
- Exibição de detalhes como horário, professor, participantes

**Funcionalidades de Cancelamento:**
- Cancelamento de sessões específicas por data/horário
- Cancelamento de todas as sessões do usuário
- Cancelamento seletivo por estúdio ou dia da semana
- Filtros combinados (sessões em um estúdio específico em determinada data)
- Reconhecimento de diferentes formas de expressar cancelamento (cancelar, desmarcar, remover, etc.)

**Detalhes Técnicos:**
- Implementação de filtros por sobreposição de horários (intervalos 14h-16h)
- Detecção de padrões específicos como "todas as sessões de estudio"
- Atualização de status para 'CANCELLED' no modelo Event
- Atualização de status para 'CANCELLED' nos EventParticipant associados
- **Documentação Técnica Detalhada:** [dev_cancelamento_sessoes.md](dev_cancelamento_sessoes.md)

**Exemplos de Comandos Reconhecidos:**
- "Quais são minhas sessões agendadas para hoje?"
- "Mostre meus agendamentos no estúdio da Barra"
- "Cancele todas as minhas sessões"
- "Desmarque a sessão do estúdio de 14h às 16h da Barra do dia 09/04"
- "Cancele meus agendamentos de sexta"

## 6. Integração com o WhatsApp para Interações Adicionais

**Status: ⏳ Pendente**

**Objetivo:** Permitir que o chatbot interaja com usuários também via WhatsApp, mantendo a capacidade de acessar informações específicas conforme o número de telefone associado.

**Recursos Sugeridos:**
- Twilio API para WhatsApp
- Biblioteca WhatsApp Business API

**Passos Planejados:**
- Configurar conta no Twilio e habilitar o sandbox para WhatsApp
- Utilizar biblioteca Twilio para Python para enviar e receber mensagens
- Desenvolver lógica para associar números de telefone a usuários no banco de dados
- Implementar sistema de verificação e autenticação via WhatsApp
- Adaptar o `OpenAIManager` para suportar interações via WhatsApp

## Cronograma de Execução Atualizado

- ✅ Semanas 1-2: Implementação do widget de chatbot na plataforma
- ✅ Semana 3: Integração com a API da OpenAI para respostas genéricas
- ✅ Semana 4: Desenvolvimento da integração com o banco de dados
- ✅ Semana 5: Implementação do sistema de orientações de comportamento
- ✅ Semana 6: Integração com o sistema de agendamentos de estúdio
- ⏳ Semanas 7-8: Implementação da integração com o WhatsApp e testes finais

## Próximos Passos

1. Melhorar a compreensão do contexto em conversas sobre agendamentos
2. Adicionar confirmação antes de realizar cancelamentos definitivos
3. Implementar funcionalidade para reagendar sessões existentes
4. Iniciar a implementação da integração com WhatsApp (Etapa 6)
5. Realizar testes abrangentes do sistema atual
6. Coletar feedback dos usuários sobre a experiência com o assistente
