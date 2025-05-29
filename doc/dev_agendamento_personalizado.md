# Sistema de Agendamento com Horários Personalizados

## Visão Geral

O sistema de agendamento da plataforma 55Jam agora permite que professores agendem aulas e eventos com horários personalizados, além dos slots pré-definidos de 1 hora. Esta funcionalidade proporciona maior flexibilidade ao professor, permitindo a criação de eventos com duração variável de acordo com a necessidade, sem a obrigatoriedade de seguir um padrão fixo de duração.

![Visão geral do calendário](../static/img/docs/calendario_visao_geral.png)

## Funcionalidades Principais

- **Seleção de horário personalizado**: Os professores podem definir horários de início e término personalizados
- **Limite de 3 horas**: Eventos não podem ter duração superior a 3 horas
- **Verificação de disponibilidade em tempo real**: O sistema verifica se o horário escolhido está disponível
- **Integração com o calendário**: Visualização clara dos horários disponíveis e ocupados
- **Fluxo simplificado**: Agendamento direto sem redirecionamentos desnecessários
- **Validações de segurança**: Tanto no frontend quanto no backend

## Como Utilizar

### Passo 1: Acessar o Calendário

1. Faça login como professor
2. Acesse o menu "Agenda"
3. Selecione o estúdio onde deseja realizar o agendamento

![Seleção de estúdio](../static/img/docs/selecao_estudio.png)

### Passo 2: Selecionar a Data

1. No calendário, clique na data desejada
2. Um modal será aberto com as opções de agendamento

![Seleção de data no calendário](../static/img/docs/selecao_data.png)

### Passo 3: Escolher Entre Horários Fixos e Personalizados

1. Por padrão, o sistema mostra os slots disponíveis de 1 hora
2. Para usar um horário personalizado, ative a chave "Horário Personalizado" no topo do modal

![Alternância para horário personalizado](../static/img/docs/toggle_horario_personalizado.png)

### Passo 4: Definir o Horário Personalizado

1. Insira o horário de início desejado
2. Insira o horário de término desejado
3. Clique em "Aplicar Horário"
4. O sistema verificará se o horário está disponível e se está dentro do limite de 3 horas
5. Se disponível, uma confirmação aparecerá e você poderá prosseguir com o agendamento

![Configuração de horário personalizado](../static/img/docs/configuracao_horario.png)

### Passo 5: Preencher os Detalhes do Evento

1. Defina um título para o evento (ou use o título padrão)
2. Selecione o tipo de evento (aula regular, workshop, etc.)
3. Opcionalmente, selecione um curso associado ao evento
4. Se um curso for selecionado, você poderá escolher quais alunos participarão

![Detalhes do evento](../static/img/docs/detalhes_evento.png)

### Passo 6: Confirmar o Agendamento

1. Clique em "Confirmar Agendamento"
2. O evento será criado e você será redirecionado de volta ao calendário
3. Uma mensagem de sucesso será exibida

![Confirmação de agendamento](../static/img/docs/confirmacao_agendamento.png)

## Regras e Limitações

- **Horário de funcionamento**: Os agendamentos só podem ser feitos dentro do horário de funcionamento dos estúdios (geralmente 8h às 20h em dias úteis, 9h às 16h aos sábados)
- **Duração máxima**: Nenhum evento pode ter duração superior a 3 horas
- **Verificação de conflitos**: O sistema não permite agendamentos que se sobreponham a eventos já existentes
- **Período de agendamento**: É possível agendar com até 3 meses de antecedência
- **Datas passadas**: Não é possível agendar em datas passadas

## Mensagens de Erro

O sistema exibe mensagens claras quando um agendamento não pode ser realizado:

- **Duração excedida**: "A duração máxima permitida é de 3 horas."
- **Horário fora do período de funcionamento**: "O horário selecionado está fora do horário de funcionamento."
- **Conflito com outro evento**: "Este horário não está disponível pois conflita com outro agendamento."
- **Data passada**: "Não é possível agendar para datas passadas."
- **Antecedência muito grande**: "Não é possível agendar com mais de 3 meses de antecedência."

![Exemplo de mensagem de erro](../static/img/docs/mensagem_erro.png)

## Detalhes Técnicos

### Frontend

A interface de usuário para o agendamento personalizado é implementada em HTML, CSS e JavaScript, utilizando o framework Bootstrap para elementos visuais. As principais características técnicas incluem:

- **Validação em tempo real**: JavaScript valida a duração e verifica conflitos antes do envio
- **Chamadas AJAX**: Interação com o backend para verificar disponibilidade sem recarregar a página
- **Feedback visual**: Mensagens claras sobre limitações e conflitos
- **Responsividade**: Interface adaptável a diferentes dispositivos

### Backend

O backend é implementado em Django, com os seguintes componentes principais:

- **API de verificação de disponibilidade**: Endpoint que verifica se um horário personalizado está disponível
- **Validações de segurança**: Verificações redundantes no servidor para garantir o cumprimento das regras
- **Modelo de dados**: Utiliza o modelo `Event` para armazenar os agendamentos, com campos `start_time` e `end_time` para definir o período
- **View dedicada**: `EventCreateView` com lógica específica para processar horários personalizados

### Arquivos Principais

- `scheduler/templates/scheduler/calendar.html`: Template com a interface do usuário e lógica JavaScript
- `scheduler/views.py`: Contém a API de verificação de disponibilidade e lógica de criação de eventos
- `scheduler/models.py`: Define o modelo de dados para eventos e participantes

## Fluxo de Dados

1. O usuário seleciona uma data e ativa a opção de horário personalizado
2. Ao definir início e fim, o frontend faz uma chamada AJAX para a API de verificação de disponibilidade
3. A API verifica se o horário está dentro dos limites e se não há conflitos
4. Se disponível, o frontend permite a continuação do agendamento
5. Ao confirmar, os dados são enviados para a view `EventCreateView`
6. A view valida novamente os dados, cria o evento e associa participantes se necessário
7. O usuário é redirecionado de volta para o calendário com uma mensagem de sucesso

## Exemplos de Código

### Verificação de Duração no Frontend (JavaScript)

```javascript
function validateCustomTimeRange() {
    const startTime = customStartTime.value;
    const endTime = customEndTime.value;
    
    if (!startTime || !endTime) return;
    
    const start = new Date(`2000-01-01T${startTime}`);
    const end = new Date(`2000-01-01T${endTime}`);
    
    // Calcular duração em minutos
    const durationMs = end - start;
    const durationMinutes = durationMs / (1000 * 60);
    
    // Verificar se a duração é maior que 3 horas (180 minutos)
    if (durationMinutes > 180) {
        durationWarning.style.display = 'block';
        applyCustomTimeBtn.disabled = true;
    } else {
        durationWarning.style.display = 'none';
        applyCustomTimeBtn.disabled = false;
    }
}
```

### Verificação de Disponibilidade no Backend (Python)

```python
# Verificar duração (máximo 3 horas)
duration_minutes = (slot_end - slot_start).total_seconds() / 60

if duration_minutes > 180:  # 3 horas = 180 minutos
    return JsonResponse({
        'error': 'Duração máxima permitida é de 3 horas',
        'available': False
    }, status=400)

# Verificar conflitos com outros eventos
for event in existing_events:
    if (slot_start < event.end_time and slot_end > event.start_time):
        is_available = False
        conflicting_event = {
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat()
        }
        break
```

## Melhorias Futuras

- Implementação de opção para eventos recorrentes com horários personalizados
- Possibilidade de definir horários padrão personalizados para facilitar agendamentos frequentes
- Notificações automáticas para alunos quando um evento é agendado
- Estatísticas de uso dos horários mais populares
- Integração com sistemas de calendário externos (Google Calendar, Outlook)

## Suporte

Para questões, problemas ou sugestões relacionadas ao sistema de agendamento personalizado, entre em contato com o suporte técnico da plataforma através do email suporte@55jam.com.br ou pelo WhatsApp (21) 99999-9999.

---

*Documentação criada em Abril de 2025. Última atualização: Abril de 2025.* 