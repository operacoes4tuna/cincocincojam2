"""
Script para testar a emissão de nota fiscal com RPS - Versão Melhorada
Este script testa a emissão de nota fiscal para uma transação existente
e fornece feedback detalhado sobre o processo.
"""
import os
import sys
import django
import logging
import json
import traceback
from datetime import datetime

# Configurar ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Importar modelos e serviços após configuração do Django
from invoices.services import NFEioService
from invoices.models import Invoice, CompanyConfig
from core.models import User
from payments.models import PaymentTransaction
from django.utils import timezone
from django.conf import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/invoice_test.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("invoice_test")

def check_environment():
    """Verifica se o ambiente está configurado corretamente para testes"""
    logger.info("=== Verificando configurações do ambiente ===")
    
    # Verificar variáveis de ambiente críticas
    if not settings.NFEIO_API_KEY:
        logger.error("NFEIO_API_KEY não está configurada. Defina no arquivo .env")
        return False
    else:
        # Ocultar a chave completa por segurança
        key_sample = settings.NFEIO_API_KEY[:8] + "..." + settings.NFEIO_API_KEY[-4:]
        logger.info(f"NFEIO_API_KEY: {key_sample} (tamanho: {len(settings.NFEIO_API_KEY)})")
    
    if not settings.NFEIO_COMPANY_ID:
        logger.error("NFEIO_COMPANY_ID não está configurada. Defina no arquivo .env")
        return False
    else:
        logger.info(f"NFEIO_COMPANY_ID: {settings.NFEIO_COMPANY_ID}")
    
    # Verificar ambiente
    logger.info(f"NFEIO_ENVIRONMENT: {settings.NFEIO_ENVIRONMENT}")
    if settings.NFEIO_ENVIRONMENT != "Development":
        logger.warning("Atenção: Não está usando ambiente de desenvolvimento! Isso pode gerar notas fiscais reais.")
        confirmation = input("Continuar mesmo assim? (s/N): ").lower()
        if confirmation != 's':
            logger.info("Operação cancelada pelo usuário.")
            return False
    
    logger.info("Verificação de ambiente concluída com sucesso.")
    return True

def find_professor(email=None):
    """Encontra um professor para teste, com opção de especificar email"""
    logger.info("=== Procurando professor para teste ===")
    
    if email:
        try:
            professor = User.objects.get(email=email)
            logger.info(f"Professor encontrado pelo email informado: {professor.username} ({professor.email})")
            return professor
        except User.DoesNotExist:
            logger.warning(f"Professor com email {email} não encontrado. Tentando usar o padrão.")
    
    # Tentar encontrar o professor padrão
    try:
        professor = User.objects.get(email='professor@example.com')
        logger.info(f"Professor padrão encontrado: {professor.username} ({professor.email})")
        return professor
    except User.DoesNotExist:
        logger.warning("Professor padrão não encontrado.")
    
    # Tentar encontrar qualquer professor
    professors = User.objects.filter(user_type="PROFESSOR")
    if professors.exists():
        professor = professors.first()
        logger.info(f"Outro professor encontrado: {professor.username} ({professor.email})")
        return professor
    
    logger.error("Nenhum professor encontrado no sistema.")
    return None

def check_company_config(professor):
    """Verifica a configuração da empresa do professor"""
    logger.info("=== Verificando configuração da empresa ===")
    
    try:
        company_config = CompanyConfig.objects.get(user=professor)
        
        logger.info(f"Configuração encontrada para: {professor.get_full_name() or professor.username}")
        logger.info(f"CNPJ: {company_config.cnpj}")
        logger.info(f"Razão Social: {company_config.razao_social}")
        logger.info(f"Série RPS: {company_config.rps_serie}")
        logger.info(f"Número atual RPS: {company_config.rps_numero_atual}")
        logger.info(f"Lote RPS: {company_config.rps_lote}")
        logger.info(f"Inscrição Municipal: {company_config.inscricao_municipal}")
        logger.info(f"Regime Tributário: {company_config.regime_tributario}")
        
        # Verificar se todos os campos obrigatórios estão preenchidos
        if company_config.is_complete():
            logger.info("A configuração da empresa está completa.")
            return company_config
        else:
            logger.error("A configuração da empresa está incompleta. Verifique os campos obrigatórios.")
            return None
            
    except CompanyConfig.DoesNotExist:
        logger.error(f"O professor {professor.email} não possui configuração de empresa. Configure em /invoices/settings/")
        return None

def find_transaction(professor, transaction_id=None):
    """Encontra uma transação de pagamento paga para o teste"""
    logger.info("=== Procurando transação para teste ===")
    
    if transaction_id:
        # Se um ID específico foi fornecido
        try:
            transaction = PaymentTransaction.objects.get(
                id=transaction_id,
                enrollment__course__professor=professor
            )
            logger.info(f"Transação específica encontrada: ID={transaction.id}, Valor={transaction.amount}")
            
            # Verificar se já existe nota fiscal
            if Invoice.objects.filter(transaction=transaction).exists():
                logger.warning(f"Atenção: A transação já possui uma nota fiscal emitida.")
                invoice = Invoice.objects.filter(transaction=transaction).first()
                logger.info(f"Nota existente: ID={invoice.id}, Status={invoice.status}")
                
                confirmation = input("Continuar e emitir uma nova nota? (s/N): ").lower()
                if confirmation != 's':
                    logger.info("Operação cancelada pelo usuário.")
                    return None
            
            return transaction
        except PaymentTransaction.DoesNotExist:
            logger.warning(f"Transação com ID {transaction_id} não encontrada para o professor. Buscando outras opções.")
    
    # Buscar transações pagas
    transactions = PaymentTransaction.objects.filter(
        enrollment__course__professor=professor,
        status='PAID'
    )
    
    if not transactions.exists():
        logger.error("Não foram encontradas transações para emissão de nota fiscal")
        return None
    
    # Filtrar transações que não possuem nota fiscal
    pending_transactions = []
    for transaction in transactions:
        if not Invoice.objects.filter(transaction=transaction).exists():
            pending_transactions.append(transaction)
    
    if pending_transactions:
        transaction = pending_transactions[0]
        logger.info(f"Transação sem nota fiscal encontrada: ID={transaction.id}, Valor={transaction.amount}")
        return transaction
    
    # Se não encontrou nenhuma sem nota, usar a primeira transação paga
    transaction = transactions.first()
    logger.warning(f"Todas as transações já possuem nota fiscal. Usando a primeira: ID={transaction.id}")
    return transaction

def emit_invoice(transaction):
    """Emite uma nota fiscal para a transação"""
    logger.info("=== Emitindo nota fiscal ===")
    logger.info(f"Transação: ID={transaction.id}, Valor={transaction.amount}")
    
    # Verificar detalhes da transação
    enrollment = transaction.enrollment
    student = enrollment.student
    course = enrollment.course
    
    logger.info(f"Curso: {course.title}")
    logger.info(f"Professor: {course.professor.get_full_name() or course.professor.username}")
    logger.info(f"Aluno: {student.get_full_name() or student.username}")
    
    # Criar nota fiscal
    invoice = Invoice(
        transaction=transaction,
        status='pending'
    )
    
    try:
        invoice.save()
        logger.info(f"Nota fiscal criada: ID={invoice.id}")
        
        # Emitir nota fiscal usando o serviço NFEio
        service = NFEioService()
        
        logger.info("Enviando para emissão de nota fiscal...")
        response = service.emit_invoice(invoice)
        
        if response and isinstance(response, dict) and response.get('error'):
            logger.error(f"Erro na emissão: {response.get('message', 'Erro não especificado')}")
            return False
        
        # Recarregar a invoice para obter dados atualizados
        invoice.refresh_from_db()
        
        logger.info(f"Nota fiscal emitida com sucesso!")
        logger.info(f"Status: {invoice.status}")
        logger.info(f"RPS Série: {invoice.rps_serie}")
        logger.info(f"RPS Número: {invoice.rps_numero}")
        logger.info(f"RPS Lote: {invoice.rps_lote}")
        logger.info(f"External ID: {invoice.external_id}")
        
        # Verificar se há URL do PDF
        if invoice.focus_pdf_url:
            logger.info(f"PDF URL: {invoice.focus_pdf_url}")
        
        # Verificar próximo número de RPS
        company_config = CompanyConfig.objects.get(user=course.professor)
        company_config.refresh_from_db()
        logger.info(f"Próximo número RPS: {company_config.rps_numero_atual}")
        
        return invoice
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Erro ao emitir nota fiscal: {str(e)}")
        logger.debug(f"Traceback:\n{error_traceback}")
        return None

def main():
    """Função principal para testar a emissão de nota fiscal"""
    logger.info("====== TESTE DE EMISSÃO DE NOTA FISCAL ======")
    
    # Verificar ambiente
    if not check_environment():
        logger.error("Verificação de ambiente falhou. Abortando.")
        return False
    
    # Obter argumentos da linha de comando
    professor_email = None
    transaction_id = None
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if '@' in arg:
                professor_email = arg
                logger.info(f"Email do professor especificado: {professor_email}")
            elif arg.isdigit():
                transaction_id = int(arg)
                logger.info(f"ID da transação especificado: {transaction_id}")
    
    # Encontrar professor
    professor = find_professor(professor_email)
    if not professor:
        logger.error("Não foi possível encontrar um professor válido. Abortando.")
        return False
    
    # Verificar configuração da empresa
    company_config = check_company_config(professor)
    if not company_config:
        logger.error("Configuração da empresa inválida. Abortando.")
        return False
    
    # Encontrar transação
    transaction = find_transaction(professor, transaction_id)
    if not transaction:
        logger.error("Não foi possível encontrar uma transação válida. Abortando.")
        return False
    
    # Emitir nota fiscal
    invoice = emit_invoice(transaction)
    if not invoice:
        logger.error("Falha na emissão da nota fiscal.")
        return False
    
    logger.info("====== TESTE CONCLUÍDO COM SUCESSO ======")
    logger.info(f"Nota fiscal ID={invoice.id} emitida para transação ID={transaction.id}")
    
    # Verificar se a nota foi aprovada
    if invoice.status == 'approved':
        logger.info("A nota fiscal foi aprovada automaticamente!")
        if invoice.focus_pdf_url:
            logger.info(f"PDF disponível em: {invoice.focus_pdf_url}")
    else:
        logger.info(f"Status atual da nota: {invoice.status}")
        logger.info("Você pode verificar o status mais tarde através do painel administrativo.")
    
    return True

if __name__ == "__main__":
    # Exibir instruções de uso
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Uso: python test_rps_emission_improved.py [email_do_professor] [id_da_transacao]")
        print("Exemplo: python test_rps_emission_improved.py professor@example.com 123")
        sys.exit(0)
    
    # Executar o teste
    success = main()
    
    if success:
        logger.info("Teste concluído com sucesso!")
        sys.exit(0)
    else:
        logger.error("Teste falhou. Verifique os logs para mais detalhes.")
        sys.exit(1) 