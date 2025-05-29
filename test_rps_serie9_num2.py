"""
Script para testar a emissão de nota fiscal com valores específicos de RPS
Série: 9
Número: 2
"""
import os
import sys
import django
import logging
import json
from decimal import Decimal
from datetime import datetime

# Configurar ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Importar modelos e serviços após configuração do Django
from invoices.services import NFEioService
from invoices.models import Invoice, CompanyConfig
from core.models import User
from payments.models import PaymentTransaction
from courses.models import Course, Enrollment
from django.utils import timezone
from django.db import transaction

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_rps_config(serie="9", numero=2, lote=1):
    """
    Atualiza a configuração de RPS com os valores específicos
    """
    try:
        professor = User.objects.get(email='professor@example.com')
        company_config = CompanyConfig.objects.get(user=professor)
        
        company_config.rps_serie = serie
        company_config.rps_numero_atual = numero
        company_config.rps_lote = lote
        company_config.save()
        
        logger.info("=== CONFIGURAÇÃO RPS ATUALIZADA ===")
        logger.info(f"Série RPS: '{company_config.rps_serie}'")
        logger.info(f"Número atual RPS: {company_config.rps_numero_atual}")
        logger.info(f"Lote RPS: {company_config.rps_lote}")
        
        return company_config
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração: {str(e)}")
        return None

def create_test_transaction():
    """
    Cria uma transação de teste para um curso existente
    """
    # Buscar usuários para o teste
    try:
        professor = User.objects.get(email='professor@example.com')
        student = User.objects.get(email='aluno@example.com')
        logger.info(f"Professor: {professor.username}")
        logger.info(f"Aluno: {student.username}")
    except User.DoesNotExist:
        logger.error("Usuários não encontrados. Verifique se os usuários padrão foram criados.")
        return None
    
    # Buscar um curso do professor
    try:
        course = Course.objects.filter(professor=professor).first()
        if not course:
            logger.error("Nenhum curso encontrado para o professor")
            return None
        logger.info(f"Curso selecionado: {course.title}, preço: {course.price}")
    except Exception as e:
        logger.error(f"Erro ao buscar curso: {str(e)}")
        return None
    
    # Criar uma matrícula se não existir
    enrollment, created = Enrollment.objects.get_or_create(
        student=student,
        course=course,
        defaults={
            'status': 'active',
            'enrolled_at': timezone.now()
        }
    )
    
    if created:
        logger.info(f"Nova matrícula criada para o curso '{course.title}'")
    else:
        logger.info(f"Matrícula existente encontrada para o curso '{course.title}'")
    
    # Criar uma transação de pagamento
    with transaction.atomic():
        payment = PaymentTransaction.objects.create(
            enrollment=enrollment,
            amount=course.price or Decimal('99.90'),
            payment_method='credit_card',
            status='PAID',
            payment_date=timezone.now(),
            transaction_id=f"TEST-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        )
        logger.info(f"Transação de pagamento criada: ID={payment.id}, Valor={payment.amount}")
        
        return payment

def emit_invoice_for_transaction(transaction_id):
    """
    Emite uma nota fiscal para uma transação específica
    """
    # Buscar a transação
    try:
        transaction = PaymentTransaction.objects.get(id=transaction_id)
        logger.info(f"Transação encontrada: ID={transaction.id}, Valor={transaction.amount}")
    except PaymentTransaction.DoesNotExist:
        logger.error(f"Transação não encontrada: ID={transaction_id}")
        return False
    
    # Verificar se já existe nota fiscal
    if Invoice.objects.filter(transaction=transaction).exists():
        logger.error(f"Já existe uma nota fiscal para esta transação")
        return False
    
    professor = transaction.enrollment.course.professor
    
    # Verificar configuração RPS do professor
    try:
        company_config = CompanyConfig.objects.get(user=professor)
        logger.info(f"Configuração da empresa encontrada")
        logger.info(f"Série RPS: '{company_config.rps_serie}'")
        logger.info(f"Número atual RPS: {company_config.rps_numero_atual}")
        logger.info(f"Lote RPS: {company_config.rps_lote}")
    except CompanyConfig.DoesNotExist:
        logger.error("O professor não possui configuração de empresa. Configure em /invoices/settings/")
        return False
    
    # Criar nota fiscal
    invoice = Invoice(
        transaction=transaction,
        status='pending'
    )
    invoice.save()
    logger.info(f"Nota fiscal criada: ID={invoice.id}")
    
    # Emitir nota fiscal usando o serviço NFEio
    service = NFEioService()
    try:
        logger.info("Emitindo nota fiscal...")
        response = service.emit_invoice(invoice)
        
        if response.get('error'):
            logger.error(f"Erro na emissão: {response.get('message')}")
            return False
        
        # Recarregar a invoice para obter dados atualizados
        invoice.refresh_from_db()
        
        logger.info(f"Nota fiscal emitida com sucesso!")
        logger.info(f"Status: {invoice.status}")
        logger.info(f"RPS Série: '{invoice.rps_serie}'")
        logger.info(f"RPS Número: {invoice.rps_numero}")
        logger.info(f"RPS Lote: {invoice.rps_lote}")
        logger.info(f"External ID: {invoice.external_id}")
        
        # Verificar próximo número de RPS
        company_config.refresh_from_db()
        logger.info(f"Próximo número RPS: {company_config.rps_numero_atual}")
        
        # Verificar status 30 segundos depois
        logger.info("Verificando status após 30 segundos...")
        import time
        time.sleep(30)
        
        # Verificar status novamente
        verify_response = service.check_invoice_status(invoice)
        if verify_response.get('error'):
            logger.error(f"Erro na verificação após espera: {verify_response.get('message')}")
        else:
            logger.info(f"Status após 30s: {invoice.status}")
            logger.info(f"Verificação OK!")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao emitir nota fiscal: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== Teste de Emissão de Nota Fiscal com Valores Específicos de RPS ===")
    logger.info("Série: 9, Número: 2")
    
    # Atualizar configuração RPS para os valores especificados
    config = update_rps_config(serie="9", numero=2, lote=1)
    
    if config:
        # Criar transação de teste
        logger.info("\n=== Criando transação de teste ===")
        transaction = create_test_transaction()
        
        if transaction:
            logger.info(f"Transação criada com sucesso: ID={transaction.id}")
            
            # Emitir nota fiscal para a transação
            logger.info("\n=== Emitindo nota fiscal ===")
            result = emit_invoice_for_transaction(transaction.id)
            
            if result:
                logger.info("Nota fiscal emitida com sucesso!")
            else:
                logger.error("Falha ao emitir nota fiscal. Verifique os logs.")
        else:
            logger.error("Falha ao criar transação de teste.")
    else:
        logger.error("Não foi possível atualizar a configuração de RPS.")
