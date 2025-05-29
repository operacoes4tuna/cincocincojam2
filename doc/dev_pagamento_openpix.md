# Documentação Técnica: Integração com OpenPix para Pagamentos PIX

## 1. Visão Geral

O sistema de pagamentos da plataforma 5Cinco5 JAM foi implementado utilizando a API da **OpenPix**, permitindo o recebimento de pagamentos via PIX para matrículas em cursos. Esta implementação permite que os alunos se inscrevam em cursos pagos e realizem o pagamento de forma rápida, prática e segura utilizando o método PIX.

### 1.1 Recursos Principais:

- Geração automática de QR Codes PIX
- Interface amigável para copiar o código PIX
- Verificação automática do status do pagamento
- Webhook para confirmação instantânea de pagamentos
- Atualização automática do status da matrícula após confirmação
- Modo de simulação para ambiente de desenvolvimento

### 1.2 Componentes da Integração:

```
┌─────────────────┐       ┌─────────────────┐      ┌─────────────────┐
│                 │       │                 │      │                 │
│  5Cinco5 JAM    │◄─────►│  OpenPix API    │◄────►│  Rede Bancária  │
│  Plataforma     │       │  (Gateway PIX)  │      │                 │
│                 │       │                 │      │                 │
└─────────────────┘       └─────────────────┘      └─────────────────┘
```

## 2. Fluxo de Funcionamento

### 2.1 Fluxo do Usuário

1. Aluno seleciona um curso pago e clica em "Matricular-se"
2. Sistema cria matrícula com status "PENDING" 
3. Aluno é redirecionado para a página de pagamento PIX
4. O QR Code e o código PIX são exibidos para o aluno
5. Aluno realiza o pagamento usando seu aplicativo bancário
6. Sistema recebe a confirmação do pagamento via webhook da OpenPix
7. Status da matrícula é atualizado para "ACTIVE"
8. Aluno ganha acesso ao conteúdo do curso

### 2.2 Diagrama de Sequência

```
┌─────┐          ┌─────────┐          ┌───────┐          ┌───────┐
│Aluno│          │Plataforma│          │OpenPix│          │Banco  │
└──┬──┘          └────┬────┘          └───┬───┘          └───┬───┘
   │   Matrícula      │                   │                  │
   │─────────────────►│                   │                  │
   │                  │                   │                  │
   │                  │ Criar cobrança    │                  │
   │                  │──────────────────►│                  │
   │                  │                   │                  │
   │                  │ QR Code + Código  │                  │
   │                  │◄──────────────────│                  │
   │                  │                   │                  │
   │   Tela de        │                   │                  │
   │◄─────────────────│                   │                  │
   │   pagamento      │                   │                  │
   │                  │                   │                  │
   │   Escaneia QR    │                   │                  │
   │────────────────────────────────────────────────────────►│
   │                  │                   │                  │
   │                  │                   │ Notifica        │
   │                  │                   │◄─────────────────│
   │                  │                   │                  │
   │                  │Webhook (pagamento)│                  │
   │                  │◄──────────────────│                  │
   │                  │                   │                  │
   │ Acesso liberado  │                   │                  │
   │◄─────────────────│                   │                  │
   │                  │                   │                  │
```

## 3. Implementação Técnica

### 3.1 Estrutura de Arquivos

```
payments/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── openpix_service.py    # Serviço para comunicação com a API OpenPix
├── pix_views.py          # Views para pagamentos PIX
├── urls.py
└── templates/
    └── payments/
        └── pix_payment_detail.html  # Template da página de pagamento
```

### 3.2 Modelos de Dados

#### 3.2.1 Enrollment (Matrícula)

```python
class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Ativa')
        COMPLETED = 'COMPLETED', _('Concluída')
        CANCELLED = 'CANCELLED', _('Cancelada')
        PENDING = 'PENDING', _('Pendente')
    
    # Relacionamentos
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    
    # Campos
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    # outros campos...
```

#### 3.2.2 PaymentTransaction (Transação de Pagamento)

```python
class PaymentTransaction(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pendente')
        PAID = 'PAID', _('Pago')
        REFUNDED = 'REFUNDED', _('Estornado')
        FAILED = 'FAILED', _('Falhou')
    
    # Relacionamentos
    enrollment = models.ForeignKey('courses.Enrollment', on_delete=models.CASCADE, related_name='payments')
    
    # Campos gerais
    amount = models.DecimalField(_('valor'), max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Campos específicos para PIX
    correlation_id = models.CharField(max_length=255, blank=True)
    brcode = models.TextField(blank=True, null=True)
    qrcode_image = models.URLField(blank=True, null=True)
    
    # Campos de controle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 3.3 Serviço OpenPix

O arquivo `openpix_service.py` implementa a comunicação com a API da OpenPix:

```python
class OpenPixService:
    """
    Serviço para integração com a API do OpenPix para pagamentos via Pix.
    """
    # Ambiente de desenvolvimento vs produção
    BASE_URL = "https://api.sandbox.openpix.com.br/api/v1"  # Para teste
    # BASE_URL = "https://api.openpix.com.br/api/v1"  # Para produção
    
    def __init__(self):
        self.headers = {
            "Authorization": settings.OPENPIX_TOKEN,
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger('payments')
    
    def create_charge(self, enrollment, correlation_id=None, use_local_simulation=False):
        """Cria uma cobrança Pix para uma matrícula"""
        # implementação...
    
    def get_charge_status(self, correlation_id, use_local_simulation=False, force_completed=False):
        """Verifica o status de uma cobrança pelo ID de correlação"""
        # implementação...
    
    def simulate_payment(self, correlation_id, use_local_simulation=False):
        """Simula o pagamento de uma cobrança (apenas para desenvolvimento)"""
        # implementação...
```

### 3.4 Views Principais

#### 3.4.1 Criação de Pagamento PIX

```python
@login_required
def create_pix_payment(request, course_id):
    """
    Cria um pagamento via Pix para o curso selecionado.
    """
    course = get_object_or_404(Course, id=course_id, status=Course.Status.PUBLISHED)
    
    # Verificar se já está matriculado com status ACTIVE
    if Enrollment.objects.filter(student=request.user, course=course, status=Enrollment.Status.ACTIVE).exists():
        messages.warning(request, _('Você já está matriculado neste curso.'))
        return redirect('courses:student:course_detail', pk=course.id)
    
    # Verificar se já existe um pagamento pendente
    existing_payment = PaymentTransaction.objects.filter(
        enrollment__student=request.user,
        enrollment__course=course,
        status=PaymentTransaction.Status.PENDING,
        payment_method='PIX'
    ).first()
    
    if existing_payment:
        return redirect('payments:pix_payment_detail', payment_id=existing_payment.id)
    
    # Criar matrícula com status PENDING
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'status': Enrollment.Status.PENDING}
    )
    
    # Se a matrícula já existia mas não está com status PENDING, atualizar
    if not created and enrollment.status != Enrollment.Status.PENDING:
        enrollment.status = Enrollment.Status.PENDING
        enrollment.save()
    
    # Criar cobrança na OpenPix
    openpix = OpenPixService()
    try:
        charge_data = openpix.create_charge(enrollment)
        
        # Salvar informações do pagamento
        payment = PaymentTransaction.objects.create(
            enrollment=enrollment,
            amount=course.price,
            status=PaymentTransaction.Status.PENDING,
            payment_method='PIX',
            correlation_id=charge_data.get('correlationID'),
            brcode=charge_data.get('brCode'),
            qrcode_image=charge_data.get('qrCodeImage')
        )
        
        return redirect('payments:pix_payment_detail', payment_id=payment.id)
    except Exception as e:
        # Tratamento de erro
        # ...
```

#### 3.4.2 Webhook para Confirmação de Pagamento

```python
@csrf_exempt
@require_POST
def pix_webhook(request):
    """
    Webhook para receber notificações de pagamento da OpenPix.
    """
    # Verificar assinatura do webhook (em produção)
    if not settings.DEBUG and settings.OPENPIX_WEBHOOK_SECRET:
        signature = request.headers.get('x-webhook-signature', '')
        payload = request.body
        expected_signature = hmac.new(
            settings.OPENPIX_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return HttpResponse(status=401)
    
    # Processar dados do webhook
    payload = json.loads(request.body.decode('utf-8'))
    
    # Verificar o tipo de evento
    event = payload.get('event')
    if event != 'CHARGE_COMPLETED':
        return HttpResponse(status=200)
    
    # Obter dados da cobrança
    charge = payload.get('charge', {})
    correlation_id = charge.get('correlationID')
    status = charge.get('status')
    
    if not correlation_id or status != 'COMPLETED':
        return HttpResponse(status=200)
    
    # Atualizar transação e matrícula
    try:
        transaction = PaymentTransaction.objects.get(correlation_id=correlation_id)
        
        if transaction.status != PaymentTransaction.Status.PAID:
            # Marcar como pago
            transaction.status = PaymentTransaction.Status.PAID
            transaction.payment_date = timezone.now()
            transaction.save()
            
            # Atualizar status da matrícula
            enrollment = transaction.enrollment
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()
    except PaymentTransaction.DoesNotExist:
        # Tratamento se não encontrar a transação
        pass
    
    return HttpResponse(status=200)
```

## 4. Configuração

### 4.1 Settings

```python
# Em settings.py

# Para ambiente de desenvolvimento (sandbox)
OPENPIX_TOKEN = 'appid.token'  # Token de teste
OPENPIX_WEBHOOK_SECRET = 'seu-segredo-webhook'  # Segredo para validação de webhooks
DEBUG = True  # Em ambiente de desenvolvimento

# Para ambiente de produção
# OPENPIX_TOKEN = 'seu-token-de-producao'
# OPENPIX_WEBHOOK_SECRET = 'seu-segredo-webhook-producao'
# DEBUG = False
```

### 4.2 URLs

```python
# Em payments/urls.py
urlpatterns = [
    path('pix/create/<int:course_id>/', create_pix_payment, name='create_pix_payment'),
    path('pix/detail/<int:payment_id>/', pix_payment_detail, name='pix_payment_detail'),
    path('pix/webhook/', pix_webhook, name='pix_webhook'),
    path('pix/check-status/<int:payment_id>/', check_payment_status, name='check_pix_status'),
    path('pix/simulate/<int:payment_id>/', simulate_pix_payment, name='simulate_pix_payment'),
]
```

## 5. Testes

### 5.1 Testes em Ambiente de Desenvolvimento

1. **Preparação**:
   - Certifique-se de que está em modo DEBUG=True
   - Configure o token de sandbox da OpenPix

2. **Teste do Fluxo Completo**:
   - Crie um curso com um preço (ex: R$ 50,00)
   - Faça login como um aluno
   - Acesse o curso e clique em "Matricular-se"
   - Verifique se é redirecionado para a página de pagamento PIX
   - Verifique se o QR Code e o código PIX são exibidos
   - Clique no botão "Simular pagamento" (disponível apenas em ambiente de desenvolvimento)
   - Verifique se o status da matrícula muda para ACTIVE
   - Verifique se consegue acessar o conteúdo do curso

3. **Teste de Verificação de Status**:
   - Inicie o fluxo de pagamento sem clicar em "Simular pagamento"
   - Clique no botão "Verificar pagamento" 
   - Verifique se o sistema responde corretamente que o pagamento ainda está pendente

4. **Teste de Acesso Negado**:
   - Com uma matrícula em status PENDING, tente acessar diretamente o conteúdo do curso
   - Verifique se o sistema redireciona para a página de pagamento

### 5.2 Testes em Ambiente de Produção

1. **Preparação**:
   - Mude para DEBUG=False
   - Configure as credenciais de produção da OpenPix
   - Configure um domínio público para receber webhooks
   - Registre a URL do webhook no painel da OpenPix

2. **Teste com Pagamento Real**:
   - **IMPORTANTE**: Use um valor mínimo de R$ 5,00 para o teste (evitando problemas com as taxas da OpenPix)
   - Faça login como um aluno
   - Matricule-se em um curso pago
   - Realize o pagamento usando um app bancário real
   - Verifique se o webhook recebe a notificação 
   - Confirme se o status da matrícula é atualizado corretamente

3. **Conciliação**:
   - Após o teste, verifique no painel da OpenPix se a transação foi registrada corretamente
   - Compare os dados da transação com os registros no banco de dados

4. **Procedimento de Estorno** (se necessário):
   - Para testes, você pode estornar o pagamento pelo app bancário ou pelo painel da OpenPix
   - Verifique se o webhook de estorno é processado corretamente

## 6. Considerações para Produção

### 6.1 Segurança

- **Proteção do Webhook**: É crucial validar a assinatura do webhook para garantir que as requisições são realmente da OpenPix
- **HTTPS**: Sempre use HTTPS em produção para proteger as transações
- **Logs**: Mantenha logs detalhados de todas as transações para auditoria
- **Validação**: Valide o valor da cobrança contra o preço do curso para evitar manipulações

### 6.2 Tratamento de Erros

- Implementar retry para falhas temporárias de comunicação
- Criar um processo manual para conciliação de pagamentos que não forem processados automaticamente
- Monitorar os logs de erros relacionados ao pagamento

### 6.3 Taxas da OpenPix

- A OpenPix cobra uma taxa fixa por transação (entre R$0,10 e R$0,15)
- Também existe uma taxa percentual (geralmente 0,99% a 1,99% do valor)
- Para valores muito baixos (menos de R$5,00), o custo da taxa pode ser significativo em relação ao valor da transação

## 7. Resolução de Problemas Comuns

### 7.1 Pagamento não confirmado automaticamente

**Possíveis causas**:
- Webhook não está configurado corretamente
- URL do webhook não está acessível publicamente
- Erro na validação da assinatura do webhook

**Solução**:
- Verifique os logs do servidor para identificar se o webhook está sendo recebido
- Confirme que a URL do webhook está corretamente registrada no painel da OpenPix
- Verifique se a validação da assinatura está configurada corretamente

### 7.2 QR Code não é exibido

**Possíveis causas**:
- Erro na comunicação com a API da OpenPix
- Token inválido ou expirado
- Problemas de configuração da conta OpenPix

**Solução**:
- Verifique os logs para identificar erros na comunicação com a API
- Confirme que o token da OpenPix está correto e ativo
- Verifique se a conta da OpenPix está ativa e configurada corretamente

### 7.3 URLs úteis para diagnóstico

- Painel da OpenPix: https://app.openpix.com.br/
- Documentação da API: https://developers.openpix.com.br/api/
- Status da API: https://status.openpix.com.br/

## 8. Conclusão

A integração com a plataforma OpenPix para pagamentos PIX oferece uma solução robusta e conveniente para os alunos realizarem pagamentos por cursos. Esta documentação busca fornecer todas as informações necessárias para entender, testar e manter essa integração crítica.

Por se tratar de uma funcionalidade que lida diretamente com pagamentos reais, é fundamental seguir as melhores práticas de segurança e realizar testes exaustivos antes de disponibilizar em produção.

Para informações adicionais sobre a API da OpenPix, consulte a documentação oficial em https://developers.openpix.com.br/api/.

## 9. Simulação de Pagamentos para Demonstração

### 9.1 Botão de Simulação de Pagamento

Para facilitar testes e demonstrações do fluxo completo de pagamento e matrícula, o sistema implementa um botão de simulação de pagamento na página de pagamento PIX. Esta funcionalidade foi desenvolvida exclusivamente para fins de demonstração e teste do sistema.

```
┌───────────────────────────────────┐
│                                   │
│     ┌───────────────────────┐     │
│     │     QR Code PIX       │     │
│     └───────────────────────┘     │
│                                   │
│     ┌───────────────────────┐     │
│     │  Código Copia e Cola  │     │
│     └───────────────────────┘     │
│                                   │
│     ┌───────────────────────┐     │
│     │   Simular Pagamento   │     │
│     └───────────────────────┘     │
│                                   │
└───────────────────────────────────┘
```

### 9.2 Funcionamento da Simulação

O botão "Simular Pagamento" executa os seguintes passos:

1. Exibe um modal com animação de carregamento (spinner)
2. Apresenta uma sequência de mensagens simulando as etapas de um pagamento real:
   - "Conectando ao sistema de pagamento..."
   - "Verificando os dados da transação..."
   - "Confirmando pagamento..."
   - "Pagamento confirmado! Redirecionando..."
3. Faz uma requisição AJAX para o endpoint `/pix/simulate/<payment_id>/` 
4. O backend marca o pagamento como PAID e a matrícula como ACTIVE
5. O usuário é redirecionado automaticamente para a página do curso

### 9.3 Controle de Disponibilidade

Esta funcionalidade está disponível apenas em ambientes de desenvolvimento ou teste, controlada pelas seguintes configurações:

```python
# Em settings.py
DEBUG = True                 # Ambiente de desenvolvimento padrão
DEBUG_PAYMENTS = True        # Específico para habilitar funcionalidades de teste de pagamento
```

O template verifica estas configurações para mostrar ou esconder os botões de simulação:

```html
{% if debug or debug_payments %}
    <!-- Botões de simulação de pagamento são exibidos -->
{% endif %}
```

### 9.4 Implementação no Backend

A função de simulação de pagamento foi implementada para verificar a configuração `DEBUG_PAYMENTS`, permitindo que a simulação seja habilitada mesmo em um ambiente de produção para fins de demonstração específicos:

```python
@login_required
def simulate_pix_payment(request, payment_id):
    """
    Simula o pagamento de uma cobrança Pix no ambiente de sandbox.
    Essa função só deve ser utilizada em ambiente de desenvolvimento ou teste.
    """
    # Verificar se estamos em ambiente de DEBUG ou DEBUG_PAYMENTS
    if not settings.DEBUG and not getattr(settings, 'DEBUG_PAYMENTS', False):
        messages.error(request, _('Esta funcionalidade está disponível apenas em ambiente de testes.'))
        return redirect('courses:student:dashboard')
    
    # Implementação da simulação de pagamento...
```

### 9.5 Melhorias na Simulação para Ambiente de Deploy

Foram implementadas as seguintes melhorias para garantir o funcionamento correto da simulação em ambientes de deploy:

#### 9.5.1 Suporte a Requisições AJAX

O backend foi aprimorado para responder adequadamente tanto para requisições normais quanto para requisições AJAX, retornando respostas JSON quando apropriado:

```python
# Exemplo de resposta para requisições AJAX
if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
    return JsonResponse({
        'success': True,
        'redirect_url': reverse('courses:student:course_learn', kwargs={'pk': enrollment.course.id})
    })
```

#### 9.5.2 Tratamento de Erros Aprimorado

A implementação de simulação de pagamento agora inclui tratamento de erros mais robusto:

- Verificação detalhada do status da resposta HTTP
- Exibição de mensagens de erro específicas no modal
- Logs detalhados no console do navegador para facilitar diagnóstico
- Suporte a fallback para simulação local quando a API falha

```javascript
// Código JavaScript melhorado para tratamento de erros
try {
    const response = await fetch(pixConfig.simulateUrl, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        console.error('Erro na resposta:', errorText);
        throw new Error(`Erro na resposta: ${response.status} ${errorText}`);
    }
} catch (error) {
    console.error('Erro ao simular pagamento:', error);
    simulationMessage.innerHTML = `<span class="text-danger">Erro ao processar pagamento.</span><br><small>${error.message}</small>`;
}
```

#### 9.5.3 Verificação de Ambiente Flexível

O serviço OpenPix foi modificado para detectar corretamente ambientes de teste, considerando tanto a configuração `DEBUG` quanto `DEBUG_PAYMENTS`:

```python
def is_sandbox_mode(self):
    """
    Verifica se o serviço está operando em ambiente de sandbox ou se DEBUG_PAYMENTS está ativo
    """
    # Verificar tanto DEBUG quanto DEBUG_PAYMENTS
    return settings.DEBUG or getattr(settings, 'DEBUG_PAYMENTS', False)
```

Isso permite que o botão de simulação funcione corretamente:
1. Durante o desenvolvimento local (quando `DEBUG=True`)
2. Em ambientes de homologação (quando `DEBUG=False`, mas `DEBUG_PAYMENTS=True`)
3. Em demonstrações para clientes (usando a configuração `DEBUG_PAYMENTS=True`) 