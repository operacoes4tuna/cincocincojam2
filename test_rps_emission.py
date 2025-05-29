"""
Script para testar a emissão de nota fiscal com RPS
"""
import os
import sys
import django
import logging
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

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_rps_emission():
    """
    Testa a emissão de nota fiscal com RPS para uma transação
    """
    # Buscar um professor para o teste
    try:
        professor = User.objects.get(email='professor@example.com')
        logger.info(f"Professor encontrado: {professor.username}")
    except User.DoesNotExist:
        logger.error("Professor não encontrado. Utilize o comando 'python manage.py createsuperuser' para criar um usuário administrador.")
        return False
    
    # Verificar configuração RPS do professor
    try:
        company_config = CompanyConfig.objects.get(user=professor)
        logger.info(f"Configuração da empresa encontrada")
        logger.info(f"Série RPS: {company_config.rps_serie}")
        logger.info(f"Número atual RPS: {company_config.rps_numero_atual}")
        logger.info(f"Lote RPS: {company_config.rps_lote}")
    except CompanyConfig.DoesNotExist:
        logger.error("O professor não possui configuração de empresa. Configure em /invoices/settings/")
        return False
    
    # Verificar se existe transação de pagamento sem nota fiscal
    transactions = PaymentTransaction.objects.filter(
        enrollment__course__professor=professor,
        status='PAID'
    )
    
    if not transactions.exists():
        logger.error("Não foram encontradas transações para emissão de nota fiscal")
        return False
    
    # Filtrar transações que não possuem nota fiscal
    pending_transactions = []
    for transaction in transactions:
        if not Invoice.objects.filter(transaction=transaction).exists():
            pending_transactions.append(transaction)
    
    if not pending_transactions:
        logger.error("Não foram encontradas transações pendentes de nota fiscal")
        return False
    
    transaction = pending_transactions[0]
    logger.info(f"Transação selecionada: ID={transaction.id}, Valor={transaction.amount}")
    
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
        logger.info(f"RPS Série: {invoice.rps_serie}")
        logger.info(f"RPS Número: {invoice.rps_numero}")
        logger.info(f"RPS Lote: {invoice.rps_lote}")
        logger.info(f"External ID: {invoice.external_id}")
        
        # Verificar próximo número de RPS
        company_config.refresh_from_db()
        logger.info(f"Próximo número RPS: {company_config.rps_numero_atual}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao emitir nota fiscal: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== Teste de Emissão de Nota Fiscal com RPS ===")
    result = test_rps_emission()
    
    if result:
        logger.info("Teste concluído com sucesso!")
    else:
        logger.error("Teste falhou. Verifique os logs para mais detalhes.")
