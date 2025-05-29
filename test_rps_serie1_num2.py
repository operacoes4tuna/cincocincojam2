"""
Script para:
1. Verificar a configuração da empresa no NFE.io e compará-la com o formato padrão
2. Testar emissão com série 1 e número 2
"""
import os
import sys
import json
import requests
import django
import logging
from decimal import Decimal
from datetime import datetime

# Configurar ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Importar modelos e serviços após configuração do Django
from django.conf import settings
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

def get_company_info():
    """
    Obtém informações da empresa do NFE.io e compara com o formato padrão
    """
    print("=== Verificando configuração da empresa no NFE.io ===")
    
    # Dados da API
    api_key = settings.NFEIO_API_KEY
    company_id = settings.NFEIO_COMPANY_ID
    environment = settings.NFEIO_ENVIRONMENT
    base_url = "https://api.nfe.io/v1"
    
    print(f"API Key: {api_key[:5]}...{api_key[-5:]} (tamanho: {len(api_key)})")
    print(f"Company ID: {company_id}")
    print(f"Environment: {environment}")
    
    # Endpoint para informações da empresa
    url = f"{base_url}/companies/{company_id}"
    
    # Headers com autenticação
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    try:
        # Fazer requisição GET
        print(f"Fazendo requisição GET para {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Converter resposta para JSON
            company_info = response.json()
            
            # Exibir informações relevantes
            print("\nInformações da empresa:")
            print(f"Nome: {company_info.get('companies', {}).get('name')}")
            print(f"CNPJ: {company_info.get('companies', {}).get('federalTaxNumber')}")
            print(f"Série RPS: {company_info.get('companies', {}).get('rpsSerialNumber')}")
            print(f"Número RPS: {company_info.get('companies', {}).get('rpsNumber')}")
            print(f"Ambiente: {company_info.get('companies', {}).get('environment')}")
            
            # Verificar se a configuração segue o formato padrão
            print("\nFormatação similar ao exemplo padrão:")
            required_fields = ["id", "name", "federalTaxNumber", "rpsSerialNumber", "rpsNumber"]
            for field in required_fields:
                if field in company_info.get('companies', {}):
                    print(f"✅ Campo '{field}' encontrado")
                else:
                    print(f"❌ Campo '{field}' não encontrado")
            
            return company_info
        else:
            print(f"Erro na requisição: {response.status_code}")
            print(f"Resposta: {response.text}")
            return None
    except Exception as e:
        print(f"Erro ao obter informações da empresa: {str(e)}")
        return None

def update_rps_config(serie="1", numero=2, lote=1):
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
    print("=== Teste de configuração da empresa e emissão de nota fiscal ===")
    
    # Verificar informações da empresa
    company_info = get_company_info()
    
    # Atualizar configuração RPS para série 1, número 2
    logger.info("\n=== Atualizando configuração para Série 1, Número 2 ===")
    config = update_rps_config(serie="1", numero=2, lote=1)
    
    if config:
        # Criar transação de teste
        logger.info("\n=== Criando transação de teste ===")
        transaction = create_test_transaction()
        
        if transaction:
            logger.info(f"Transação criada com sucesso: ID={transaction.id}")
            
            # Emitir nota fiscal para a transação
            logger.info("\n=== Emitindo nota fiscal com Série 1, Número 2 ===")
            result = emit_invoice_for_transaction(transaction.id)
            
            if result:
                logger.info("Processo de emissão finalizado!")
            else:
                logger.error("Falha ao emitir nota fiscal. Verifique os logs.")
        else:
            logger.error("Falha ao criar transação de teste.")
    else:
        logger.error("Não foi possível atualizar a configuração de RPS.")
