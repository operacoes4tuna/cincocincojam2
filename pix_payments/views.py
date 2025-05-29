from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.translation import gettext as _
from django.conf import settings

from .openpix_service import OpenPixService
from .models import Payment
from courses.models import Course, Enrollment

@login_required
def create_pix_payment(request, course_id):
    """
    Cria uma cobrança Pix para o curso selecionado
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Verificar se o usuário já está matriculado
    if Enrollment.objects.filter(student=request.user, course=course).exists():
        messages.warning(request, _('Você já está matriculado neste curso.'))
        return redirect('courses:course_detail', pk=course.id)
    
    # Verificar se já existe um pagamento pendente
    existing_payment = Payment.objects.filter(
        user=request.user, 
        course=course, 
        status='PENDING'
    ).first()
    
    if existing_payment:
        return redirect('pix_payments:payment_detail', payment_id=existing_payment.id)
    
    # Criar cobrança na OpenPix
    openpix = OpenPixService()
    try:
        charge_data = openpix.create_charge(course, request.user)
        
        # Salvar informações do pagamento
        payment = Payment.objects.create(
            user=request.user,
            course=course,
            amount=course.price,
            correlation_id=charge_data.get('correlationID'),
            brcode=charge_data.get('brCode'),
            qrcode_image=charge_data.get('qrCodeImage')
        )
        
        return redirect('pix_payments:payment_detail', payment_id=payment.id)
    except Exception as e:
        messages.error(request, _('Erro ao gerar cobrança Pix. Por favor, tente novamente.'))
        return redirect('courses:course_detail', pk=course.id)

@login_required
def payment_detail(request, payment_id):
    """
    Exibe os detalhes do pagamento e o QR Code para o usuário
    """
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Atualizar status do pagamento
    if payment.status == 'PENDING':
        try:
            openpix = OpenPixService()
            status_data = openpix.get_charge_status(payment.correlation_id)
            
            if status_data.get('status') == 'COMPLETED':
                payment.status = 'COMPLETED'
                payment.save()
                
                # Criar matrícula após pagamento confirmado
                Enrollment.objects.create(
                    student=payment.user,
                    course=payment.course,
                    status='ACTIVE'
                )
                
                messages.success(request, _('Pagamento confirmado! Você foi matriculado no curso.'))
                return redirect('courses:my_courses')
        except Exception:
            pass  # Continuar exibindo a página normalmente
    
    return render(request, 'pix_payments/payment_detail.html', {
        'payment': payment,
        'course': payment.course
    })

@csrf_exempt
@require_POST
def webhook(request):
    """
    Webhook para receber notificações da OpenPix
    """
    # Aqui implementaremos a lógica do webhook mais tarde
    return HttpResponse(status=200)
