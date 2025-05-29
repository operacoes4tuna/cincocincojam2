#!/usr/bin/env python
"""
Script para testar o fluxo completo de emissão de notas fiscais.
Este script não depende do sistema de comandos do Django e pode ser executado diretamente.

Uso:
    python test_nfe_emission.py
"""
import os
import sys
import time
import django

# Configurar o ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Importar modelos e serviços após configurar o ambiente
from django.contrib.auth import get_user_model
from invoices.models import CompanyConfig, Invoice
from invoices.services import NFEioService
from payments.models import PaymentTransaction
from courses.models import Enrollment

User = get_user_model()

# Configurações
EMAIL_PROFESSOR = 'professor@example.com'
TRANSACTION_ID = None  # Deixe None para selecionar automaticamente
INTERVAL_SECONDS = 5
MAX_CHECKS = 12


def print_header(message):
    """Imprime um cabeçalho formatado"""
    print("\n" + "="*80)
    print(message.center(80))
    print("="*80)


def print_success(message):
    """Imprime uma mensagem de sucesso"""
    print(f"\033[92m✅ {message}\033[0m")


def print_error(message):
    """Imprime uma mensagem de erro"""
    print(f"\033[91m❌ {message}\033[0m")


def print_warning(message):
    """Imprime uma mensagem de aviso"""
    print(f"\033[93m⚠️ {message}\033[0m")


def print_info(message):
    """Imprime uma mensagem informativa"""
    print(f"\033[94m📌 {message}\033[0m")


def main():
    """Função principal"""
    print_header("TESTE DE EMISSÃO DE NOTA FISCAL")
    
    try:
        # 1. Obter o professor
        print_info(f"Buscando professor com email {EMAIL_PROFESSOR}...")
        try:
            professor = User.objects.get(email=EMAIL_PROFESSOR)
            print_success(f"Professor encontrado: {professor.get_full_name() or professor.email} (ID: {professor.id})")
        except User.DoesNotExist:
            print_error(f"Professor com email {EMAIL_PROFESSOR} não encontrado.")
            return

        # 2. Verificar se o professor possui configuração fiscal
        print_info("Verificando configuração fiscal...")
        try:
            company_config = CompanyConfig.objects.get(user=professor)
            
            if not company_config.is_complete():
                print_error("Configuração fiscal incompleta. Verifique os dados do professor.")
                return
            
            print_success(f"Configuração fiscal encontrada e válida:")
            print(f"  CNPJ: {company_config.cnpj}")
            print(f"  Razão Social: {company_config.razao_social}")
            print(f"  Nome Fantasia: {company_config.nome_fantasia}")
            print(f"  Regime Tributário: {company_config.regime_tributario}")
        except CompanyConfig.DoesNotExist:
            print_error(f"Professor {EMAIL_PROFESSOR} não possui configuração fiscal.")
            return

        # 3. Buscar ou selecionar uma transação de pagamento
        transaction = None
        if TRANSACTION_ID:
            print_info(f"Buscando transação com ID {TRANSACTION_ID}...")
            try:
                transaction = PaymentTransaction.objects.get(id=TRANSACTION_ID)
            except PaymentTransaction.DoesNotExist:
                print_error(f"Transação com ID {TRANSACTION_ID} não encontrada.")
                return
        else:
            print_info("Buscando transações disponíveis do professor...")
            # Buscar matrículas em cursos do professor
            enrollments = Enrollment.objects.filter(
                course__professor=professor,
                status='ACTIVE'  # O status é em maiúsculas no banco de dados
            ).select_related('course', 'student')
            
            if not enrollments.exists():
                print_error("Nenhuma matrícula paga encontrada para o professor.")
                return
            
            # Buscar transações das matrículas
            transactions = PaymentTransaction.objects.filter(
                enrollment__in=enrollments,
                status='PAID'  # O status é em maiúsculas no banco de dados
            ).order_by('-created_at')
            
            if not transactions.exists():
                print_error("Nenhuma transação aprovada encontrada para o professor.")
                return
            
            # Selecionar a transação mais recente que ainda não tem nota fiscal
            for tx in transactions:
                if not Invoice.objects.filter(transaction=tx).exists():
                    transaction = tx
                    break
            
            if not transaction:
                transaction = transactions.first()
                print_warning("Todas as transações já possuem notas fiscais. Usando a mais recente.")
        
        # Mostrar detalhes da transação
        print_success(f"Transação selecionada:")
        print(f"  ID: {transaction.id}")
        print(f"  Valor: R$ {transaction.amount:.2f}")
        print(f"  Data: {transaction.created_at}")
        print(f"  Curso: {transaction.enrollment.course.title}")
        print(f"  Aluno: {transaction.enrollment.student.get_full_name() or transaction.enrollment.student.email}")

        # 4. Criar objeto Invoice
        print_info("Criando registro de nota fiscal...")
        
        # Verificar se já existe uma nota para esta transação
        existing_invoice = Invoice.objects.filter(transaction=transaction).first()
        if existing_invoice:
            print_warning(f"Já existe uma nota fiscal para esta transação (ID: {existing_invoice.id}, Status: {existing_invoice.status}).")
            invoice = existing_invoice
            if invoice.status in ['approved', 'cancelled']:
                print_info("A nota fiscal existente já está finalizada. Criando uma nova...")
                # Criar nova nota para a mesma transação para fins de teste
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

        # 5. Iniciar processo de emissão da nota fiscal
        print_info("Iniciando processo de emissão...")
        service = NFEioService()
        
        # Emitir a nota
        print_warning("EMITINDO NOTA FISCAL...")
        emission_result = service.emit_invoice(invoice)
        
        if emission_result.get('error'):
            print_error(f"Erro na emissão: {emission_result.get('message')}")
            return
        
        print_success("Nota fiscal enviada para processamento!")
        print(f"  ID Externo: {invoice.external_id}")
        print(f"  Status: {invoice.status}")
        print(f"  Status API: {invoice.focus_status}")
        
        # 6. Acompanhar o status até finalizar ou atingir o limite de verificações
        print_info(f"Acompanhando status da nota fiscal a cada {INTERVAL_SECONDS} segundos...")
        
        check_count = 0
        while check_count < MAX_CHECKS:
            check_count += 1
            print(f"Verificação {check_count}/{MAX_CHECKS}...")
            
            # Esperar pelo intervalo configurado
            time.sleep(INTERVAL_SECONDS)
            
            # Verificar status
            print("Verificando status atual...")
            status_result = service.check_invoice_status(invoice)
            
            # Recarregar o objeto invoice para ter os dados mais atualizados
            invoice.refresh_from_db()
            
            # Mostrar status atual
            print(f"  Status atual: {invoice.status}")
            print(f"  Status API: {invoice.focus_status}")
            
            # Verificar se já finalizou o processamento
            if invoice.status in ['approved', 'cancelled', 'error']:
                break
        
        # 7. Exibir resultado final
        print_header("RESULTADO FINAL DA EMISSÃO")
        invoice.refresh_from_db()
        
        if invoice.status == 'approved':
            print_success("NOTA FISCAL EMITIDA COM SUCESSO!")
        elif invoice.status == 'error':
            print_error(f"ERRO NA EMISSÃO: {invoice.error_message}")
        elif invoice.status == 'cancelled':
            print_warning("NOTA FISCAL CANCELADA")
        else:
            print_warning(f"NOTA FISCAL AINDA EM PROCESSAMENTO (Status: {invoice.status}, API Status: {invoice.focus_status})")
        
        print("\nDetalhes da nota fiscal:")
        print(f"  ID: {invoice.id}")
        print(f"  ID Externo (NFE.io): {invoice.external_id}")
        print(f"  Status interno: {invoice.status}")
        print(f"  Status API: {invoice.focus_status}")
        print(f"  Criada em: {invoice.created_at}")
        print(f"  Atualizada em: {invoice.updated_at}")
        
        if invoice.focus_pdf_url:
            print(f"  PDF: {invoice.focus_pdf_url}")
        if invoice.focus_xml_url:
            print(f"  XML: {invoice.focus_xml_url}")
        
        if invoice.error_message:
            print(f"\nMensagem de erro: {invoice.error_message}")
        
    except Exception as e:
        print_error(f"Erro inesperado: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
