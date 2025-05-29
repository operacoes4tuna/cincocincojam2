"""
Arquivo de views de teste para forçar a exibição de informações financeiras
"""
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET
from django.shortcuts import render
from django.template.loader import render_to_string

from .db_manager import DatabaseManager

@require_GET
def test_financial_info(request):
    """Rota de teste que força a exibição de informações financeiras"""
    # Inicializa o gerenciador de banco de dados
    db_manager = DatabaseManager()
    
    # Obtém dados financeiros
    revenue_stats = db_manager.get_revenue_stats()
    pending_payments = db_manager.get_pending_payments()
    
    # Formatar as informações de faturamento
    revenue_html = "<h2>📊 Estatísticas de Faturamento</h2>"
    
    if revenue_stats:
        revenue_html += f"""
        <p><strong>Faturamento total</strong>: R$ {float(revenue_stats.get('total_revenue', 0)):.2f}</p>
        <p><strong>Total de transações</strong>: {revenue_stats.get('total_transactions', 0)}</p>
        """
        
        # Informações sobre status
        if 'transactions_by_status' in revenue_stats:
            revenue_html += "<h3>Transações por Status</h3><ul>"
            for status, count in revenue_stats.get('transactions_by_status', {}).items():
                revenue_html += f"<li><strong>{status}</strong>: {count}</li>"
            revenue_html += "</ul>"
    
    # Formatar os pagamentos pendentes
    pending_html = "<h2>⏳ Pagamentos Pendentes</h2>"
    
    if pending_payments:
        count = pending_payments.get('total_count', 0)
        total = pending_payments.get('total_amount', 0)
        
        pending_html += f"""
        <p><strong>Total de pagamentos pendentes</strong>: {count}</p>
        <p><strong>Valor total pendente</strong>: R$ {float(total):.2f}</p>
        """
        
        if count > 0 and 'payments' in pending_payments:
            pending_html += "<h3>Lista de Pagamentos Pendentes</h3>"
            
            for i, payment in enumerate(pending_payments.get('payments', []), 1):
                pending_html += f"""
                <div style="margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                    <h4>{i}. Pagamento #{payment.get('id')}</h4>
                    <p><strong>Aluno</strong>: {payment.get('student_name', 'N/A')} ({payment.get('student_email', 'N/A')})</p>
                    <p><strong>Curso</strong>: {payment.get('course_name', 'N/A')}</p>
                    <p><strong>Valor</strong>: R$ {float(payment.get('amount', 0)):.2f}</p>
                    <p><strong>Data de criação</strong>: {payment.get('created_at', 'N/A')}</p>
                </div>
                """
        else:
            pending_html += "<p><em>Não há pagamentos pendentes no momento.</em></p>"
    
    # Combinando todos os dados
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Informações Financeiras</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3, h4 {{ color: #333; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .section {{ margin-bottom: 30px; padding: 20px; border-radius: 5px; background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Informações Financeiras da Plataforma</h1>
            
            <div class="section">
                {revenue_html}
            </div>
            
            <div class="section">
                {pending_html}
            </div>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html_content)
