#!/usr/bin/env python
"""
Script para testar a geração de PIX para notas fiscais emitidas
"""
import os
import sys
import django
import json
from datetime import datetime

# Configurar o Django
if __name__ == "__main__":
    sys.path.append('.')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from django.contrib.auth import get_user_model
from invoices.models import Invoice, CompanyConfig
from payments.models import PaymentTransaction, SingleSale
from courses.models import Enrollment, Course
from payments.openpix_service import OpenPixService

User = get_user_model()

def print_header(text):
    print("\n" + "="*60)
    print(f" {text}")
    print("="*60)

def print_step(text):
    print(f"\n→ {text}")

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def test_pix_generation():
    """Testa a geração de PIX para uma nota fiscal"""
    
    print_header("TESTE DE GERAÇÃO DE PIX PARA NOTA FISCAL")
    
    # 1. Buscar uma nota fiscal aprovada
    print_step("Buscando nota fiscal aprovada...")
    
    # Primeiro, tentar encontrar uma nota fiscal aprovada
    approved_invoice = Invoice.objects.filter(
        status__in=['approved', 'issued']
    ).first()
    
    if not approved_invoice:
        print_warning("Nenhuma nota fiscal aprovada encontrada. Buscando qualquer nota fiscal...")
        
        # Se não houver aprovada, buscar qualquer nota fiscal
        approved_invoice = Invoice.objects.first()
        
        if not approved_invoice:
            print_error("Nenhuma nota fiscal encontrada no sistema.")
            return False
    
    print_success(f"Nota fiscal encontrada: ID={approved_invoice.id}, Status={approved_invoice.status}")
    
    # 2. Obter informações da nota fiscal
    print_step("Obtendo informações da nota fiscal...")
    
    invoice_amount = None
    customer_name = None
    customer_email = None
    customer_tax_id = None
    description = None
    
    if approved_invoice.transaction:
        # Para transações de matrícula
        invoice_amount = approved_invoice.transaction.amount
        customer_name = approved_invoice.transaction.enrollment.student.get_full_name() or approved_invoice.transaction.enrollment.student.username
        customer_email = approved_invoice.transaction.enrollment.student.email
        customer_tax_id = getattr(approved_invoice.transaction.enrollment.student, 'cpf', '')
        description = f"Pagamento - {approved_invoice.transaction.enrollment.course.title}"
        print_success(f"Nota fiscal de transação: {description}")
    elif approved_invoice.singlesale:
        # Para vendas avulsas
        invoice_amount = approved_invoice.singlesale.amount
        customer_name = approved_invoice.singlesale.customer_name
        customer_email = approved_invoice.singlesale.customer_email
        customer_tax_id = approved_invoice.singlesale.customer_cpf
        description = f"Pagamento - {approved_invoice.singlesale.description}"
        print_success(f"Nota fiscal de venda avulsa: {description}")
    elif approved_invoice.amount:
        # Para notas diretas
        invoice_amount = approved_invoice.amount
        customer_name = approved_invoice.customer_name
        customer_email = approved_invoice.customer_email
        customer_tax_id = approved_invoice.customer_tax_id
        description = approved_invoice.description
        print_success(f"Nota fiscal direta: {description}")
    
    if not invoice_amount:
        print_error("Não foi possível determinar o valor da nota fiscal.")
        return False
    
    print_success(f"Valor da nota: R$ {invoice_amount}")
    print_success(f"Cliente: {customer_name}")
    print_success(f"Email: {customer_email}")
    
    # 3. Testar geração de PIX
    print_step("Testando geração de PIX...")
    
    try:
        # Inicializar o serviço OpenPix
        openpix_service = OpenPixService()
        
        # Preparar dados para a cobrança PIX
        correlation_id = f"invoice-{approved_invoice.id}-{int(datetime.now().timestamp())}"
        charge_data = {
            'correlationID': correlation_id,
            'value': int(invoice_amount * 100),  # Converter para centavos
            'comment': description or f"Pagamento da Nota Fiscal #{approved_invoice.id}",
            'customer': {
                'name': customer_name or 'Cliente',
                'email': customer_email or '',
                'phone': '',
                'taxID': customer_tax_id or ''
            },
            'expiresIn': 3600,  # 1 hora
            'additionalInfo': [
                {
                    'key': 'Nota Fiscal',
                    'value': f'#{approved_invoice.id}'
                }
            ]
        }
        
        print_step("Enviando requisição para OpenPix...")
        print(f"Dados da cobrança: {json.dumps(charge_data, indent=2, ensure_ascii=False)}")
        
        # Gerar a cobrança PIX
        pix_response = openpix_service.create_charge_dict(charge_data)
        
        print_step("Resposta da OpenPix:")
        print(json.dumps(pix_response, indent=2, ensure_ascii=False))
        
        if pix_response and pix_response.get('brCode'):
            print_success("PIX gerado com sucesso!")
            print(f"QR Code Image: {pix_response.get('qrCodeImage')}")
            print(f"BR Code: {pix_response.get('brCode')[:50]}...") # Mostrar apenas os primeiros 50 caracteres
            print(f"Correlation ID: {correlation_id}")
            print(f"Status: {pix_response.get('status')}")
            return True
        else:
            print_error(f"Erro ao gerar PIX: {pix_response}")
            return False
            
    except Exception as e:
        print_error(f"Exceção ao gerar PIX: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_openpix_service():
    """Testa o serviço OpenPix isoladamente"""
    
    print_header("TESTE ISOLADO DO SERVIÇO OPENPIX")
    
    try:
        # Inicializar o serviço
        print_step("Inicializando OpenPixService...")
        openpix_service = OpenPixService()
        
        print_success(f"Serviço inicializado")
        print(f"URL Base: {openpix_service.BASE_URL}")
        print(f"Ambiente: {'SANDBOX' if openpix_service.is_sandbox else 'PRODUÇÃO'}")
        
        # Dados de teste mínimos
        test_charge_data = {
            'correlationID': f"test-{int(datetime.now().timestamp())}",
            'value': 1000,  # R$ 10,00 em centavos
            'comment': "Teste de geração de PIX",
            'customer': {
                'name': 'Cliente Teste',
                'email': 'teste@exemplo.com',
                'phone': '',
                'taxID': ''
            },
            'expiresIn': 3600,
            'additionalInfo': [
                {
                    'key': 'Teste',
                    'value': 'PIX para nota fiscal'
                }
            ]
        }
        
        print_step("Gerando PIX de teste...")
        response = openpix_service.create_charge_dict(test_charge_data)
        
        print_step("Resposta:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        if response and response.get('brCode'):
            print_success("Teste do serviço OpenPix realizado com sucesso!")
            return True
        else:
            print_error("Falha no teste do serviço OpenPix")
            return False
            
    except Exception as e:
        print_error(f"Erro no teste do serviço: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal do teste"""
    
    print_header("INICIANDO TESTES DE INTEGRAÇÃO PIX + NOTA FISCAL")
    
    # Teste 1: Serviço OpenPix isolado
    test1_success = test_openpix_service()
    
    # Teste 2: Geração de PIX para nota fiscal
    test2_success = test_pix_generation()
    
    # Resultado final
    print_header("RESULTADO DOS TESTES")
    
    if test1_success:
        print_success("✅ Teste do serviço OpenPix: PASSOU")
    else:
        print_error("❌ Teste do serviço OpenPix: FALHOU")
    
    if test2_success:
        print_success("✅ Teste de PIX para nota fiscal: PASSOU")
    else:
        print_error("❌ Teste de PIX para nota fiscal: FALHOU")
    
    if test1_success and test2_success:
        print_success("\n🎉 TODOS OS TESTES PASSARAM! A integração está funcionando.")
        print("\nAgora você pode:")
        print("1. Acessar a lista de vendas avulsas")
        print("2. Encontrar uma nota fiscal emitida/aprovada")
        print("3. Clicar no botão PIX (ícone QR code verde)")
        print("4. Visualizar o QR Code e código PIX gerados")
    else:
        print_error("\n❌ Alguns testes falharam. Verifique as configurações.")
        print("\nVerifique:")
        print("1. Se a variável OPENPIX_TOKEN está configurada")
        print("2. Se há conexão com a internet")
        print("3. Se há notas fiscais no sistema")

if __name__ == "__main__":
    main() 