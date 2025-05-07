import json
import requests
import logging
import base64
import socket
import traceback
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from .models import Invoice, CompanyConfig
from datetime import datetime
import uuid
import time

logger = logging.getLogger(__name__)

# Comentando a classe antiga de FocusNFe mas mantendo para referência
"""
class FocusNFeService:
    # O código da classe FocusNFeService existente
    ...
"""

class NFEioService:
    """
    Serviço para integração com a API do NFE.io
    """
    
    def __init__(self):
        self.api_key = settings.NFEIO_API_KEY
        self.company_id = settings.NFEIO_COMPANY_ID
        self.environment = settings.NFEIO_ENVIRONMENT
        self.base_url = 'https://api.nfe.io'
        self.max_retries = 3
        self.retry_delay = 5  # segundos
        
        # Verificar se estamos em modo de teste offline
        self.offline_mode = getattr(settings, 'NFEIO_OFFLINE_MODE', False)
        if self.offline_mode:
            logger.warning("NFEioService inicializado em modo OFFLINE. Nenhuma requisição real será feita.")
            print("DEBUG - NFEioService em modo OFFLINE. Simulando respostas da API.")
        
        self.headers = {
            'Authorization': f'Basic {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"NFEioService inicializado: ambiente={self.environment}, base_url={self.base_url}, offline_mode={self.offline_mode}")

    def validate_company_config(self, company_config):
        """
        Valida a configuração da empresa do professor
        """
        if not company_config:
            return False, "Professor não possui configuração de empresa"
            
        if not company_config.enabled:
            return False, "Emissão de notas fiscais desabilitada para este professor"
            
        if not company_config.is_complete():
            return False, "Configurações fiscais incompletas para este professor"
            
        return True, "Configuração válida"

    def validate_student_data(self, student):
        """
        Valida os dados do aluno (cliente)
        """
        required_fields = {
            'CPF': student.cpf,
            'Nome': student.get_full_name(),
            'Email': student.email,
            'Endereço': student.address_line,
            'Número': student.address_number,
            'Bairro': student.neighborhood,
            'Cidade': student.city,
            'Estado': student.state,
            'CEP': student.zipcode
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            return False, f"Campos obrigatórios do cliente faltando: {', '.join(missing_fields)}"
            
        return True, "Dados do cliente válidos"

    def check_connectivity(self):
        """
        Verifica se o serviço NFE.io está acessível
        """
        if self.offline_mode:
            logger.info("Verificação de conectividade ignorada (modo offline)")
            return True
            
        try:
            # Tentar resolver o nome do domínio
            host = self.base_url.replace('https://', '').replace('http://', '')
            if '/' in host:
                host = host.split('/')[0]
                
            logger.info(f"Tentando resolver o nome de domínio: {host}")
            print(f"DEBUG - Tentando resolver o nome de domínio: {host}")
            socket.gethostbyname(host)
            return True
        except Exception as e:
            error_msg = f"Erro ao verificar conectividade com NFE.io: {str(e)}"
            logger.error(error_msg)
            print(f"DEBUG - ERRO de conectividade: {error_msg}")
            return False

    def _make_request(self, method, endpoint, data=None, retry_count=0):
        """
        Realiza uma requisição para a API do NFE.io com retry automático
        """
        if self.offline_mode:
            return self._simulate_request(method, endpoint, data)
            
        try:
            url = f"{self.base_url}/{endpoint}"
            
            # Log do payload
            if data:
                print(f"\nDEBUG - Payload da requisição:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            
            response = requests.request(method, url, headers=self.headers, json=data)
            
            # Log da resposta
            print(f"\nDEBUG - Resposta da API:")
            print(f"Status: {response.status_code}")
            try:
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            except:
                print(response.text)
            
            # Se houver erro 5xx, tentar novamente
            if response.status_code >= 500 and retry_count < self.max_retries:
                logger.warning(f"Erro {response.status_code} na requisição. Tentativa {retry_count + 1} de {self.max_retries}")
                time.sleep(self.retry_delay)
                return self._make_request(method, endpoint, data, retry_count + 1)
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na requisição para NFE.io: {str(e)}"
            logger.error(error_msg)
            return {"error": True, "message": error_msg}

    def emit_invoice(self, invoice):
        """
        Emite uma nota fiscal de serviço usando a API NFE.io
        """
        print(f"\nDEBUG - Iniciando emissão de nota fiscal ID: {invoice.id}")
        
        # 1. Validar configuração do professor
        professor = invoice.transaction.enrollment.course.professor
        config_valid, config_message = self.validate_company_config(professor.company_config)
        if not config_valid:
            invoice.status = 'error'
            invoice.error_message = config_message
            invoice.save()
            return {"error": True, "message": config_message}
            
        # 2. Validar dados do aluno
        student = invoice.transaction.enrollment.student
        student_valid, student_message = self.validate_student_data(student)
        if not student_valid:
            invoice.status = 'error'
            invoice.error_message = student_message
            invoice.save()
            return {"error": True, "message": student_message}
            
        # 3. Verificar conectividade
        if not self.check_connectivity():
            error_msg = "Não foi possível conectar ao serviço NFE.io"
            invoice.status = 'error'
            invoice.error_message = error_msg
            invoice.save()
            return {"error": True, "message": error_msg}
            
        # 4. Gerar número RPS se necessário
        if invoice.rps_numero is None:
            self._generate_rps_for_invoice(invoice, professor)
            
        # 5. Preparar dados da nota
        invoice_data = self._prepare_invoice_data(invoice)
        
        # 6. Emitir nota
        endpoint = f"v1/companies/{self.company_id}/serviceinvoices"
        response = self._make_request('POST', endpoint, invoice_data)
        
        if response.get('error'):
            invoice.status = 'error'
            invoice.error_message = response.get('message')
            invoice.save()
            return response
            
        # 7. Atualizar nota com resposta
        self._update_invoice_with_response(invoice, response)
        
        # 8. Verificar status inicial
        time.sleep(5)
        self.check_invoice_status(invoice)
        
        return response

    def _prepare_invoice_data(self, invoice):
        """
        Prepara os dados da nota fiscal no formato esperado pela API
        """
        transaction = invoice.transaction
        student = transaction.enrollment.student
        professor = transaction.enrollment.course.professor
        
        # Limpar CPF
        cpf = getattr(student, 'cpf', '00000000000')
        if cpf:
            cpf = cpf.replace('.', '').replace('-', '')
        else:
            cpf = '00000000000'
            
        # Determinar tipo de pessoa
        borrower_type = "LegalEntity" if len(cpf) > 11 else "NaturalPerson"
        
        # Descrição do serviço
        service_description = f"Aula de {transaction.enrollment.course.title}"
        if hasattr(transaction, 'customized_description') and transaction.customized_description:
            service_description = transaction.customized_description
            
        # Formatar valor do serviço
        services_amount = float(transaction.amount)
        if services_amount <= 0:
            services_amount = 0.01  # Valor mínimo para evitar erro
            
        # Formatar CEP
        zipcode = getattr(student, 'zipcode', '00000000')
        if zipcode:
            zipcode = zipcode.replace('-', '')
        else:
            zipcode = '00000000'
            
        # Obter estado e cidade
        state = getattr(student, 'state', 'SP') or 'SP'
        city = getattr(student, 'city', 'São Paulo') or 'São Paulo'
        
        # Mapear código da cidade baseado no estado
        city_codes = {
            'SP': '3550308',  # São Paulo
            'RJ': '3304557',  # Rio de Janeiro
            'MG': '3106200',  # Belo Horizonte
            'RS': '4314902',  # Porto Alegre
            'PR': '4106902',  # Curitiba
            'BA': '2927408',  # Salvador
            'PE': '2611606',  # Recife
            'CE': '2304400',  # Fortaleza
            'DF': '5300108',  # Brasília
            'GO': '5208707',  # Goiânia
        }
        
        # Usar código da cidade do estado ou São Paulo como fallback
        city_code = city_codes.get(state.upper(), '3550308')
            
        return {
            "borrower": {
                "type": borrower_type,
                "name": f"{student.first_name} {student.last_name}".strip(),
                "email": student.email,
                "federalTaxNumber": str(cpf),  # Garantir que é string
                "address": {
                    "country": "BRA",
                    "state": state.upper(),  # Garantir que estado está em maiúsculo
                    "city": {
                        "code": city_code,
                        "name": city
                    },
                    "district": getattr(student, 'neighborhood', 'Centro') or 'Centro',
                    "street": getattr(student, 'address_line', 'Endereço não informado') or 'Endereço não informado',
                    "number": getattr(student, 'address_number', 'S/N') or 'S/N',
                    "postalCode": zipcode,
                    "additionalInformation": getattr(student, 'address_complement', '') or ''
                }
            },
            "cityServiceCode": "0107",
            "description": service_description,
            "servicesAmount": str(services_amount),  # Enviar como string
            "environment": "Production" if self.environment == "production" else "Testing",
            "reference": f"TRANSACTION_{transaction.id}",
            "additionalInformation": f"Aula ministrada por {professor.first_name} {professor.last_name}. Plataforma: 555JAM",
            "rpsSerialNumber": str(invoice.rps_serie),  # Garantir que é string
            "rpsNumber": str(invoice.rps_numero)  # Garantir que é string
        }

    def _update_invoice_with_response(self, invoice, response):
        """
        Atualiza o objeto Invoice com os dados da resposta da API
        """
        invoice.external_id = response.get('id')
        invoice.focus_status = response.get('flowStatus')
        invoice.status = 'processing'
        invoice.response_data = response
        
        if 'pdf' in response and response['pdf'] is not None:
            invoice.focus_pdf_url = response['pdf'].get('url')
            
        if 'xml' in response and response['xml'] is not None:
            invoice.focus_xml_url = response['xml'].get('url')
            
        invoice.emitted_at = timezone.now()
        invoice.save()

    def _simulate_request(self, method, endpoint, data=None):
        """
        Simula uma resposta da API em modo offline
        """
        external_id = str(uuid.uuid4())
        
        if method.upper() == 'POST' and 'serviceinvoices' in endpoint:
            return {
                "id": external_id,
                "status": "Processing",
                "flowStatus": "WaitingCalculateTaxes",
                "flowMessage": "Aguardando cálculo de impostos (simulado)",
                "pdf": {"url": f"https://exemplo.com/pdf/{external_id}.pdf"},
                "xml": {"url": f"https://exemplo.com/xml/{external_id}.xml"}
            }
            
        return {"error": True, "message": "Método ou endpoint não suportado em modo offline"}

    def check_invoice_status(self, invoice):
        """
        Verifica o status de uma nota fiscal no NFE.io
        """
        # Se estiver em modo offline, retornar uma resposta simulada
        if self.offline_mode:
            logger.info(f"Verificando status da nota fiscal ID {invoice.id} em modo OFFLINE (simulado)")
            print(f"DEBUG - Verificando status em modo OFFLINE: Invoice ID {invoice.id}")
            
            # Simular diferentes status baseados no ID da nota
            status_options = ['approved', 'processing', 'error', 'cancelled']
            simulated_status = status_options[invoice.id % len(status_options)]
            
            # Para notas em processamento, alternar para aprovado após algum tempo
            if invoice.status == 'processing' and invoice.created_at:
                time_since_creation = timezone.now() - invoice.created_at
                if time_since_creation.total_seconds() > 30:  # Aprovar após 30 segundos
                    simulated_status = 'approved'
            
            # Mapear para status externo
            external_status_map = {
                'approved': 'Issued',
                'processing': 'Processing',
                'error': 'Error',
                'cancelled': 'Cancelled'
            }
            
            # Atualizar o status da nota
            invoice.status = simulated_status
            invoice.external_status = external_status_map.get(simulated_status, 'Unknown')
            invoice.external_message = f"Status simulado: {simulated_status}"
            invoice.last_checked = timezone.now()
            invoice.save()
            
            return {
                'success': True,
                'status': simulated_status,
                'external_status': external_status_map.get(simulated_status, 'Unknown'),
                'message': f"Status simulado: {simulated_status}"
            }
        
        try:
            # Verificar conectividade antes de fazer a requisição
            if not self.check_connectivity():
                return {
                    'success': False,
                    'status': 'error',
                    'message': 'Não foi possível conectar ao serviço NFE.io. Verifique sua conexão com a internet.'
                }
            
            # Se não tiver ID externo, não há como verificar
            if not invoice.external_id:
                return {
                    'success': False,
                    'status': 'error',
                    'message': 'Nota fiscal sem ID externo'
                }
            
            # Montar URL para consulta
            url = f"{self.base_url}/v1/companies/{self.company_id}/serviceinvoices/{invoice.external_id}"
            
            # Fazer requisição para a API
            response = requests.get(url, headers=self.headers)
            
            # Verificar se a requisição foi bem-sucedida
            if response.status_code == 200:
                data = response.json()
                
                # Mapear status da API para status interno
                status_mapping = {
                    'Issued': 'approved',
                    'Cancelled': 'cancelled',
                    'Processing': 'processing',
                    'Error': 'error',
                    'Draft': 'pending'
                }
                
                api_status = data.get('status', 'Unknown')
                internal_status = status_mapping.get(api_status, 'error')
                
                return {
                    'success': True,
                    'status': internal_status,
                    'external_status': api_status,
                    'message': data.get('flowStatus', {}).get('message', '')
                }
            else:
                # Tratar erros da API
                error_message = f"Erro na API NFE.io: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_message = error_data['message']
                except:
                    pass
                
                return {
                    'success': False,
                    'status': 'error',
                    'message': error_message
                }
                
        except Exception as e:
            logger.error(f"Erro ao verificar status da nota fiscal: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'status': 'error',
                'message': f'Erro interno: {str(e)}'
            }

    def _generate_rps_for_invoice(self, invoice, professor):
        """
        Gera um número de RPS para a nota fiscal e atualiza o contador no CompanyConfig.
        
        Args:
            invoice: Objeto Invoice do Django
            professor: Objeto User (professor) associado à nota fiscal
        """
        print(f"DEBUG - Gerando número RPS para invoice {invoice.id}")
        
        # Obter a configuração da empresa do professor
        try:
            company_config = CompanyConfig.objects.get(user=professor)
            
            # Atribuir valores de RPS à nota fiscal
            invoice.rps_serie = company_config.rps_serie
            invoice.rps_numero = company_config.rps_numero_atual
            invoice.rps_lote = company_config.rps_lote
            invoice.save()
            
            # Incrementar o contador de RPS na configuração da empresa
            company_config.rps_numero_atual += 1
            company_config.save()
            
            print(f"DEBUG - RPS gerado: Série {invoice.rps_serie}, Número {invoice.rps_numero}")
            print(f"DEBUG - Próximo número RPS será: {company_config.rps_numero_atual}")
            
        except CompanyConfig.DoesNotExist:
            print(f"DEBUG - ERRO: Configuração da empresa não encontrada para o professor {professor.id}")
            # Usar valores padrão para evitar falha na emissão
            invoice.rps_serie = '1'
            invoice.rps_numero = 1
            invoice.rps_lote = 1
            invoice.save()
            print(f"DEBUG - RPS padrão gerado: Série 1, Número 1")
    
    def cancel_invoice(self, invoice, cancel_reason):
        """
        Cancela uma nota fiscal emitida.
        
        Args:
            invoice: Objeto Invoice do Django
            cancel_reason: Motivo do cancelamento
            
        Returns:
            dict: Resposta da API com o resultado do cancelamento
        """
        if not invoice.external_id:
            logger.error(f"Nota fiscal {invoice.id} não possui ID externo")
            invoice.error_message = "Nota fiscal não possui ID externo"
            invoice.save()
            return {"error": True, "message": "Nota fiscal não possui ID externo"}
        
        # Verifica se a nota pode ser cancelada (baseado no status atual)
        status_map = {
            'approved': True,
            'issued': True,
            'processing': False,
            'cancelled': False,
            'error': False,
            'pending': False
        }
        
        if not status_map.get(invoice.status, False):
            error_msg = f"Nota fiscal com status '{invoice.status}' não pode ser cancelada"
            logger.error(f"Tentativa de cancelamento inválida: {error_msg}")
            invoice.error_message = error_msg
            invoice.save()
            return {"error": True, "message": error_msg}
        
        logger.info(f"Cancelando nota fiscal ID={invoice.id}, external_id={invoice.external_id}")
        
        # Preparar dados para o cancelamento
        cancel_data = {
            "reason": cancel_reason[:255] if cancel_reason else "Cancelamento a pedido do cliente"
        }
        
        # Fazer requisição para cancelar a nota
        endpoint = f"companies/{self.company_id}/serviceinvoices/{invoice.external_id}/cancel"
        response = self._make_request('POST', endpoint, cancel_data)
        
        # Log para debugging
        logger.info(f"Resposta do cancelamento: {response}")
        
        # Processar a resposta do cancelamento
        if not response.get('error'):
            if response.get('flowStatus') == 'Cancelled':
                invoice.status = 'cancelled'
                invoice.focus_status = 'Cancelled'
                invoice.cancelled_at = timezone.now()
                invoice.save()
                logger.info(f"Nota fiscal {invoice.id} cancelada com sucesso")
            else:
                # Pode estar em processo de cancelamento
                invoice.status = 'processing'
                invoice.focus_status = response.get('flowStatus', 'ProcessingCancellation')
                invoice.save()
                logger.info(f"Cancelamento em processamento: {response.get('flowStatus')}")
        else:
            error_msg = response.get('message', 'Erro desconhecido ao cancelar nota fiscal')
            logger.error(f"Erro ao cancelar nota fiscal: {error_msg}")
            invoice.error_message = error_msg
            invoice.save()
        
        return response
    
    def download_pdf(self, invoice):
        """
        Obtém a URL para download do PDF da nota fiscal.
        
        Args:
            invoice: Objeto Invoice do Django
            
        Returns:
            str: URL para download do PDF ou None
        """
        if not invoice.external_id:
            logger.error(f"Nota fiscal {invoice.id} não possui ID externo")
            return None
        
        # Verificar se já temos a URL do PDF salva
        if hasattr(invoice, 'focus_pdf_url') and invoice.focus_pdf_url:
            logger.info(f"URL do PDF já disponível: {invoice.focus_pdf_url}")
            return invoice.focus_pdf_url
        
        logger.info(f"Obtendo PDF da nota fiscal ID={invoice.id}, external_id={invoice.external_id}")
        
        # Primeiro, vamos verificar o status atual da nota
        status_response = self.check_invoice_status(invoice)
        
        # Se o status retornou erro, não seguimos
        if status_response.get('error'):
            logger.error(f"Erro ao verificar status para download do PDF: {status_response.get('message')}")
            return None
        
        # Verificar se a nota está autorizada (apenas notas autorizadas têm PDF)
        if invoice.status != 'approved' and invoice.focus_status != 'Authorized':
            logger.warning(f"Nota fiscal {invoice.id} não está autorizada, não há PDF disponível")
            return None
        
        # Se a verificação de status atualizou o URL do PDF, retornar
        if hasattr(invoice, 'focus_pdf_url') and invoice.focus_pdf_url:
            return invoice.focus_pdf_url
            
        # Caso não tenha URL ainda, solicitar diretamente
        endpoint = f"companies/{self.company_id}/serviceinvoices/{invoice.external_id}/pdf"
        response = self._make_request('GET', endpoint)
        
        if not response.get('error') and 'url' in response:
            # Salvar a URL do PDF no objeto invoice
            invoice.focus_pdf_url = response['url']
            invoice.save()
            logger.info(f"URL do PDF obtida com sucesso: {response['url']}")
            return response['url']
        else:
            logger.error(f"Erro ao obter URL do PDF: {response.get('message', 'Erro desconhecido')}")
            return None
