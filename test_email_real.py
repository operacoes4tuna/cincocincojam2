import os
import django
import logging

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from invoices.models import Invoice
from invoices.email_service import EmailService

# Configurar logging para ver os detalhes
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_email_with_pdf():
    """
    Testa o envio real de email com as melhorias implementadas
    """
    print("🧪 TESTE DE ENVIO REAL DE EMAIL COM PDF")
    print("=" * 60)
    
    # Buscar uma nota fiscal aprovada
    invoices = Invoice.objects.filter(
        status='approved',
        focus_pdf_url__isnull=False
    ).order_by('-created_at')[:3]
    
    if not invoices.exists():
        print("❌ Nenhuma nota fiscal aprovada com PDF encontrada")
        return
    
    print(f"📋 Notas fiscais disponíveis:")
    for i, invoice in enumerate(invoices, 1):
        print(f"  {i}. Invoice #{invoice.id} - External ID: {invoice.external_id}")
        print(f"     Status: {invoice.status}")
        print(f"     PDF: {'✅ Disponível' if invoice.focus_pdf_url else '❌ Não'}")
    
    # Escolher a primeira
    invoice = invoices.first()
    print(f"\n🎯 Usando Invoice #{invoice.id}")
    
    # Pedir email de destino
    email_destino = input("\n📧 Digite o email de destino: ").strip()
    if not email_destino:
        print("❌ Email não informado")
        return
    
    # Inicializar serviço
    email_service = EmailService()
    
    print(f"\n📤 Enviando email para {email_destino}...")
    print("🔍 Acompanhe os logs detalhados abaixo:")
    print("-" * 60)
    
    # Enviar email
    result = email_service.send_invoice_email(
        invoice, 
        email_destino, 
        "Email de teste com PDF anexado - CincoCincoJAM"
    )
    
    print("-" * 60)
    print(f"\n📊 RESULTADO:")
    
    if result['success']:
        print(f"✅ SUCESSO: {result['message']}")
        print("📧 Verifique sua caixa de entrada")
        print("📎 O PDF deve estar anexado se tudo funcionou corretamente")
    else:
        print(f"❌ FALHA: {result['message']}")
        print("🔧 Verifique os logs acima para identificar o problema")

if __name__ == "__main__":
    test_email_with_pdf() 