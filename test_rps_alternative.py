"""
Script para testar a emissão de nota fiscal com RPS - Abordagem alternativa
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

def show_rps_config():
    """
    Mostra a configuração atual de RPS
    """
    try:
        professor = User.objects.get(email='professor@example.com')
        company_config = CompanyConfig.objects.get(user=professor)
        
        logger.info("=== CONFIGURAÇÃO RPS ATUAL ===")
        logger.info(f"Série RPS: '{company_config.rps_serie}'")
        logger.info(f"Número atual RPS: {company_config.rps_numero_atual}")
        logger.info(f"Lote RPS: {company_config.rps_lote}")
        
        return company_config
    except Exception as e:
        logger.error(f"Erro ao obter configuração: {str(e)}")
        return None

def update_rps_config(serie="RPS", numero=1, lote=1):
    """
    Atualiza a configuração de RPS
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

class ModifiedNFEioService(NFEioService):
    """
    Versão modificada do serviço NFEio que altera a maneira como o RPS é enviado
    """
    
    def emit_invoice(self, invoice):
        """
        Sobrescreve o método original para alterar o formato do RPS
        """
        print(f"\nDEBUG - Iniciando emissão de nota fiscal ID: {invoice.id}")
        print(f"DEBUG - Status atual: {invoice.status}")
        
        # Dados da transação
        transaction = invoice.transaction
        print(f"DEBUG - Transação: {transaction.id} - Valor: {transaction.amount}")
        
        # Dados do professor (prestador) - corrigindo o acesso ao professor
        enrollment = transaction.enrollment
        course = enrollment.course
        professor = course.professor
        print(f"DEBUG - Curso: {course.title}")
        print(f"DEBUG - Professor: {professor.username}")
        
        # Obter ou criar o próximo número de RPS
        if invoice.rps_numero is None:
            self._generate_rps_for_invoice(invoice, professor)
        print(f"DEBUG - RPS: Série {invoice.rps_serie}, Número {invoice.rps_numero}")
        
        if not hasattr(professor, 'company_config'):
            error_msg = f"Professor {professor.id} não possui configuração de empresa"
            print(f"DEBUG - ERRO: {error_msg}")
            invoice.status = 'error'
            invoice.error_message = error_msg
            invoice.save()
            return {"error": True, "message": error_msg}
            
        company_config = professor.company_config
        print(f"DEBUG - Configuração da empresa: {company_config}")
        
        # Dados do estudante (cliente)
        student = enrollment.student
        print(f"DEBUG - Aluno: {student.username}")
        
        # Montar objeto para envio
        service_description = f"Aula de {course.title}"
        if hasattr(transaction, 'customized_description') and transaction.customized_description:
            service_description = transaction.customized_description
            
        print(f"DEBUG - Descrição do serviço: {service_description}")
            
        # Preparar dados da nota fiscal no formato esperado pela API NFE.io
        # Incluindo informações do RPS
        
        # Verificar se o documento do cliente é CPF ou CNPJ
        cpf = getattr(student, 'cpf', '00000000000')
        if cpf:
            cpf = cpf.replace('.', '').replace('-', '')
        else:
            cpf = '00000000000'
            
        # Verificar se é pessoa física ou jurídica baseado no tamanho do documento
        # CPF = 11 dígitos, CNPJ = 14 dígitos
        if len(cpf) == 11:
            borrower_type = "NaturalPerson"  # Pessoa Física
        else:
            borrower_type = "LegalEntity"    # Pessoa Jurídica
            
        invoice_data = {
            "borrower": {
                "type": borrower_type,
                "name": f"{student.first_name} {student.last_name}".strip(),
                "email": student.email,
                "federalTaxNumber": int(cpf),
                "address": {
                    "country": "BRA",
                    "state": getattr(student, 'state', 'SP') or 'SP',
                    "city": {
                        "code": "3550308",  # Código IBGE para São Paulo (padrão)
                        "name": getattr(student, 'city', 'São Paulo') or 'São Paulo'
                    },
                    "district": getattr(student, 'neighborhood', 'Centro') or 'Centro',
                    "street": getattr(student, 'address_line', 'Endereço não informado') or 'Endereço não informado',
                    "number": getattr(student, 'address_number', 'S/N') or 'S/N',
                    "postalCode": getattr(student, 'zipcode', '00000000').replace('-', '') or '00000000',
                    "additionalInformation": getattr(student, 'address_complement', '') or ''
                }
            },
            "cityServiceCode": "0107",
            "description": service_description,
            "servicesAmount": float(transaction.amount),
            "environment": self.environment,
            "reference": f"TRANSACTION_{transaction.id}",
            "additionalInformation": f"Aula ministrada por {professor.first_name} {professor.last_name}. Plataforma: 555JAM",
            # Adicionar informações do RPS - usando apenas o número, sem série
            "rpsNumber": invoice.rps_numero
        }
        
        # Adicionar a série apenas se não for vazia
        if invoice.rps_serie and invoice.rps_serie.strip():
            invoice_data["rpsSerialNumber"] = invoice.rps_serie
        
        print(f"DEBUG - Dados da nota fiscal para envio: {json.dumps(invoice_data, indent=2)}")
        
        # Endpoint para emissão de nota fiscal
        endpoint = f"companies/{self.company_id}/serviceinvoices"
        print(f"DEBUG - Endpoint de emissão: {endpoint}")
        
        # Realizar a requisição
        print(f"DEBUG - Enviando dados para API NFE.io")
        response = self._make_request('POST', endpoint, invoice_data)
        print(f"DEBUG - Resposta da emissão: {response}")
        
        # Verificar se a requisição foi bem sucedida
        if response.get('error'):
            error_msg = response.get('message', 'Erro desconhecido na emissão')
            print(f"DEBUG - ERRO na emissão: {error_msg}")
            invoice.status = 'error'
            invoice.error_message = error_msg
            invoice.save()
            return response
            
        # Atualizar o objeto Invoice com os dados retornados
        print(f"DEBUG - Emissão bem sucedida")
        invoice.external_id = response.get('id')
        invoice.focus_status = response.get('flowStatus')
        invoice.status = 'processing'  # Inicialmente fica como processing até confirmação
        invoice.response_data = response
        
        print(f"DEBUG - External ID: {invoice.external_id}")
        print(f"DEBUG - Focus Status: {invoice.focus_status}")
        
        # Outras informações úteis que podem estar na resposta
        if 'pdf' in response and response['pdf'] is not None:
            pdf_url = response.get('pdf', {}).get('url')
            if pdf_url:
                invoice.focus_pdf_url = pdf_url
                print(f"DEBUG - PDF URL: {pdf_url}")
        
        if 'xml' in response and response['xml'] is not None:
            xml_url = response.get('xml', {}).get('url')
            if xml_url:
                invoice.focus_xml_url = xml_url
                print(f"DEBUG - XML URL: {xml_url}")
                
        invoice.emitted_at = timezone.now()
        print(f"DEBUG - Salvando nota fiscal emitida")
        invoice.save()
        
        # Checar o status imediatamente após emissão para detectar erros rapidamente
        print(f"DEBUG - Verificando status imediatamente após emissão")
        self.check_invoice_status(invoice)
        
        return response

def emit_invoice_for_transaction(transaction_id):
    """
    Emite uma nota fiscal para uma transação específica usando o serviço modificado
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
    
    # Emitir nota fiscal usando o serviço NFEio modificado
    service = ModifiedNFEioService()
    try:
        logger.info("Emitindo nota fiscal com serviço modificado...")
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
        
        return True
    except Exception as e:
        logger.error(f"Erro ao emitir nota fiscal: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== Teste de Emissão de Nota Fiscal com RPS - Abordagem Alternativa ===")
    
    # Mostrar configuração atual
    show_rps_config()
    
    # Atualizar configuração RPS para usar a variação "RPS"
    logger.info("\n=== Atualizando configuração RPS ===")
    config = update_rps_config(serie="RPS", numero=1, lote=1)
    
    if config:
        # Criar transação de teste
        logger.info("\n=== Criando transação de teste ===")
        transaction = create_test_transaction()
        
        if transaction:
            logger.info(f"Transação criada com sucesso: ID={transaction.id}")
            
            # Emitir nota fiscal para a transação
            logger.info("\n=== Emitindo nota fiscal com abordagem alternativa ===")
            result = emit_invoice_for_transaction(transaction.id)
            
            if result:
                logger.info("Nota fiscal emitida com sucesso!")
            else:
                logger.error("Falha ao emitir nota fiscal. Verifique os logs.")
        else:
            logger.error("Falha ao criar transação de teste.")
    else:
        logger.error("Não foi possível atualizar a configuração de RPS.")
