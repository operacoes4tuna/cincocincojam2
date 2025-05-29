from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

import json
import uuid
import logging
import hmac
import hashlib
import base64

from .pagarme_service import PagarmeService
from .models import PaymentTransaction
from courses.models import Course, Enrollment
from core.models import User

logger = logging.getLogger('payments')

def create_card_payment(request, course_id):
    """
    Cria um pagamento via cartão para o curso selecionado.
    
    Args:
        request: Objeto HttpRequest
        course_id: ID do curso
    
    Returns:
        HttpResponse: Redirecionamento para a página de detalhes do pagamento ou mensagem de erro
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
    
    # Verificar se já existe um pagamento com cartão para esta matrícula
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

def card_payment_detail(request, payment_id):
    """
    Exibe os detalhes do pagamento com cartão.
    
    Args:
        request: Objeto HttpRequest
        payment_id: ID do pagamento
    
    Returns:
        HttpResponse: Página de detalhes do pagamento
    """
    # Verificar se o pagamento existe e pertence ao usuário logado
    payment = get_object_or_404(
        PaymentTransaction, 
        id=payment_id, 
        enrollment__student=request.user,
        payment_method__in=['CREDIT_CARD', 'DEBIT_CARD']
    )
    
    # Obter dados do curso e matrícula
    enrollment = payment.enrollment
    course = enrollment.course
    
    # Verificar status atual do pagamento
    if payment.status in [PaymentTransaction.Status.PENDING, 'processing']:
        # Verificar na API da Pagar.me
        pagarme = PagarmeService()
        status_data = pagarme.get_transaction_status(payment.correlation_id)
        
        # Atualizar status do pagamento se necessário
        if status_data.get('status') == 'paid' and payment.status != PaymentTransaction.Status.PAID:
            payment.status = PaymentTransaction.Status.PAID
            payment.paid_at = timezone.now()
            payment.save()
            
            # Atualizar status da matrícula
            enrollment = payment.enrollment
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()
            
            messages.success(request, _('Pagamento confirmado! Sua matrícula está ativa.'))
    
    context = {
        'payment': payment,
        'enrollment': enrollment,
        'course': course,
        'is_paid': payment.status == PaymentTransaction.Status.PAID,
        'is_pending': payment.status == PaymentTransaction.Status.PENDING,
        'is_failed': payment.status in [PaymentTransaction.Status.FAILED, 'canceled']
    }
    
    return render(request, 'payments/card_payment_detail.html', context)

@csrf_exempt
def card_webhook(request):
    """
    Webhook para receber notificações de pagamento da Pagar.me.
    
    Args:
        request: Objeto HttpRequest
    
    Returns:
        HttpResponse: Resposta JSON
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
        logger.debug(f"Payload: {json.dumps(payload)}")
        
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
            'paid': 'paid',
            'authorized': 'processing',
            'refunded': 'refunded',
            'waiting_payment': 'pending',
            'pending_refund': 'processing',
            'refused': 'failed',
            'chargedback': 'canceled',
            'analyzing': 'processing',
            'pending_review': 'processing'
        }
        
        new_status = status_map.get(current_status, payment.status)
        
        # Atualizar status do pagamento
        old_status = payment.status
        payment.status = new_status
        
        # Se o pagamento foi aprovado, atualizar data de pagamento e status da matrícula
        if new_status == 'paid' and old_status != 'paid':
            payment.paid_at = timezone.now()
            
            # Atualizar status da matrícula
            enrollment = payment.enrollment
            enrollment.status = 'active'
            enrollment.save()
            
            logger.info(f"Matrícula {enrollment.id} ativada pelo webhook")
        
        # Salvar detalhes da notificação
        payment.details = json.dumps(payload)
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

def simulate_card_payment(request, payment_id):
    """
    Simula o pagamento de uma transação com cartão no ambiente de sandbox.
    
    Args:
        request: Objeto HttpRequest
        payment_id: ID do pagamento
    
    Returns:
        HttpResponse: Redirecionamento para a página de detalhes do pagamento
    """
    # Verificar se está em ambiente de desenvolvimento
    if not settings.DEBUG:
        messages.error(request, _('Esta funcionalidade só está disponível em ambiente de desenvolvimento.'))
        return redirect('payments:card_payment_detail', payment_id=payment_id)
    
    # Verificar se o pagamento existe e pertence ao usuário logado
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
        # Chamar API da Pagar.me para simular pagamento
        pagarme = PagarmeService()
        result = pagarme.simulate_transaction(payment.correlation_id, status="paid", use_local_simulation=True)
        
        if result:
            # Atualizar status do pagamento
            payment.status = PaymentTransaction.Status.PAID
            payment.paid_at = timezone.now()
            payment.save()
            
            # Atualizar status da matrícula
            enrollment = payment.enrollment
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()
            
            messages.success(request, _('Pagamento simulado com sucesso! Matrícula ativada.'))
        else:
            messages.error(request, _('Erro ao simular pagamento. Por favor, tente novamente.'))
    
    except Exception as e:
        logger.exception(f"Erro ao simular pagamento: {str(e)}")
        messages.error(request, _('Erro ao simular pagamento: ') + str(e))
    
    return redirect('payments:card_payment_detail', payment_id=payment_id) 