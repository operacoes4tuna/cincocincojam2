# Funcionalidade de Cancelamento de Sessões - Assistente IA

Este documento descreve a implementação da funcionalidade de cancelamento de sessões de estúdio através do assistente virtual da 55JAM. A funcionalidade permite que usuários cancelem sessões específicas ou múltiplas sessões usando linguagem natural.

## Visão Geral

A funcionalidade de cancelamento de sessões é parte do módulo de assistente IA integrado ao sistema de agendamentos da plataforma. Ela permite que usuários cancelem sessões usando comandos em linguagem natural como "cancele todas as minhas sessões" ou "desmarque minha sessão de 14h no estúdio da Barra".

## Arquitetura da Solução

### Componentes Principais

1. **OpenAIManager** - Responsável por detectar solicitações de cancelamento na entrada do usuário
2. **cancel_studio_booking()** - Função principal para processamento de cancelamentos
3. **Extratores de informação** - Funções auxiliares para extrair informações específicas de consultas
4. **Função de filtragem** - Lógica para filtrar eventos baseada em critérios extraídos

### Fluxo da Solicitação

1. O usuário envia uma solicitação de cancelamento pelo chat
2. O `OpenAIManager` identifica a intenção de cancelamento
3. A solicitação é encaminhada para a função `cancel_studio_booking()`
4. A função extrai informações relevantes (data, hora, estúdio)
5. Uma consulta é construída para buscar os eventos correspondentes
6. Os eventos encontrados são atualizados para status "CANCELLED"
7. Uma resposta de confirmação é retornada ao usuário

## Implementação Detalhada

### 1. Detecção de Solicitações de Cancelamento

No arquivo `openai_manager.py`, adicionamos a detecção de palavras-chave e padrões específicos para identificar solicitações de cancelamento:

```python
# Palavras-chave para cancelamento de sessões
cancel_keywords = [
    'cancelar', 'cancele', 'cancelamento', 'desmarcar', 'desmarque', 
    'remover', 'remova', 'deletar', 'delete', 'anular', 'anule', 
    'tirar', 'excluir', 'exclua', 'não quero mais', 'suspender'
]

# Verificar se a consulta está relacionada a cancelamentos
is_cancel_query = any(keyword in user_message for keyword in cancel_keywords)

# Verificar combinações específicas que sempre devem ser tratadas como cancelamento
cancel_patterns = [
    'cancel todas', 'cancelar todas', 'cancele todas', 
    'desmarcar todas', 'desmarque todas',
    'cancel meus', 'cancelar meus', 'cancele meus',
    'cancel minhas', 'cancelar minhas', 'cancele minhas',
    'desmarcar meus', 'desmarque meus',
    'desmarcar minhas', 'desmarque minhas',
    'remov todas', 'remover todas', 'remova todas',
    'excluir todas', 'exclua todas'
]
is_cancel_all_query = any(pattern in user_message for pattern in cancel_patterns)
```

A lógica de encaminhamento prioriza solicitações de cancelamento sobre outros tipos de consultas:

```python
# Processar solicitações de cancelamento com máxima prioridade
if is_cancel_all_query or (is_cancel_query and is_schedule_query):
    logger.info("Solicitação de cancelamento de sessão detectada")
    from .db_query import cancel_studio_booking
    return cancel_studio_booking(user_message)
```

### 2. Processamento de Cancelamentos

A função `cancel_studio_booking()` no arquivo `db_query.py` é o núcleo da funcionalidade:

```python
def cancel_studio_booking(query):
    """
    Processa uma solicitação de cancelamento de sessões de estúdio.
    Permite cancelar sessões específicas ou múltiplas sessões com base em critérios como data, horário ou local.
    """
    try:
        from scheduler.models import Event, EventParticipant
        from django.db.models import Q
        from datetime import datetime, timedelta, date
        from django.utils import timezone
        import re
        
        # Verificar se a consulta realmente é sobre cancelamento
        query_lower = query.lower()
        is_cancel_query = any(word in query_lower for word in cancel_words)
        
        if not is_cancel_query:
            return {
                "response_type": "text",
                "content": "Não entendi se você deseja cancelar uma sessão."
            }
        
        # Extrair informações da consulta
        date_time_info = extract_date_time(query)
        studio_info = extract_studio(query)
        
        # Extrair horários específicos mencionados na consulta
        start_hour, end_hour = extract_time_range(query)
        
        # Verificar menção a "todas as sessões"
        all_sessions = check_all_sessions_patterns(query_lower)
        
        # Construir a consulta base
        base_query = build_base_query(current_user)
        
        # Adicionar filtros específicos
        if not all_sessions:
            base_query = add_date_filters(base_query, date_time_info)
            base_query = add_time_filters(base_query, start_hour, end_hour)
            base_query = add_weekday_filters(base_query, mentioned_weekday)
        
        # Adicionar filtro por estúdio, se especificado
        if studio_info:
            studio, studio_id = studio_info
            base_query &= Q(location=studio)
        
        # Buscar os eventos que correspondem aos critérios
        events_to_cancel = Event.objects.filter(base_query).order_by('start_time')
        
        # Cancelar os eventos
        for event in events_to_cancel:
            event.status = 'CANCELLED'
            event.save()
            
            # Também atualizar o status dos participantes
            EventParticipant.objects.filter(event=event).update(attendance_status='CANCELLED')
        
        # Preparar resposta de sucesso
        return format_success_response(events_to_cancel)
        
    except Exception as e:
        return {
            "response_type": "text",
            "content": f"Ocorreu um erro ao processar sua solicitação: {str(e)}"
        }
```

### 3. Extração de Informações

Para processar a linguagem natural, desenvolvemos vários extratores de informação:

#### Extração de Horários

```python
# Padrão para horários como "14h às 16h" ou "14:00 às 16:00"
time_range_pattern = r'(\d{1,2})(?:h|:00|:\d{2})?\s*(?:às|as|a|até|ate|-)?\s*(\d{1,2})(?:h|:00|:\d{2})?'
time_range_match = re.search(time_range_pattern, query_lower)

# Padrão para horário único como "14h" ou "14:00"
single_time_pattern = r'(\d{1,2})(?:h|:00|:\d{2})'
single_time_match = re.search(single_time_pattern, query_lower)

if time_range_match:
    # Se encontrou um intervalo de horários
    start_hour = int(time_range_match.group(1))
    end_hour = int(time_range_match.group(2))
elif single_time_match:
    # Se encontrou apenas um horário específico
    specific_hour = int(single_time_match.group(1))
    start_hour = specific_hour
    end_hour = start_hour + 2  # Assumir duração padrão de 2 horas
```

#### Filtros por Sobreposição de Horários

```python
# Eventos que começam dentro do intervalo especificado
hour_query = Q(start_time__hour__gte=start_hour, start_time__hour__lt=end_hour)
# Eventos que terminam dentro do intervalo especificado
hour_query |= Q(end_time__hour__gt=start_hour, end_time__hour__lte=end_hour)
# Eventos que englobam completamente o intervalo especificado
hour_query |= Q(start_time__hour__lte=start_hour, end_time__hour__gte=end_hour)
```

#### Detecção de "Todas as Sessões"

```python
# Verificar padrões específicos que indicam cancelamento de todas as sessões
all_sessions_patterns = [
    'todas as sessões', 'todos os agendamentos', 'todas as aulas',
    'desmarque todas', 'cancele todas', 'remova todas',
    'meus agendamentos', 'minhas sessões'
]

# Verificação específica para o padrão problemático
if 'todas as sessões de estudio' in query_lower or 'todas as sessões do estudio' in query_lower:
    all_sessions = True
```

## Testes e Validação

Foram implementados scripts de teste para validar a funcionalidade:

1. **test_cancel_booking.py**: Testes básicos para validar a função
2. **test_cancel_booking_fixed.py**: Testes específicos para casos problemáticos
3. **test_specific_cancellations.py**: Testes para cenários específicos (por estúdio, por hora)
4. **test_barra_14h_session.py**: Teste para um caso específico problemático

Exemplos de solicitações testadas com sucesso:

```
"cancele todas as minhas sessões"
"desmarque todas as sessões de estudio para mim"
"desmarque a sessão do studio de 14h às 16h da barra do dia 09/04"
"cancele meus agendamentos de sexta"
"remover todos os meus agendamentos do estúdio da barra"
"cancelar a aula do estúdio da barra na quarta às 17h"
```

## Desafios e Soluções

### Problema 1: Reconhecimento de "todas as sessões"

**Desafio**: O sistema não identificava corretamente solicitações para cancelar todas as sessões.

**Solução**: Implementamos a detecção específica de padrões e variações linguísticas comuns:

```python
all_sessions_terms = ['todas', 'todos', 'tudo', 'qualquer', 'meus agendamentos', 'minhas sessões']
all_sessions = any(term in query_lower for term in all_sessions_terms)

# Verificação específica para o padrão "todas as sessões de estudio"
if 'todas as sessões de estudio' in query_lower:
    all_sessions = True
```

### Problema 2: Reconhecimento de Horários

**Desafio**: Extrair corretamente horários mencionados em diferentes formatos (14h, 14:00, etc.).

**Solução**: Implementamos expressões regulares mais refinadas:

```python
time_range_pattern = r'(\d{1,2})(?:h|:00|:\d{2})?\s*(?:às|as|a|até|ate|-)?\s*(\d{1,2})(?:h|:00|:\d{2})?'
```

### Problema 3: Filtros por Sobreposição de Horários

**Desafio**: Identificar eventos que se sobrepõem a um intervalo de horário mencionado.

**Solução**: Implementamos uma lógica de filtro que considera três casos de sobreposição:

```python
# Eventos que começam dentro do intervalo
hour_query = Q(start_time__hour__gte=start_hour, start_time__hour__lt=end_hour)
# Eventos que terminam dentro do intervalo
hour_query |= Q(end_time__hour__gt=start_hour, end_time__hour__lte=end_hour)
# Eventos que englobam completamente o intervalo
hour_query |= Q(start_time__hour__lte=start_hour, end_time__hour__gte=end_hour)
```

## Melhorias Futuras

1. **Confirmação Antes de Cancelar**: Implementar um fluxo de confirmação antes de cancelar sessões
2. **Reagendamento**: Adicionar a capacidade de reagendar sessões canceladas
3. **Cancelamento Seletivo**: Permitir cancelar apenas algumas sessões de uma lista
4. **Cancelamento com Justificativa**: Incluir a opção de fornecer justificativa para o cancelamento
5. **Notificações**: Enviar notificações automáticas para os participantes afetados

## Conclusão

A funcionalidade de cancelamento de sessões amplia significativamente as capacidades do assistente virtual, permitindo que os usuários gerenciem seus agendamentos de forma mais natural e intuitiva. A implementação robusta e flexível permite reconhecer uma ampla variedade de solicitações em linguagem natural, proporcionando uma experiência de usuário mais fluida e eficiente. 