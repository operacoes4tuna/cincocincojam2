# Implementação do Sistema de Cobrança - 55Jam

Este documento descreve a implementação do sistema de cobrança da plataforma 55Jam, que consiste em duas funcionalidades principais: o botão "Emitir Cobrança" para professores e o aviso de pagamento pendente para alunos.

## 1. Visão Geral

A implementação consiste em:

1. **Botão "Emitir Cobrança"** - Permite que professores emitam novas cobranças para transações pendentes na lista de movimentações financeiras.
2. **Aviso de Pagamento Pendente** - Um alerta no dashboard do aluno informando sobre cobranças pendentes, com um link direto para realizar o pagamento.

## 2. Arquivos Implementados/Modificados

### 2.1. Emissão de Cobrança (Professor)
- `payments/views.py` - Adição da função `emit_payment_charge` para processar a emissão de nova cobrança.
- `payments/urls.py` - Adição da URL para a funcionalidade de emissão de cobrança.
- `templates/payments/professor/transaction_list.html` - Adição do botão "Emitir Cobrança" e feedback visual.

### 2.2. Aviso de Pagamento Pendente (Aluno)
- `courses/student_views.py` - Modificação da view `StudentDashboardView` para verificar pagamentos pendentes.
- `templates/courses/student/dashboard.html` - Adição do alerta de cobrança pendente.

## 3. Detalhes da Implementação

### 3.1. Emissão de Cobrança (Professor)

#### 3.1.1. Nova View

A função `emit_payment_charge` em `payments/views.py` implementa a lógica para emitir uma nova cobrança:

```python
@login_required
def emit_payment_charge(request, transaction_id):
    """
    Emite uma cobrança para uma transação pendente, enviando um lembrete de pagamento
    e fornecendo um novo link de pagamento PIX.
    """
    # Obter a transação, garantindo que pertence a um curso do professor atual
    transaction = get_object_or_404(
        PaymentTransaction, 
        id=transaction_id, 
        status=PaymentTransaction.Status.PENDING,
        enrollment__course__professor=request.user
    )
    
    enrollment = transaction.enrollment
    
    try:
        # Criar uma nova cobrança PIX usando o OpenPix
        openpix = OpenPixService()
        charge_data = openpix.create_charge(enrollment)
        
        # Atualizar os dados da transação existente
        transaction.correlation_id = charge_data.get('correlationID')
        transaction.brcode = charge_data.get('brCode')
        transaction.qrcode_image = charge_data.get('qrCodeImage')
        transaction.updated_at = timezone.now()
        transaction.save()
        
        # Enviar um e-mail de cobrança para o aluno (implementação futura)
        
        messages.success(request, f'Cobrança emitida com sucesso para {enrollment.student.email}.')
        
        # Redirecionar para a página de detalhes da transação com um parâmetro para indicar o sucesso
        return redirect(reverse('payments:professor_transactions') + f'?emitted={transaction.id}')
        
    except Exception as e:
        messages.error(request, f'Erro ao emitir cobrança: {str(e)}')
        return redirect('payments:professor_transactions')
```

#### 3.1.2. Interface para Professores

O botão "Emitir Cobrança" foi adicionado na listagem de transações para professores:

```html
<td class="text-end">
    {% if transaction.status == 'PENDING' %}
    <a href="{% url 'payments:emit_payment_charge' transaction.id %}" class="btn btn-sm btn-warning">
        <i class="fas fa-paper-plane me-1"></i> Emitir Cobrança
    </a>
    {% endif %}
</td>
```

### 3.2. Aviso de Pagamento Pendente (Aluno)

#### 3.2.1. Modificação da View do Dashboard do Aluno

A classe `StudentDashboardView` em `courses/student_views.py` foi modificada para buscar transações pendentes:

```python
# Verificar se há cobranças pendentes
try:
    from payments.models import PaymentTransaction
    
    # Buscar transações pendentes
    pending_transactions = PaymentTransaction.objects.filter(
        enrollment__student=self.request.user,
        status=PaymentTransaction.Status.PENDING
    ).select_related('enrollment', 'enrollment__course').order_by('-created_at')
    
    context['pending_transactions'] = pending_transactions
    context['has_pending_payment'] = pending_transactions.exists()
    
    # Se tiver apenas uma transação pendente, facilitar o acesso direto
    if pending_transactions.count() == 1:
        context['single_pending_transaction'] = pending_transactions.first()
except (ImportError, Exception) as e:
    # Se o módulo payments não estiver disponível ou ocorrer outro erro
    print(f"Erro ao buscar transações pendentes: {e}")
    context['has_pending_payment'] = False
```

#### 3.2.2. Alerta Visual no Dashboard do Aluno

Um alerta foi adicionado ao dashboard do aluno para mostrar cobranças pendentes:

```html
{% if has_pending_payment %}
<!-- Alerta de cobrança pendente -->
<div class="alert alert-warning alert-dismissible fade show mb-4" role="alert">
    <div class="d-flex align-items-center">
        <div class="flex-shrink-0">
            <i class="fas fa-exclamation-triangle fa-2x me-3"></i>
        </div>
        <div class="flex-grow-1 ms-3">
            <h4 class="alert-heading">Você possui pagamento(s) pendente(s)</h4>
            <p class="mb-0">
                {% if pending_transactions.count == 1 %}
                    Existe uma cobrança pendente para o curso <strong>{{ single_pending_transaction.enrollment.course.title }}</strong> 
                    no valor de <strong>R$ {{ single_pending_transaction.amount|floatformat:2 }}</strong>.
                {% else %}
                    Existem {{ pending_transactions.count }} cobranças pendentes no total de 
                    <strong>R$ {{ pending_transactions.amount__sum|floatformat:2 }}</strong>.
                {% endif %}
            </p>
            <hr>
            <div class="mt-2">
                {% if pending_transactions.count == 1 and single_pending_transaction.payment_method == 'PIX' %}
                    <a href="{% url 'payments:pix_payment_detail' single_pending_transaction.id %}" class="btn btn-warning">
                        <i class="fas fa-qrcode me-1"></i> Visualizar Pagamento PIX
                    </a>
                {% else %}
                    <a href="{% url 'payments:student_payments' %}" class="btn btn-warning">
                        <i class="fas fa-dollar-sign me-1"></i> Saiba Mais
                    </a>
                {% endif %}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
            </div>
        </div>
    </div>
</div>
{% endif %}
```

## 4. Fluxo de Utilização

### 4.1. Fluxo do Professor
1. O professor acessa a lista de transações financeiras.
2. Para transações com status "Pendente", o botão "Emitir Cobrança" é exibido.
3. Ao clicar no botão:
   - Uma nova cobrança PIX é gerada utilizando o serviço OpenPix.
   - Os dados da transação são atualizados com as novas informações de pagamento.
   - O professor é redirecionado de volta à lista de transações com uma notificação de sucesso.
   - A linha da transação que teve a cobrança emitida é destacada visualmente.

### 4.2. Fluxo do Aluno
1. O aluno acessa seu dashboard.
2. Se possuir pagamentos pendentes, um alerta é exibido no topo da página.
3. O alerta informa detalhes da cobrança pendente:
   - Se for apenas uma cobrança, informa o curso e o valor
   - Se forem várias cobranças, informa a quantidade e o valor total
4. O aluno pode clicar em:
   - "Visualizar Pagamento PIX" (caso seja uma única cobrança via PIX)
   - "Saiba Mais" (caso tenha múltiplas cobranças)
5. O aluno é direcionado para realizar o pagamento ou visualizar os detalhes da cobrança.

## 5. Benefícios da Implementação

### 5.1. Para Professores
- Facilidade em realizar cobranças recorrentes
- Aumento na taxa de conversão de matrículas pendentes para pagas
- Controle eficiente de pagamentos pendentes

### 5.2. Para Alunos
- Visibilidade clara de cobranças pendentes
- Acesso rápido e direto para realizar pagamentos
- Experiência de usuário aprimorada com avisos relevantes

## 6. Considerações Técnicas

### 6.1. Segurança
- Verificações de permissão garantem que professores só podem emitir cobranças para seus próprios cursos
- Alunos só visualizam suas próprias cobranças pendentes

### 6.2. UX/UI
- Feedback visual adequado para ambos os tipos de usuário
- Botões e alertas bem posicionados e com cores apropriadas
- Tratamento diferenciado para casos de cobrança única vs. múltiplas cobranças

### 6.3. Performance
- Consultas otimizadas com `select_related` para reduzir o número de queries
- Tratamento de exceções para prevenir erros em produção

## 7. Extensões Futuras

- Implementação do envio de e-mail ao emitir cobrança
- Sistema de notificações push para alunos
- Painel de histórico de cobranças emitidas para professores
- Opção para personalizar a mensagem de cobrança

---

**Importante**: Este sistema de cobrança aprimora significativamente a gestão financeira da plataforma 55Jam, melhorando tanto a experiência do professor quanto a do aluno no que diz respeito a pagamentos pendentes. 