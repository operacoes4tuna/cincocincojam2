import os
import json
import logging
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from payments.models import PaymentTransaction
from invoices.models import Invoice, CompanyConfig
from invoices.services import NFEioService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def print_header(text):
    """Imprime um cabeçalho formatado"""
    print("\n" + "="*80)
    print(f" {text} ".center(80, "="))
    print("="*80 + "\n")

def print_step(text):
    """Imprime um passo do processo"""
    print(f"\n>>> {text}")

def print_success(text):
    """Imprime uma mensagem de sucesso"""
    print(f"\n✅ {text}")

def print_error(text):
    """Imprime uma mensagem de erro"""
    print(f"\n❌ {text}")

def print_info(text):
    """Imprime uma mensagem informativa"""
    print(f"\nℹ️ {text}")

def print_warning(text):
    """Imprime uma mensagem de aviso"""
    print(f"\n⚠️ {text}")

def test_invoice_emission():
    """Testa a emissão de uma nota fiscal"""
    print_header("TESTE DE EMISSÃO DE NOTA FISCAL")
    
    # 1. Verificar se existe uma transação de teste
    print_step("Buscando transação de teste...")
    try:
        transaction = PaymentTransaction.objects.filter(status='approved').first()
        if not transaction:
            print_error("Nenhuma transação aprovada encontrada para teste")
            return False
    except Exception as e:
        print_error(f"Erro ao buscar transação: {str(e)}")
        return False
    
    print_success(f"Transação encontrada:")
    print(f"  ID: {transaction.id}")
    print(f"  Valor: R$ {transaction.amount:.2f}")
    print(f"  Data: {transaction.created_at}")
    print(f"  Curso: {transaction.enrollment.course.title}")
    print(f"  Aluno: {transaction.enrollment.student.get_full_name() or transaction.enrollment.student.email}")
    
    # 2. Verificar configuração RPS do professor
    print_step("Verificando configuração RPS do professor...")
    professor = transaction.enrollment.course.professor
    try:
        company_config = CompanyConfig.objects.get(user=professor)
        print_success("Configuração RPS encontrada:")
        print(f"  Série RPS: {company_config.rps_serie}")
        print(f"  Número atual RPS: {company_config.rps_numero_atual}")
        print(f"  Lote RPS: {company_config.rps_lote}")
    except CompanyConfig.DoesNotExist:
        print_error("O professor não possui configuração de empresa")
        return False
    
    # 3. Criar nota fiscal
    print_step("Criando registro de nota fiscal...")
    try:
        # Verificar se já existe uma nota para esta transação
        existing_invoice = Invoice.objects.filter(transaction=transaction).first()
        if existing_invoice:
            print_warning(
                f"Já existe uma nota fiscal para esta transação "
                f"(ID: {existing_invoice.id}, Status: {existing_invoice.status})"
            )
            invoice = existing_invoice
            if invoice.status in ['approved', 'cancelled']:
                print_info("A nota fiscal existente já está finalizada. Criando uma nova...")
                invoice = Invoice.objects.create(
                    transaction=transaction,
                    status='pending'
                )
        else:
            invoice = Invoice.objects.create(
                transaction=transaction,
                status='pending'
            )
        
        print_success(f"Nota fiscal criada/selecionada com ID: {invoice.id}")
    except Exception as e:
        print_error(f"Erro ao criar nota fiscal: {str(e)}")
        return False
    
    # 4. Emitir nota fiscal
    print_step("Iniciando processo de emissão...")
    try:
        service = NFEioService()
        print_info("EMITINDO NOTA FISCAL...")
        emission_result = service.emit_invoice(invoice)
        
        if emission_result.get('error'):
            print_error(f"Erro na emissão: {emission_result.get('message')}")
            return False
        
        print_success("Nota fiscal enviada para processamento!")
        print(f"  ID Externo: {invoice.external_id}")
        print(f"  Status: {invoice.status}")
        
        # 5. Verificar status após alguns segundos
        print_step("Verificando status da emissão...")
        timezone.sleep(5)  # Aguardar 5 segundos
        status_result = service.check_invoice_status(invoice)
        
        if status_result.get('error'):
            print_error(f"Erro ao verificar status: {status_result.get('message')}")
        else:
            print_success(f"Status atual: {invoice.status}")
            if invoice.focus_pdf_url:
                print(f"  PDF URL: {invoice.focus_pdf_url}")
            if invoice.focus_xml_url:
                print(f"  XML URL: {invoice.focus_xml_url}")
        
        return True
        
    except Exception as e:
        print_error(f"Erro durante a emissão: {str(e)}")
        return False

if __name__ == "__main__":
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cincocincojam2.settings')
    import django
    django.setup()
    
    # Executar teste
    test_invoice_emission() 