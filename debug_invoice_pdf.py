import os
import django
import logging

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from invoices.models import Invoice
from invoices.email_service import EmailService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def debug_invoice_pdf():
    """
    Debug específico para verificar PDF de uma nota fiscal
    """
    print("🔍 DEBUG DE PDF - NOTA FISCAL ESPECÍFICA")
    print("=" * 60)
    
    # Listar notas fiscais recentes
    invoices = Invoice.objects.filter(
        status__in=['approved', 'processing', 'issued']
    ).order_by('-created_at')[:10]
    
    if not invoices.exists():
        print("❌ Nenhuma nota fiscal encontrada")
        return
    
    print("📋 Notas fiscais disponíveis:")
    for i, invoice in enumerate(invoices, 1):
        status_icon = "✅" if invoice.status == 'approved' else "⚠️"
        pdf_icon = "📎" if invoice.focus_pdf_url else "❌"
        external_icon = "🔗" if invoice.external_id else "❌"
        
        print(f"  {i}. {status_icon} Invoice #{invoice.id}")
        print(f"     Status: {invoice.status}")
        print(f"     {external_icon} External ID: {invoice.external_id}")
        print(f"     {pdf_icon} PDF URL: {'Sim' if invoice.focus_pdf_url else 'Não'}")
        if invoice.focus_pdf_url:
            print(f"     🌐 URL: {invoice.focus_pdf_url[:80]}...")
        print()
    
    # Pedir ID da nota fiscal
    try:
        invoice_id = int(input("📝 Digite o ID da nota fiscal para debug: "))
        invoice = Invoice.objects.get(id=invoice_id)
    except (ValueError, Invoice.DoesNotExist):
        print("❌ Nota fiscal não encontrada")
        return
    
    print(f"\n🎯 DEBUGANDO INVOICE #{invoice.id}")
    print("-" * 40)
    
    # Mostrar detalhes
    print(f"📊 DETALHES DA NOTA FISCAL:")
    print(f"   ID: {invoice.id}")
    print(f"   External ID: {invoice.external_id}")
    print(f"   Status: {invoice.status}")
    print(f"   Focus Status: {invoice.focus_status}")
    print(f"   Focus PDF URL: {invoice.focus_pdf_url}")
    print(f"   Created: {invoice.created_at}")
    print(f"   Updated: {invoice.updated_at}")
    
    # Testar EmailService
    print(f"\n🔧 TESTANDO EMAIL SERVICE:")
    email_service = EmailService()
    
    print(f"   NFE.io API Key: {'✅ Configurada' if email_service.nfeio_api_key else '❌ Não configurada'}")
    print(f"   NFE.io Company ID: {email_service.nfeio_company_id}")
    print(f"   SendGrid API Key: {'✅ Configurada' if email_service.api_key else '❌ Não configurada'}")
    
    # Testar busca de PDF
    print(f"\n📎 TESTANDO BUSCA DE PDF:")
    
    # Teste 1: API NFE.io
    if invoice.external_id and email_service.nfeio_api_key:
        print("🔍 Teste 1: Buscar PDF na API NFE.io...")
        pdf_content = email_service.get_pdf_from_nfeio_api(invoice)
        if pdf_content:
            print(f"✅ SUCESSO: PDF encontrado na API ({len(pdf_content)} bytes)")
        else:
            print("❌ FALHA: PDF não encontrado na API")
    else:
        print("⚠️ Teste 1 IGNORADO: External ID ou credenciais não disponíveis")
    
    # Teste 2: Focus PDF URL
    if invoice.focus_pdf_url:
        print("🔍 Teste 2: Download da focus_pdf_url...")
        try:
            import requests
            session = requests.Session()
            session.verify = False
            
            headers = {}
            if email_service.nfeio_api_key:
                headers['Authorization'] = f'Basic {email_service.nfeio_api_key}'
            
            response = session.get(invoice.focus_pdf_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                content = response.content
                if content and content.startswith(b'%PDF'):
                    print(f"✅ SUCESSO: PDF baixado da URL ({len(content)} bytes)")
                else:
                    print(f"❌ FALHA: URL não retorna PDF válido ({len(content)} bytes)")
            else:
                print(f"❌ FALHA: Status HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ ERRO: {str(e)}")
    else:
        print("⚠️ Teste 2 IGNORADO: focus_pdf_url não disponível")
    
    # Teste 3: Protocolo forçado completo
    print("🔍 Teste 3: Protocolo forçado completo...")
    attachment = email_service.force_pdf_attachment(invoice)
    if attachment:
        print("🎉 SUCESSO: Anexo criado com protocolo forçado!")
    else:
        print("❌ FALHA: Protocolo forçado não funcionou")
    
    # Resumo final
    print(f"\n📊 RESUMO:")
    has_external_id = bool(invoice.external_id)
    has_pdf_url = bool(invoice.focus_pdf_url)
    has_credentials = bool(email_service.nfeio_api_key)
    
    print(f"   External ID: {'✅' if has_external_id else '❌'}")
    print(f"   PDF URL: {'✅' if has_pdf_url else '❌'}")
    print(f"   Credenciais: {'✅' if has_credentials else '❌'}")
    
    can_attach = attachment is not None
    print(f"\n🎯 RESULTADO: {'✅ PDF PODE SER ANEXADO' if can_attach else '❌ PDF NÃO PODE SER ANEXADO'}")

if __name__ == "__main__":
    debug_invoice_pdf() 