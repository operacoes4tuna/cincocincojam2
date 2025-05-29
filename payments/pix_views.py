from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from django.urls import reverse

# Modelos
from courses.models import Course, Enrollment
from .models import PaymentTransaction

# Serviços
from .openpix_service import OpenPixService

@login_required
def create_pix_payment(request, course_id):
    """
    Cria um pagamento via Pix para o curso selecionado.
    """
    course = get_object_or_404(Course, id=course_id, status=Course.Status.PUBLISHED)
    
    # Verificar se o usuário já está matriculado com matrícula ATIVA
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
    
    # Se a matrícula já existia e não está com status PENDING, atualizar para PENDING
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
        # Se houver erro, excluir a matrícula pendente se foi criada agora
        if created:
            enrollment.delete()
        
        messages.error(request, _('Erro ao gerar cobrança Pix. Por favor, tente novamente.'))
        return redirect('courses:student:course_detail', pk=course.id)

@login_required
def pix_payment_detail(request, payment_id):
    """
    Exibe os detalhes do pagamento via Pix e o QR Code para o usuário.
    """
    payment = get_object_or_404(
        PaymentTransaction, 
        id=payment_id, 
        enrollment__student=request.user,
        payment_method='PIX'
    )
    
    # Se o pagamento já estiver confirmado, redireciona para a página de aprendizado do curso
    if payment.status == PaymentTransaction.Status.PAID:
        messages.success(request, _('Seu pagamento já foi confirmado. Você está matriculado no curso.'))
        return redirect('courses:student:course_learn', pk=payment.enrollment.course.id)
    
    # Atualizar status do pagamento se ainda estiver pendente
    if payment.status == PaymentTransaction.Status.PENDING:
        try:
            openpix = OpenPixService()
            status_data = openpix.get_charge_status(payment.correlation_id)
            
            if status_data.get('status') == 'COMPLETED':
                payment.status = PaymentTransaction.Status.PAID
                payment.payment_date = timezone.now()
                payment.save()
                
                # Atualizar status da matrícula
                enrollment = payment.enrollment
                enrollment.status = Enrollment.Status.ACTIVE
                enrollment.save()
                
                messages.success(request, _('Pagamento confirmado! Você foi matriculado no curso.'))
                return redirect('courses:student:course_learn', pk=enrollment.course.id)
        except Exception as e:
            messages.error(request, _('Erro ao verificar status do pagamento: {}').format(str(e)))
    
    # Preparar contexto
    context = {
        'payment': payment,
        'course': payment.enrollment.course,
        'debug': settings.DEBUG,
        'debug_payments': getattr(settings, 'DEBUG_PAYMENTS', False)
    }
    
    return render(request, 'payments/pix_payment_detail.html', context)

@csrf_exempt
@require_POST
def pix_webhook(request):
    """
    Webhook para receber notificações de pagamento da OpenPix.
    """
    # A implementação completa do webhook será feita posteriormente
    import json
    import logging
    import hmac
    import hashlib
    from django.conf import settings
    from .models import PaymentTransaction
    from courses.models import Enrollment
    
    logger = logging.getLogger('payments')
    
    # Log da requisição recebida
    logger.info("Webhook OpenPix recebido")
    
    try:
        # Verificar assinatura do webhook (quando estiver em produção)
        if not settings.DEBUG and settings.OPENPIX_WEBHOOK_SECRET:
            signature = request.headers.get('x-webhook-signature', '')
            
            # Calcular assinatura esperada
            payload = request.body
            expected_signature = hmac.new(
                settings.OPENPIX_WEBHOOK_SECRET.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.error(f"Assinatura de webhook inválida. Recebida: {signature}, Esperada: {expected_signature}")
                return HttpResponse(status=401)
        
        # Obter dados do webhook
        payload = json.loads(request.body.decode('utf-8'))
        logger.info(f"Payload do webhook: {json.dumps(payload)[:200]}...") # Log truncado para não ser muito grande
        
        # Verificar o tipo de evento
        event = payload.get('event')
        if event != 'CHARGE_COMPLETED':
            logger.info(f"Evento ignorado: {event}")
            return HttpResponse(status=200)  # Aceitar o webhook, mas ignorar eventos que não sejam de pagamento concluído
        
        # Obter dados da cobrança
        charge = payload.get('charge', {})
        correlation_id = charge.get('correlationID')
        status = charge.get('status')
        
        if not correlation_id or status != 'COMPLETED':
            logger.info(f"Ignorando webhook - correlation_id ausente ou status diferente de COMPLETED: {status}")
            return HttpResponse(status=200)
        
        logger.info(f"Processando pagamento para correlation_id: {correlation_id}")
        
        # Buscar a transação correspondente
        try:
            # Primeiro, verificar pagamento de curso
            transaction = PaymentTransaction.objects.get(correlation_id=correlation_id)
            
            # Se já estiver pago, apenas retorna sucesso
            if transaction.status == PaymentTransaction.Status.PAID:
                logger.info(f"Transação {transaction.id} já estava marcada como paga.")
                return HttpResponse(status=200)
            
            # Marcar como pago
            transaction.status = PaymentTransaction.Status.PAID
            transaction.payment_date = timezone.now()
            transaction.save()
            
            # Atualizar status da matrícula
            enrollment = transaction.enrollment
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()
            
            logger.info(f"Pagamento confirmado para matrícula {enrollment.id} via webhook.")
            return HttpResponse(status=200)
            
        except PaymentTransaction.DoesNotExist:
            # Verificar se é uma venda avulsa
            from .models import SingleSale
            try:
                sale = SingleSale.objects.get(correlation_id=correlation_id)
                
                # Se já estiver pago, apenas retorna sucesso
                if sale.status == SingleSale.Status.PAID:
                    logger.info(f"Venda avulsa {sale.id} já estava marcada como paga.")
                    return HttpResponse(status=200)
                
                # Marcar como pago
                sale.mark_as_paid()
                logger.info(f"Pagamento confirmado para venda avulsa {sale.id} via webhook.")
                return HttpResponse(status=200)
                
            except SingleSale.DoesNotExist:
                logger.error(f"Nenhuma transação encontrada para correlation_id: {correlation_id}")
                return HttpResponse(status=404)
    
    except Exception as e:
        logger.exception(f"Erro ao processar webhook: {str(e)}")
        return HttpResponse(status=500)
    
    return HttpResponse(status=200)

def check_payment_status(request, payment_id):
    """
    Endpoint AJAX para verificar o status de um pagamento.
    """
    payment = get_object_or_404(
        PaymentTransaction, 
        id=payment_id, 
        enrollment__student=request.user,
        payment_method='PIX'
    )
    
    if payment.status == PaymentTransaction.Status.PENDING:
        try:
            openpix = OpenPixService()
            status_data = openpix.get_charge_status(payment.correlation_id)
            
            if status_data.get('status') == 'COMPLETED':
                payment.status = PaymentTransaction.Status.PAID
                payment.payment_date = timezone.now()
                payment.save()
                
                # Atualizar status da matrícula
                enrollment = payment.enrollment
                enrollment.status = Enrollment.Status.ACTIVE
                enrollment.save()
                
                return JsonResponse({
                    'status': 'PAID',
                    'redirect_url': reverse('courses:student:course_learn', kwargs={'pk': enrollment.course.id})
                })
        except Exception as e:
            return JsonResponse({'status': 'ERROR', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': payment.status})

@login_required
def simulate_pix_payment(request, payment_id):
    """
    Simula o pagamento de uma cobrança Pix no ambiente de sandbox.
    Essa função só deve ser utilizada em ambiente de desenvolvimento.
    """
    # Verificar se estamos em ambiente de DEBUG ou DEBUG_PAYMENTS
    if not settings.DEBUG and not getattr(settings, 'DEBUG_PAYMENTS', False):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Esta funcionalidade está disponível apenas em ambiente de testes.'
            }, status=403)
        messages.error(request, _('Esta funcionalidade está disponível apenas em ambiente de testes.'))
        return redirect('courses:student:dashboard')
    
    try:
        # Importar o modelo aqui para evitar importação circular
        from courses.models import Enrollment
        from .models import PaymentTransaction
        
        payment = get_object_or_404(PaymentTransaction, id=payment_id)
        
        # Verificar se o usuário é o dono do pagamento
        if payment.enrollment.student != request.user and not request.user.is_staff:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Você não tem permissão para simular este pagamento.'
                }, status=403)
            messages.error(request, _('Você não tem permissão para simular este pagamento.'))
            return redirect('courses:student:dashboard')
        
        # Verificar se o pagamento já foi confirmado
        if payment.status != PaymentTransaction.Status.PENDING:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Este pagamento não está pendente.'
                }, status=400)
            messages.warning(request, _('Este pagamento não está pendente.'))
            return redirect('payments:pix_payment_detail', payment_id=payment.id)
        
        # Chamar API da OpenPix para simular pagamento
        from .openpix_service import OpenPixService
        openpix = OpenPixService()
        
        # Registrar informações no log
        print(f"Tentando simular pagamento: ID={payment_id}, Correlation ID={payment.correlation_id}")
        
        # Usar simulação local por padrão para evitar problemas de SSL
        result = openpix.simulate_payment(payment.correlation_id, use_local_simulation=True)
        
        if result.get('success'):
            # Atualizar status do pagamento para facilitar testes (opcional)
            payment.status = PaymentTransaction.Status.PAID
            payment.payment_date = timezone.now()
            payment.save()
            
            # Também atualizar o status da matrícula
            enrollment = payment.enrollment
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('courses:student:course_learn', kwargs={'pk': enrollment.course.id})
                })
                
            messages.success(request, _('Pagamento simulado com sucesso! Você foi matriculado no curso.'))
            # Redirecionar para a página de aprendizado do curso em vez da página de pagamento
            return redirect('courses:student:course_learn', pk=enrollment.course.id)
        else:
            error_detail = result.get('error', 'Erro desconhecido')
            print(f"Erro na simulação: {error_detail}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_detail
                }, status=500)
                
            messages.error(request, _(f'Erro ao simular pagamento: {error_detail}'))
            return redirect('payments:pix_payment_detail', payment_id=payment.id)
    
    except Exception as e:
        # Log do erro para depuração
        import traceback
        print(f"Erro ao processar simulação de pagamento: {str(e)}")
        print(traceback.format_exc())
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
            
        messages.error(request, _(f'Erro ao processar simulação: {str(e)}'))
        return redirect('courses:student:dashboard')
