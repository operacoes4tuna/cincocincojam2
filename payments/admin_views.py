# -*- coding: utf-8 -*-
"""
Views administrativas para gerenciar pagamentos PIX fixos
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from .models import PaymentTransaction
from courses.models import Enrollment

@staff_member_required
def payment_admin_dashboard(request):
    """
    Dashboard administrativo para gerenciar pagamentos PIX fixos.
    """
    # Buscar pagamentos pendentes
    pending_payments = PaymentTransaction.objects.filter(
        status=PaymentTransaction.Status.PENDING,
        payment_method='PIX'
    ).select_related('enrollment', 'enrollment__course', 'enrollment__student').order_by('-created_at')
    
    # Estatísticas
    total_pending = pending_payments.count()
    recent_paid = PaymentTransaction.objects.filter(
        status=PaymentTransaction.Status.PAID,
        payment_method='PIX',
        payment_date__gte=timezone.now().date()
    ).count()
    
    context = {
        'pending_payments': pending_payments[:20],  # Últimos 20
        'total_pending': total_pending,
        'recent_paid': recent_paid,
    }
    
    return render(request, 'payments/admin/pix_fixed_dashboard.html', context)

@staff_member_required
@require_POST
def mark_payment_as_paid(request, payment_id):
    """
    Marca um pagamento como pago manualmente.
    """
    payment = get_object_or_404(PaymentTransaction, id=payment_id)
    
    if payment.status != PaymentTransaction.Status.PENDING:
        messages.error(request, _('Este pagamento não está pendente.'))
        return redirect('payments:admin_pix_dashboard')
    
    try:
        # Marcar como pago
        payment.status = PaymentTransaction.Status.PAID
        payment.payment_date = timezone.now()
        payment.save()
        
        # Ativar matrícula
        enrollment = payment.enrollment
        enrollment.status = Enrollment.Status.ACTIVE
        enrollment.save()
        
        # Log da ação
        print(f"[ADMIN] Pagamento {payment.id} marcado como pago por {request.user.email}")
        
        messages.success(
            request, 
            _('Pagamento #{} marcado como pago. Matrícula de {} ativada.').format(
                payment.id, 
                payment.enrollment.student.get_full_name() or payment.enrollment.student.email
            )
        )
        
        # Se for via AJAX, retornar JSON
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': _('Pagamento marcado como pago com sucesso!')
            })
            
    except Exception as e:
        messages.error(request, _('Erro ao marcar pagamento como pago: {}').format(str(e)))
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return redirect('payments:admin_pix_dashboard')

@staff_member_required
@require_POST
def cancel_payment(request, payment_id):
    """
    Cancela um pagamento pendente.
    """
    payment = get_object_or_404(PaymentTransaction, id=payment_id)
    
    if payment.status != PaymentTransaction.Status.PENDING:
        messages.error(request, _('Este pagamento não está pendente.'))
        return redirect('payments:admin_pix_dashboard')
    
    try:
        # Marcar como cancelado
        payment.status = PaymentTransaction.Status.FAILED
        payment.save()
        
        # Cancelar matrícula
        enrollment = payment.enrollment
        enrollment.status = Enrollment.Status.CANCELLED
        enrollment.save()
        
        # Log da ação
        print(f"[ADMIN] Pagamento {payment.id} cancelado por {request.user.email}")
        
        messages.success(
            request, 
            _('Pagamento #{} cancelado. Matrícula de {} cancelada.').format(
                payment.id, 
                payment.enrollment.student.get_full_name() or payment.enrollment.student.email
            )
        )
        
        # Se for via AJAX, retornar JSON
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': _('Pagamento cancelado com sucesso!')
            })
            
    except Exception as e:
        messages.error(request, _('Erro ao cancelar pagamento: {}').format(str(e)))
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return redirect('payments:admin_pix_dashboard')

@staff_member_required
def search_payments(request):
    """
    Busca pagamentos por diferentes critérios.
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'payments': []})
    
    # Buscar por ID, email do estudante, nome do curso ou código PIX
    payments = PaymentTransaction.objects.filter(
        payment_method='PIX'
    ).select_related('enrollment', 'enrollment__course', 'enrollment__student')
    
    # Filtrar por critérios diferentes
    if query.isdigit():
        # Se for número, buscar por ID
        payments = payments.filter(id=query)
    elif '@' in query:
        # Se contém @, buscar por email
        payments = payments.filter(enrollment__student__email__icontains=query)
    else:
        # Buscar por nome do curso ou estudante
        payments = payments.filter(
            Q(enrollment__course__title__icontains=query) |
            Q(enrollment__student__first_name__icontains=query) |
            Q(enrollment__student__last_name__icontains=query) |
            Q(correlation_id__icontains=query)
        )
    
    # Limitar resultados
    payments = payments[:10]
    
    # Serializar dados
    results = []
    for payment in payments:
        results.append({
            'id': payment.id,
            'amount': str(payment.amount),
            'status': payment.status,
            'created_at': payment.created_at.strftime('%d/%m/%Y %H:%M'),
            'student_name': payment.enrollment.student.get_full_name() or payment.enrollment.student.email,
            'course_title': payment.enrollment.course.title,
            'correlation_id': payment.correlation_id,
        })
    
    return JsonResponse({'payments': results}) 