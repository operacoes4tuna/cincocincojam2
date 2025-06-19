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

def test_pdf_attachment():
    """
    Testa a funcionalidade de anexo de PDF em emails
    """
    print("🧪 TESTE DE ANEXO DE PDF EM EMAILS")
    print("=" * 50)
    
    # Buscar uma nota fiscal aprovada para teste
    invoices = Invoice.objects.filter(
        status='approved',
        focus_pdf_url__isnull=False
    ).order_by('-created_at')[:5]
    
    if not invoices.exists():
        print("❌ Nenhuma nota fiscal aprovada encontrada para teste")
        print("💡 Dica: Emita uma nota fiscal primeiro")
        return
    
    print(f"📋 Encontradas {invoices.count()} notas fiscais para teste:")
    for i, invoice in enumerate(invoices, 1):
        print(f"  {i}. Invoice #{invoice.id} - Status: {invoice.status} - External ID: {invoice.external_id}")
        if invoice.focus_pdf_url:
            print(f"     PDF URL: {invoice.focus_pdf_url[:100]}...")
    
    # Usar a primeira nota fiscal
    invoice = invoices.first()
    print(f"\n🎯 Testando com Invoice #{invoice.id}")
    
    # Inicializar o serviço de email
    email_service = EmailService()
    
    # Debug detalhado do processo
    print("\n🔍 EXECUTANDO DEBUG DETALHADO:")
    success = email_service.debug_pdf_attachment(invoice)
    
    if success:
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("📎 O PDF pode ser anexado aos emails")
        
        # Perguntar se quer testar envio real
        test_email = input("\n📧 Deseja testar o envio real de email? (s/N): ").lower().strip()
        if test_email == 's':
            recipient = input("📧 Digite o email de destino: ").strip()
            if recipient:
                print(f"\n📧 Enviando email de teste para {recipient}...")
                result = email_service.send_invoice_email(
                    invoice, 
                    recipient, 
                    "Teste de anexo de PDF - CincoCincoJAM"
                )
                
                if result['success']:
                    print("✅ Email enviado com sucesso!")
                    print("📎 Verifique se o PDF foi anexado corretamente")
                else:
                    print(f"❌ Erro ao enviar email: {result['message']}")
    else:
        print("\n❌ TESTE FALHOU!")
        print("🔧 Verifique os logs acima para identificar o problema")
        
        # Sugestões de solução
        print("\n💡 POSSÍVEIS SOLUÇÕES:")
        print("1. Verificar se as credenciais da NFE.io estão corretas")
        print("2. Verificar se a URL do PDF está acessível")
        print("3. Verificar conectividade com a internet")
        print("4. Verificar se a nota fiscal está realmente aprovada")

if __name__ == "__main__":
    test_pdf_attachment() 