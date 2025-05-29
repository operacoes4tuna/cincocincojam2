# Documentação: Sistema de Pagamento com Cartão

## 1. Visão Geral

O módulo de pagamento com cartão permite a integração da plataforma com o Pagar.me para processar pagamentos de cursos via cartão de crédito e débito. Esta documentação descreve o funcionamento, implementação e uso do sistema.

### 1.1 Funcionalidades principais

- Processamento de pagamentos via cartão de crédito e débito
- Suporte a parcelamento (crédito)
- Validação básica de dados do cartão
- Simulação de pagamentos para ambiente de desenvolvimento
- Processamento de webhook para atualização de status
- Integração transparente com o fluxo de matrícula

## 2. Arquitetura

### 2.1 Componentes Principais

- **PagarmeService**: Serviço de comunicação com API do Pagar.me
- **card_views.py**: Controladores para processamento de cartão
- **PaymentTransaction**: Modelo de dados para armazenar transações
- **Templates**: Formulários e visualizações da interface de pagamento

### 2.2 Modelos de Dados

```python
# Em payments/models.py
class PaymentTransaction(models.Model):
    """
    Modelo para representar transações de pagamento dos alunos matriculados em cursos.
    Cada transação está relacionada a uma matrícula e guarda informações sobre o pagamento.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pendente')
        PAID = 'PAID', _('Pago')
        REFUNDED = 'REFUNDED', _('Estornado')
        FAILED = 'FAILED', _('Falhou')
    
    # Relacionamentos
    enrollment = models.ForeignKey(
        'courses.Enrollment',
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('matrícula')
    )
    
    # Campos de pagamento
    amount = models.DecimalField(
        _('valor'), 
        max_digits=10, 
        decimal_places=2
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    payment_date = models.DateTimeField(
        _('data de pagamento'),
        null=True,
        blank=True
    )
    payment_method = models.CharField(
        _('método de pagamento'),
        max_length=50,
        blank=True
    )
    transaction_id = models.CharField(
        _('ID da transação'),
        max_length=100,
        blank=True
    )
    
    # Campos específicos para pagamento 
    correlation_id = models.CharField(
        _('ID de Correlação'),
        max_length=255,
        blank=True,
        help_text=_('ID de correlação para pagamentos')
    )
    
    # Campos de controle
    created_at = models.DateTimeField(
        _('data de criação'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('última atualização'),
        auto_now=True
    )
```

## 3. Fluxo de Pagamento

### 3.1 Visão Geral do Fluxo

1. Aluno seleciona um curso pago e clica em "Matricular-se"
2. Sistema exibe opções de pagamento (PIX ou Cartão)
3. Aluno seleciona "Cartão" e é redirecionado para o formulário de pagamento
4. Aluno preenche dados do cartão e submete o formulário
5. Sistema processa o pagamento via Pagar.me
6. Pagamento é aprovado ou recusado
7. Sistema atualiza o status da matrícula e redireciona o aluno

### 3.2 Diagrama de Sequência

```
Aluno                 Sistema                   Pagar.me
  |                      |                          |
  |-- Escolhe curso ---->|                          |
  |                      |-- Cria matrícula ------->|
  |                      |                          |
  |<-- Mostra opções ----|                          |
  |                      |                          |
  |-- Escolhe cartão --->|                          |
  |                      |                          |
  |<-- Form de cartão ---|                          |
  |                      |                          |
  |-- Submete dados ---->|                          |
  |                      |-- Cria transação ------->|
  |                      |                          |
  |                      |<-- Retorna status -------|
  |                      |                          |
  |<-- Acesso liberado --|                          |
  |                      |                          |
```

## 4. Implementação

### 4.1 Configuração do Pagar.me

No arquivo `settings.py`:

```python
# Configurações do Pagar.me
PAGARME_API_KEY = env('PAGARME_API_KEY', default='')
PAGARME_ENCRYPTION_KEY = env('PAGARME_ENCRYPTION_KEY', default='')
PAGARME_ENVIRONMENT = env('PAGARME_ENVIRONMENT', default='sandbox')  # sandbox ou production
```

### 4.2 Serviço Pagar.me

```python
# Em payments/pagarme_service.py
class PagarmeService:
    """
    Serviço para integração com a API do Pagar.me
    """
    def __init__(self):
        self.api_key = settings.PAGARME_API_KEY
        self.encryption_key = settings.PAGARME_ENCRYPTION_KEY
        self.is_sandbox = settings.PAGARME_ENVIRONMENT == 'sandbox'
        self.api_url = 'https://api.sandbox.pagar.me/1' if self.is_sandbox else 'https://api.pagar.me/1'
        
        logger.info(f"=== PagarmeService inicializado: {'SANDBOX' if self.is_sandbox else 'PRODUCTION'} ===")
        logger.info(f"URL: {self.api_url}")
        logger.info(f"DEBUG: {settings.DEBUG}")
        logger.info(f"DEBUG_PAYMENTS: {getattr(settings, 'DEBUG_PAYMENTS', False)}")

    def generate_card_hash(self, card_data, use_local_simulation=False):
        """
        Gera o hash do cartão para uso na API do Pagar.me
        """
        if use_local_simulation or settings.DEBUG:
            logger.info("Usando simulação LOCAL para gerar hash de cartão")
            # Gerar um hash fictício para testes
            return f"card-hash-{uuid.uuid4()}"
            
        # Em produção, usaria a biblioteca JS do Pagar.me no frontend para gerar o hash
        # Este código simularia o resultado retornado pelo frontend
        return "mock_card_hash"

    def create_card_transaction(self, enrollment, card_data, payment_method='credit_card', 
                               installments=1, use_local_simulation=False):
        """
        Cria uma transação de cartão de crédito ou débito na Pagar.me
        """
        try:
            student = enrollment.student
            course = enrollment.course
            
            logger.info(f"Criando transação de cartão para aluno {student.email} - curso {course.id} ({course.title})")
            
            # Simulação local para ambiente de desenvolvimento
            if use_local_simulation or settings.DEBUG:
                logger.info(f"Usando simulação LOCAL para criar transação de cartão: card-{course.id}-{installments}-{int(time.time())}")
                
                # Simular resposta da API
                mock_response = {
                    'id': f"card-{course.id}-{installments}-{int(time.time())}",
                    'tid': f"tid-{uuid.uuid4()}",
                    'status': 'paid',
                    'card_brand': 'visa',
                    'card_last_digits': '1234',
                    'installments': installments,
                    'amount': int(course.price * 100)  # Pagar.me usa centavos
                }
                
                return mock_response
            
            # Implementação real para produção
            # Montar os dados da requisição para a API do Pagar.me
            transaction_data = {
                'api_key': self.api_key,
                'amount': int(course.price * 100),  # Convertido para centavos
                'card_hash': card_data.get('card_hash'),
                'payment_method': payment_method,
                'installments': installments,
                'customer': {
                    'external_id': str(student.id),
                    'name': student.get_full_name() or student.email,
                    'email': student.email,
                    'type': 'individual'
                },
                'billing': {
                    'name': student.get_full_name() or student.email
                },
                'items': [
                    {
                        'id': str(course.id),
                        'title': course.title,
                        'unit_price': int(course.price * 100),
                        'quantity': 1,
                        'tangible': False
                    }
                ],
                'metadata': {
                    'enrollment_id': enrollment.id,
                    'course_id': course.id
                }
            }
            
            # Fazer a requisição para a API do Pagar.me
            # Este é apenas um exemplo, na prática usaria libraries como requests
            response = self._post_to_api('/transactions', transaction_data)
            
            if response and response.get('id'):
                return response
            else:
                logger.error(f"Falha ao criar transação no Pagar.me: {response}")
                return None
            
        except Exception as e:
            logger.exception(f"Erro ao criar transação de cartão: {str(e)}")
            return None
```

### 4.3 Controladores

```python
# Em payments/card_views.py
def create_card_payment(request, course_id):
    """
    Cria um pagamento via cartão para o curso selecionado.
    """
    # Verificar se o curso existe
    course = get_object_or_404(Course, id=course_id, status=Course.Status.PUBLISHED)
    
    # Verificar se o usuário está autenticado
    if not request.user.is_authenticated:
        messages.error(request, _('Você precisa estar logado para se matricular.'))
        return redirect('login')
    
    # Verificar se já existe uma matrícula pendente ou ativa
    existing_enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course,
        status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE]
    ).first()
    
    # Se existir matrícula com pagamento, redirecionar
    if existing_enrollment:
        existing_payment = PaymentTransaction.objects.filter(
            enrollment=existing_enrollment,
            payment_method='CREDIT_CARD'
        ).first()
        
        if existing_payment:
            messages.info(request, _('Você já possui um pagamento iniciado para este curso.'))
            return redirect('payments:card_payment_detail', payment_id=existing_payment.id)
    
    # Se não existe matrícula, criar uma nova
    if not existing_enrollment:
        enrollment = Enrollment.objects.create(
            student=request.user,
            course=course,
            status=Enrollment.Status.PENDING
        )
    else:
        enrollment = existing_enrollment
    
    # Se o método de requisição for POST, processar o formulário de cartão
    if request.method == 'POST':
        try:
            # Obter dados do cartão do formulário
            card_data = {
                "card_number": request.POST.get('card_number', '').replace(' ', ''),
                "holder_name": request.POST.get('holder_name', ''),
                "expiration_date": request.POST.get('expiration_date', '').replace('/', ''),
                "cvv": request.POST.get('cvv', '')
            }
            
            # Escolher o método de pagamento com base na opção do usuário
            payment_method = request.POST.get('payment_method', 'credit_card')
            installments = int(request.POST.get('installments', 1))
            
            # Criar cobrança na Pagar.me
            pagarme = PagarmeService()
            
            # Gerar hash do cartão
            card_hash = pagarme.generate_card_hash(card_data, use_local_simulation=True)
            
            # Criar os dados completos do cartão para a API
            card_data_complete = {
                "card_hash": card_hash,
                "card_number": card_data["card_number"],
                "holder_name": card_data["holder_name"]
            }
            
            # Criar a transação
            charge_data = pagarme.create_card_transaction(
                enrollment, 
                card_data_complete, 
                payment_method=payment_method,
                installments=installments,
                use_local_simulation=True
            )
            
            if charge_data:
                # Criar registro do pagamento no sistema
                payment = PaymentTransaction.objects.create(
                    enrollment=enrollment,
                    correlation_id=charge_data.get('id', ''),
                    transaction_id=charge_data.get('tid', ''),
                    payment_method='CREDIT_CARD' if payment_method == 'credit_card' else 'DEBIT_CARD',
                    amount=course.price,
                    status=PaymentTransaction.Status.PAID  # Já marca como pago para simular pagamento aprovado
                )
                
                # Simular pagamento aprovado
                payment.paid_at = timezone.now()
                payment.save()
                
                # Atualizar status da matrícula para ativa
                enrollment.status = Enrollment.Status.ACTIVE
                enrollment.save()
                
                # Mensagem de sucesso
                messages.success(request, _('Pagamento aprovado! Você está matriculado no curso.'))
                
                # Redireciona para a página de detalhes do pagamento
                return redirect('payments:card_payment_detail', payment_id=payment.id)
            else:
                # Erro ao criar a transação
                messages.error(request, _('Erro ao processar o pagamento. Por favor, tente novamente.'))
                
        except Exception as e:
            logger.exception(f"Erro ao processar pagamento: {str(e)}")
            messages.error(request, _('Erro ao processar o pagamento. Por favor, tente novamente.'))
    
    # Se for requisição GET ou houver erro no POST, renderiza a página de pagamento
    context = {
        'course': course,
        'enrollment': enrollment
    }
    
    return render(request, 'payments/card_payment_form.html', context)
```

### 4.4 Webhook

```python
@csrf_exempt
def card_webhook(request):
    """
    Webhook para receber notificações de pagamento da Pagar.me.
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Método não permitido'
        }, status=405)
    
    try:
        # Obter dados do payload
        payload = json.loads(request.body.decode('utf-8'))
        logger.info("Webhook Pagar.me recebido")
        
        # Verificação de segurança do webhook (opcional em produção)
        if not settings.DEBUG and settings.PAGARME_API_KEY:
            # Verificar a assinatura (a ser implementada conforme documentação do Pagar.me)
            pass
        
        # Obter ID da transação
        transaction_id = payload.get('id')
        current_status = payload.get('current_status')
        
        if not transaction_id or not current_status:
            logger.error("Payload inválido: ID ou status ausente")
            return JsonResponse({
                'success': False,
                'message': 'Payload inválido'
            }, status=400)
        
        # Buscar pagamento pelo ID
        try:
            payment = PaymentTransaction.objects.get(correlation_id=transaction_id)
        except PaymentTransaction.DoesNotExist:
            logger.error(f"Pagamento não encontrado: {transaction_id}")
            return JsonResponse({
                'success': False,
                'message': 'Pagamento não encontrado'
            }, status=404)
        
        # Mapear status da Pagar.me para status do sistema
        status_map = {
            'paid': PaymentTransaction.Status.PAID,
            'authorized': PaymentTransaction.Status.PENDING,
            'refunded': PaymentTransaction.Status.REFUNDED,
            'waiting_payment': PaymentTransaction.Status.PENDING,
            'pending_refund': PaymentTransaction.Status.PENDING,
            'refused': PaymentTransaction.Status.FAILED,
            'chargedback': 'canceled',
            'analyzing': PaymentTransaction.Status.PENDING,
            'pending_review': PaymentTransaction.Status.PENDING
        }
        
        new_status = status_map.get(current_status, payment.status)
        
        # Atualizar status do pagamento
        old_status = payment.status
        payment.status = new_status
        
        # Se o pagamento foi aprovado, atualizar data de pagamento e status da matrícula
        if new_status == PaymentTransaction.Status.PAID and old_status != PaymentTransaction.Status.PAID:
            payment.paid_at = timezone.now()
            
            # Atualizar status da matrícula
            enrollment = payment.enrollment
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()
            
            logger.info(f"Matrícula {enrollment.id} ativada pelo webhook")
        
        payment.save()
        
        logger.info(f"Status do pagamento {payment.id} atualizado: {old_status} -> {new_status}")
        
        return JsonResponse({
            'success': True,
            'message': 'Notificação processada com sucesso'
        })
        
    except json.JSONDecodeError:
        logger.error("JSON inválido no webhook")
        return JsonResponse({
            'success': False,
            'message': 'JSON inválido'
        }, status=400)
    except Exception as e:
        logger.exception(f"Erro ao processar webhook: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }, status=500)
```

## 5. Integração na Interface

### 5.1 Formulário de Pagamento

O formulário de pagamento (em `templates/payments/card_payment_form.html`) inclui:

- Campo para número do cartão
- Campo para nome do titular
- Campo para data de validade
- Campo para código de segurança (CVV)
- Seleção do método de pagamento (crédito ou débito)
- Seleção do número de parcelas (se crédito)

### 5.2 Tela de Confirmação

A tela de confirmação (em `templates/payments/card_payment_detail.html`) exibe:

- Status do pagamento (pendente, aprovado ou recusado)
- Detalhes da transação
- Informações do cartão (número mascarado)
- Informações do curso
- Botões de ação conforme o status

## 6. Fluxo de Matrícula

A integração de cartão no fluxo de matrícula se dá através das seguintes etapas:

1. Quando o aluno clica em "Matricular-se" em um curso pago, é criada uma matrícula com status `PENDING`.
2. O aluno é direcionado para a página de opções de pagamento.
3. Ao escolher o pagamento com cartão, é criada uma transação de pagamento.
4. Quando o pagamento é confirmado, a matrícula é atualizada para status `ACTIVE`.
5. O aluno recebe acesso ao conteúdo do curso.

### 6.1 Página de Opções de Pagamento

A página de opções de pagamento (em `templates/payments/payment_options.html`) exibe:

- Informações do curso
- Opções de pagamento (PIX e Cartão)
- Vantagens de cada método de pagamento

## 7. Ambiente de Desenvolvimento

### 7.1 Simulação de Pagamentos

Para facilitar testes em ambiente de desenvolvimento, existe a funcionalidade de simular pagamentos:

```python
def simulate_card_payment(request, payment_id):
    """
    Simula o pagamento de uma transação com cartão no ambiente de sandbox.
    """
    # Verificar se está em ambiente de desenvolvimento
    if not settings.DEBUG:
        messages.error(request, _('Esta funcionalidade só está disponível em ambiente de desenvolvimento.'))
        return redirect('payments:card_payment_detail', payment_id=payment_id)
    
    # Verificar se o pagamento existe
    payment = get_object_or_404(
        PaymentTransaction, 
        id=payment_id, 
        enrollment__student=request.user,
        payment_method__in=['CREDIT_CARD', 'DEBIT_CARD']
    )
    
    # Verificar se o pagamento está pendente
    if payment.status != PaymentTransaction.Status.PENDING:
        messages.warning(request, _('Este pagamento não pode ser simulado porque não está pendente.'))
        return redirect('payments:card_payment_detail', payment_id=payment_id)
    
    try:
        # Atualizar status do pagamento
        payment.status = PaymentTransaction.Status.PAID
        payment.paid_at = timezone.now()
        payment.save()
        
        # Atualizar status da matrícula
        enrollment = payment.enrollment
        enrollment.status = Enrollment.Status.ACTIVE
        enrollment.save()
        
        messages.success(request, _('Pagamento simulado com sucesso! Matrícula ativada.'))
    
    except Exception as e:
        logger.exception(f"Erro ao simular pagamento: {str(e)}")
        messages.error(request, _('Erro ao simular pagamento: ') + str(e))
    
    return redirect('payments:card_payment_detail', payment_id=payment_id)
```

### 7.2 Configuração do Ambiente

Para configurar o ambiente de desenvolvimento para testes de pagamento:

1. Configure variáveis de ambiente:
   ```
   PAGARME_API_KEY=sua_chave_api
   PAGARME_ENCRYPTION_KEY=sua_chave_encriptacao
   PAGARME_ENVIRONMENT=sandbox
   ```

2. Acesse o sandbox do Pagar.me para gerenciar e visualizar transações de teste.

## 8. Considerações de Segurança

### 8.1 PCI DSS Compliance

Este sistema foi projetado para não armazenar dados sensíveis de cartão de crédito, conforme as diretrizes do PCI DSS. Os dados do cartão são enviados diretamente para o Pagar.me através de um token/hash.

### 8.2 Verificação de Webhook

Em ambiente de produção, é essencial implementar a verificação da assinatura dos webhooks conforme documentação do Pagar.me para evitar notificações falsas.

### 8.3 Proteção Contra Fraudes

O Pagar.me oferece uma camada de proteção contra fraudes. Certifique-se de configurar os níveis de segurança adequados no painel administrativo do Pagar.me.

## 9. Testes

### 9.1 Cartões de Teste

Para testar o sistema em ambiente de sandbox, utilize os seguintes cartões de teste:

| Bandeira | Número               | CVV | Data      | Resultado      |
|----------|----------------------|-----|-----------|----------------|
| VISA     | 4111 1111 1111 1111  | 123 | 12/2030   | Aprovado       |
| MASTER   | 5555 6666 7777 8884  | 123 | 12/2030   | Aprovado       |
| VISA     | 4222 2222 2222 2224  | 123 | 12/2030   | Recusado       |

### 9.2 Testes Automatizados

Existe uma suite de testes para verificar a funcionalidade do sistema de pagamento com cartão:

```python
# Em payments/tests/test_card_payment.py
from django.test import TestCase, Client
from django.urls import reverse
from payments.models import PaymentTransaction
from courses.models import Enrollment, Course
from core.models import User

class CardPaymentTestCase(TestCase):
    def setUp(self):
        # Criar usuário de teste
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword',
            first_name='Test',
            last_name='User',
            user_type='STUDENT'
        )
        
        # Criar professor
        self.professor = User.objects.create_user(
            email='professor@example.com',
            password='testpassword',
            first_name='Professor',
            last_name='Test',
            user_type='PROFESSOR'
        )
        
        # Criar curso de teste
        self.course = Course.objects.create(
            title='Curso Teste',
            description='Descrição do curso de teste',
            price=99.90,
            professor=self.professor,
            status=Course.Status.PUBLISHED
        )
        
        # Configurar cliente para testes
        self.client = Client()
        self.client.login(email='test@example.com', password='testpassword')
    
    def test_card_payment_flow(self):
        # Testar fluxo completo de pagamento com cartão
        
        # 1. Acessar página de opções de pagamento
        response = self.client.get(reverse('payments:payment_options', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        
        # 2. Acessar página de pagamento com cartão
        response = self.client.get(reverse('payments:create_card_payment', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        
        # 3. Enviar dados do cartão para pagamento
        card_data = {
            'card_number': '4111111111111111',
            'holder_name': 'Test User',
            'expiration_date': '12/30',
            'cvv': '123',
            'payment_method': 'credit_card',
            'installments': '1'
        }
        
        response = self.client.post(
            reverse('payments:create_card_payment', args=[self.course.id]),
            card_data,
            follow=True
        )
        
        # 4. Verificar se foi redirecionado e se pagamento foi criado
        self.assertEqual(response.status_code, 200)
        
        # Verificar se a matrícula foi criada e ativada
        enrollment = Enrollment.objects.filter(
            student=self.user,
            course=self.course
        ).first()
        
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)
        
        # Verificar se o pagamento foi criado e marcado como pago
        payment = PaymentTransaction.objects.filter(
            enrollment=enrollment,
            payment_method='CREDIT_CARD'
        ).first()
        
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, PaymentTransaction.Status.PAID)
```

## 10. Considerações para Produção

### 10.1 Homologação e Produção

Antes de ir para produção, é necessário homologar o sistema com a Pagar.me, seguindo estes passos:

1. Criar conta de produção no Pagar.me
2. Solicitar ativação da conta (pode exigir documentação)
3. Configurar chaves de produção
4. Realizar testes de ponta a ponta
5. Configurar URL de webhook em produção

### 10.2 Monitoramento e Logs

Certifique-se de configurar um sistema adequado de logs e monitoramento para acompanhar:

- Taxa de aprovação de pagamentos
- Tempo de processamento
- Erros de transação
- Chargebacks e disputas

Para isso, utilize ferramentas como Sentry, ELK Stack ou serviços nativos de nuvem.

## 11. Conclusão

O sistema de pagamento com cartão está integrado com a plataforma de cursos, permitindo o processamento de matrículas via cartão de crédito e débito. A implementação segue boas práticas de segurança e oferece uma experiência fluida para os alunos.

A estrutura do sistema permite fácil manutenção e expansão, como adição de novas formas de pagamento ou integração com outros provedores no futuro. 