"""
Módulo para acesso direto ao banco de dados sem restrições
Este módulo permite consultas diretas sem passar pelo OpenAI
"""
from django.db.models import Q, Count, Sum
from core.models import User
from courses.models import Course, Enrollment
from payments.models import PaymentTransaction

def format_financial_data():
    """
    Formata todos os dados financeiros em um único texto
    
    Returns:
        String formatada com dados financeiros
    """
    # Buscar receita total
    total_revenue = PaymentTransaction.objects.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Contar transações por status
    transactions_by_status = {
        'PAID': PaymentTransaction.objects.filter(status='PAID').count(),
        'PENDING': PaymentTransaction.objects.filter(status='PENDING').count(),
        'CANCELLED': PaymentTransaction.objects.filter(status='CANCELLED').count(),
        'REFUNDED': PaymentTransaction.objects.filter(status='REFUNDED').count(),
    }
    
    # Buscar o melhor cliente (que mais gastou)
    best_customer = User.objects.annotate(
        total_spent=Sum('paymenttransaction__amount', filter=Q(paymenttransaction__status='PAID'))
    ).filter(total_spent__gt=0).order_by('-total_spent').first()
    
    # Formatar o texto compacto
    result = f"# 📊 Relatório Financeiro Completo\n"
    
    # Estatísticas de receita
    result += f"**Faturamento total**: R$ {float(total_revenue):.2f} | "
    result += f"**Transações pagas**: {transactions_by_status['PAID']} | "
    result += f"**Pendentes**: {transactions_by_status['PENDING']} | "
    result += f"**Canceladas/Reembolsadas**: {transactions_by_status['CANCELLED'] + transactions_by_status['REFUNDED']}\n\n"
    
    # Melhor cliente
    if best_customer:
        customer_transactions = PaymentTransaction.objects.filter(user=best_customer, status='PAID')
        result += f"### 👑 Melhor Cliente\n"
        result += f"**Nome**: {best_customer.get_full_name() or best_customer.username} | "
        result += f"**Email**: {best_customer.email} | "
        result += f"**Valor gasto**: R$ {float(best_customer.total_spent):.2f} | "
        result += f"**Compras**: {customer_transactions.count()}\n\n"
    
    # Pagamentos pendentes
    pending_payments = PaymentTransaction.objects.filter(status='PENDING').order_by('-created_at')
    if pending_payments.exists():
        result += f"### ⏳ Pagamentos Pendentes ({pending_payments.count()})\n"
        
        for i, payment in enumerate(pending_payments[:10], 1):
            student_name = "N/A"
            course_name = "N/A"
            
            if payment.user:
                student_name = payment.user.get_full_name() or payment.user.username
            
            if hasattr(payment, 'enrollment') and payment.enrollment and payment.enrollment.course:
                course_name = payment.enrollment.course.title
            
            result += f"**{i}.** {student_name} | Curso: {course_name} | "
            result += f"Valor: R$ {float(payment.amount):.2f} | "
            result += f"Data: {payment.created_at.strftime('%d/%m/%Y')}\n"
            
        if pending_payments.count() > 10:
            result += f"_...e mais {pending_payments.count() - 10} pagamentos pendentes_\n\n"
    
    # Últimos pagamentos recebidos
    recent_payments = PaymentTransaction.objects.filter(status='PAID').order_by('-created_at')[:5]
    if recent_payments.exists():
        result += f"### 💰 Últimos Pagamentos Recebidos\n"
        
        for i, payment in enumerate(recent_payments, 1):
            student_name = "N/A"
            course_name = "N/A"
            
            if payment.user:
                student_name = payment.user.get_full_name() or payment.user.username
            
            if hasattr(payment, 'enrollment') and payment.enrollment and payment.enrollment.course:
                course_name = payment.enrollment.course.title
            
            result += f"**{i}.** {student_name} | Curso: {course_name} | "
            result += f"Valor: R$ {float(payment.amount):.2f} | "
            result += f"Data: {payment.created_at.strftime('%d/%m/%Y')}\n"
    
    return result

def get_best_client_info():
    """
    Retorna informações detalhadas sobre o melhor cliente
    
    Returns:
        String formatada com dados do melhor cliente
    """
    # Buscar o melhor cliente (que mais gastou)
    best_customer = User.objects.annotate(
        total_spent=Sum('paymenttransaction__amount', filter=Q(paymenttransaction__status='PAID'))
    ).filter(total_spent__gt=0).order_by('-total_spent').first()
    
    if not best_customer:
        return "Não foi possível identificar o melhor cliente. Não há registros de pagamentos."
    
    # Buscar todas as compras do cliente
    customer_purchases = PaymentTransaction.objects.filter(
        user=best_customer, 
        status='PAID'
    ).order_by('-created_at')
    
    # Formatar resposta
    result = f"# 👑 Melhor Cliente: {best_customer.get_full_name() or best_customer.username}\n\n"
    result += f"**Email**: {best_customer.email}\n"
    result += f"**Valor total gasto**: R$ {float(best_customer.total_spent):.2f}\n"
    result += f"**Total de compras**: {customer_purchases.count()}\n"
    result += f"**Data de cadastro**: {best_customer.date_joined.strftime('%d/%m/%Y')}\n\n"
    
    # Listar todas as compras
    if customer_purchases.exists():
        result += "### Histórico de Compras\n"
        
        for i, purchase in enumerate(customer_purchases, 1):
            course_name = "N/A"
            if hasattr(purchase, 'enrollment') and purchase.enrollment and purchase.enrollment.course:
                course_name = purchase.enrollment.course.title
                
            result += f"**{i}.** {course_name} | "
            result += f"Valor: R$ {float(purchase.amount):.2f} | "
            result += f"Data: {purchase.created_at.strftime('%d/%m/%Y')}\n"
    
    return result
