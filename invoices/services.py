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
from django.db.models import F
from django.db import transaction

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
            
            print(f"\nDEBUG - Enviando requisição {method} para {url}")
            response = requests.request(method, url, headers=self.headers, json=data)
            
            # Log da resposta
            print(f"\nDEBUG - Resposta da API:")
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            try:
                response_data = response.json()
                print("Conteúdo da resposta:")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"Erro ao decodificar JSON: {str(e)}")
                print(f"Resposta bruta: {response.text}")
            
            # Se houver erro 5xx, tentar novamente
            if response.status_code >= 500 and retry_count < self.max_retries:
                print(f"DEBUG - Erro {response.status_code} na requisição. Tentativa {retry_count + 1} de {self.max_retries}")
                time.sleep(self.retry_delay)
                return self._make_request(method, endpoint, data, retry_count + 1)
            
            # Se for erro 4xx, capturar detalhes do erro
            if response.status_code >= 400 and response.status_code < 500:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', 'Erro não especificado')
                    error_details = error_data.get('details', {})
                    print(f"DEBUG - Erro {response.status_code} na requisição para NFE.io:")
                    print(f"Mensagem: {error_msg}")
                    if error_details:
                        print(f"Detalhes: {json.dumps(error_details, indent=2)}")
                    return {"error": True, "message": error_msg, "details": error_details}
                except Exception as e:
                    error_msg = f"Erro {response.status_code}: {response.text}"
                    print(f"DEBUG - Erro ao processar resposta: {str(e)}")
                    print(f"DEBUG - {error_msg}")
                    return {"error": True, "message": error_msg}
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na requisição para NFE.io: {str(e)}"
            print(f"DEBUG - {error_msg}")
            return {"error": True, "message": error_msg}

    def emit_invoice(self, invoice):
        """
        Emite uma nota fiscal de serviço usando a API NFE.io
        """
        print(f"\nDEBUG - Iniciando emissão de nota fiscal ID: {invoice.id}")
        
        # Verificar se a invoice está vinculada a uma transaction ou singlesale
        if invoice.transaction:
            # 1. Validar configuração do professor
            professor = invoice.transaction.enrollment.course.professor
            print(f"DEBUG - Professor: {professor.get_full_name()}")
            
            config_valid, config_message = self.validate_company_config(professor.company_config)
            if not config_valid:
                print(f"DEBUG - Erro na configuração: {config_message}")
                invoice.status = 'error'
                invoice.error_message = config_message
                invoice.save()
                return {"error": True, "message": config_message}
                
            # 2. Validar dados do aluno
            student = invoice.transaction.enrollment.student
            print(f"DEBUG - Aluno: {student.get_full_name()}")
            
            student_valid, student_message = self.validate_student_data(student)
            if not student_valid:
                print(f"DEBUG - Erro nos dados do aluno: {student_message}")
                invoice.status = 'error'
                invoice.error_message = student_message
                invoice.save()
                return {"error": True, "message": student_message}
        elif invoice.singlesale:
            # 1. Validar configuração do professor para venda avulsa
            professor = invoice.singlesale.seller
            print(f"DEBUG - Professor (vendedor): {professor.get_full_name()}")
            
            config_valid, config_message = self.validate_company_config(professor.company_config)
            if not config_valid:
                print(f"DEBUG - Erro na configuração: {config_message}")
                invoice.status = 'error'
                invoice.error_message = config_message
                invoice.save()
                return {"error": True, "message": config_message}
                
            # 2. Para vendas avulsas, não há validação de student
            print(f"DEBUG - Cliente: {invoice.singlesale.customer_name}")
        else:
            error_message = "A nota fiscal não está associada a uma transação ou venda avulsa"
            print(f"DEBUG - Erro: {error_message}")
            invoice.status = 'error'
            invoice.error_message = error_message
            invoice.save()
            return {"error": True, "message": error_message}
            
        # 3. Verificar conectividade
        if not self.check_connectivity():
            error_msg = "Não foi possível conectar ao serviço NFE.io"
            print(f"DEBUG - Erro de conectividade: {error_msg}")
            invoice.status = 'error'
            invoice.error_message = error_msg
            invoice.save()
            return {"error": True, "message": error_msg}
            
        # 4. Gerar número RPS
        print("DEBUG - Gerando número RPS...")
        self._generate_rps_for_invoice(invoice, professor)
        print(f"DEBUG - RPS gerado: Série {invoice.rps_serie}, Número {invoice.rps_numero}")
            
        # 5. Preparar dados da nota
        print("DEBUG - Preparando dados da nota...")
        invoice_data = self._prepare_invoice_data(invoice)
        print("DEBUG - Dados preparados:")
        print(json.dumps(invoice_data, indent=2, ensure_ascii=False))
        
        # 6. Emitir nota
        print("DEBUG - Enviando para API...")
        endpoint = f"v1/companies/{self.company_id}/serviceinvoices"
        response = self._make_request('POST', endpoint, invoice_data)
        
        if response.get('error'):
            print(f"DEBUG - Erro na API: {response.get('message')}")
            invoice.status = 'error'
            invoice.error_message = response.get('message')
            invoice.save()
            return response
            
        # 7. Atualizar nota com resposta
        print("DEBUG - Atualizando nota com resposta...")
        self._update_invoice_with_response(invoice, response)
        
        # 8. Verificar status inicial
        print("DEBUG - Verificando status inicial...")
        time.sleep(5)
        status_response = self.check_invoice_status(invoice)
        print(f"DEBUG - Status inicial: {status_response}")
        
        # 9. Se a nota estiver no estado WaitingSend, enviar explicitamente
        if invoice.focus_status == 'WaitingSend':
            print("DEBUG - Nota fiscal no estado WaitingSend, enviando explicitamente...")
            send_response = self.send_invoice(invoice)
            print(f"DEBUG - Resposta do envio explícito: {send_response}")
        
        return response

    def _prepare_invoice_data(self, invoice):
        """
        Prepara os dados da nota fiscal no formato esperado pela API
        """
        print("\nDEBUG - Preparando dados da nota fiscal...")
        
        # Verificar se é uma invoice de transação ou venda avulsa
        if invoice.transaction:
            # PROCESSAMENTO PARA TRANSAÇÕES DE CURSO
            transaction = invoice.transaction
            student = transaction.enrollment.student
            professor = transaction.enrollment.course.professor
            company_config = professor.company_config
            
            print(f"DEBUG - Dados do professor:")
            print(f"- Nome: {professor.get_full_name()}")
            print(f"- CNPJ: {company_config.cnpj}")
            print(f"- Código de serviço: {company_config.city_service_code}")
            
            # Limpar CPF e converter para número
            cpf = getattr(student, 'cpf', '00000000000')
            if cpf:
                cpf = cpf.replace('.', '').replace('-', '')
                print(f"DEBUG - CPF do aluno: {cpf}")
            else:
                cpf = '00000000000'
                print("DEBUG - CPF não informado, usando padrão")
                
            # Determinar tipo de pessoa
            borrower_type = "LegalEntity" if len(cpf) > 11 else "NaturalPerson"
            print(f"DEBUG - Tipo de pessoa: {borrower_type}")
            
            # Descrição do serviço
            service_description = f"Aula de {transaction.enrollment.course.title}"
            if hasattr(transaction, 'customized_description') and transaction.customized_description:
                service_description = transaction.customized_description
            print(f"DEBUG - Descrição do serviço: {service_description}")
                
            # Formatar valor do serviço
            services_amount = float(transaction.amount)
            if services_amount <= 0:
                services_amount = 0.01  # Valor mínimo para evitar erro
                print("DEBUG - Valor do serviço ajustado para mínimo")
            print(f"DEBUG - Valor do serviço: {services_amount}")
                
            # Formatar CEP
            zipcode = getattr(student, 'zipcode', '00000000')
            if zipcode:
                zipcode = zipcode.replace('-', '')
                print(f"DEBUG - CEP do aluno: {zipcode}")
            else:
                zipcode = '00000000'
                print("DEBUG - CEP não informado, usando padrão")
                
            # Obter estado e cidade
            state = getattr(student, 'state', 'SP') or 'SP'
            city = getattr(student, 'city', 'São Paulo') or 'São Paulo'
            print(f"DEBUG - Localização: {city}/{state}")
            
            # Dados do destinatário
            borrower_name = f"{student.first_name} {student.last_name}".strip()
            borrower_email = student.email
            reference = f"TRANSACTION_{transaction.id}"
            additional_information = f"Aula ministrada por {professor.get_full_name().strip() or professor.email}. Plataforma: 555JAM"
            
            # Preparar dados do endereço
            address = {
                "country": "BRA",
                "state": state.upper(),
                "city": {
                    "code": self._get_city_code(state),
                    "name": city
                },
                "district": getattr(student, 'neighborhood', 'Centro') or 'Centro',
                "street": getattr(student, 'address_line', 'Endereço não informado') or 'Endereço não informado',
                "number": getattr(student, 'address_number', 'S/N') or 'S/N',
                "postalCode": zipcode,
                "additionalInformation": getattr(student, 'address_complement', '') or ''
            }
            
        elif invoice.singlesale:
            # PROCESSAMENTO PARA VENDAS AVULSAS
            sale = invoice.singlesale
            professor = sale.seller
            company_config = professor.company_config
            
            print(f"DEBUG - Dados do vendedor:")
            print(f"- Nome: {professor.get_full_name()}")
            print(f"- CNPJ: {company_config.cnpj}")
            print(f"- Código de serviço: {company_config.city_service_code}")
            
            # Limpar CPF e converter para número
            cpf = sale.customer_cpf or '00000000000'
            if cpf:
                cpf = cpf.replace('.', '').replace('-', '')
                print(f"DEBUG - CPF do cliente: {cpf}")
            else:
                cpf = '00000000000'
                print("DEBUG - CPF não informado, usando padrão")
                
            # Determinar tipo de pessoa
            borrower_type = "LegalEntity" if len(cpf) > 11 else "NaturalPerson"
            print(f"DEBUG - Tipo de pessoa: {borrower_type}")
            
            # Descrição do serviço
            service_description = sale.description or "Venda avulsa"
            print(f"DEBUG - Descrição do serviço: {service_description}")
                
            # Formatar valor do serviço
            services_amount = float(sale.amount)
            if services_amount <= 0:
                services_amount = 0.01  # Valor mínimo para evitar erro
                print("DEBUG - Valor do serviço ajustado para mínimo")
            print(f"DEBUG - Valor do serviço: {services_amount}")
            
            # Formatar CEP
            zipcode = sale.customer_zipcode or '00000000'
            if zipcode:
                zipcode = zipcode.replace('-', '')
                print(f"DEBUG - CEP do cliente: {zipcode}")
            else:
                zipcode = '00000000'
                print("DEBUG - CEP não informado, usando padrão")
                
            # Obter estado e cidade
            state = sale.customer_state or 'SP'
            city = sale.customer_city or 'São Paulo'
            print(f"DEBUG - Localização: {city}/{state}")
            
            # Dados para venda avulsa
            borrower_name = sale.customer_name
            borrower_email = sale.customer_email
            reference = f"SALE_{sale.id}"
            additional_information = f"Venda realizada por {professor.get_full_name().strip() or professor.email}. Plataforma: 555JAM"
            
            # Usar dados de endereço fornecidos na venda avulsa
            address = {
                "country": "BRA",
                "state": state.upper(),
                "city": {
                    "code": self._get_city_code(state),
                    "name": city
                },
                "district": sale.customer_neighborhood or 'Centro',
                "street": sale.customer_address or 'Endereço não informado',
                "number": sale.customer_address_number or 'S/N',
                "postalCode": zipcode,
                "additionalInformation": sale.customer_address_complement or ''
            }
        else:
            raise ValueError("Invoice não está associada a uma transação ou venda avulsa")

        # Formatação comum para ambos os tipos de invoice
        # Verificar se existe um código de serviço específico na venda
        service_code = None
        
        # Se for uma venda avulsa e tiver um código de serviço específico, usar ele
        if invoice.singlesale and invoice.singlesale.municipal_service_code:
            service_code = invoice.singlesale.municipal_service_code
            print(f"DEBUG - Usando código de serviço específico da venda: {service_code}")
        # Caso contrário, usar o código padrão da empresa
        else:
            service_code = company_config.city_service_code
            print(f"DEBUG - Usando código de serviço padrão da empresa: {service_code}")
            
        if not service_code:
            print("DEBUG - ERRO: Código de serviço não configurado!")
            raise ValueError("Código de serviço não configurado para o professor")
        
        # Formatar o código de serviço (remover pontos e garantir 4 dígitos)
        service_code = service_code.replace('.', '')
        if len(service_code) < 4:
            service_code = service_code.zfill(4)
        print(f"DEBUG - Código de serviço formatado: {service_code}")
        
        # Montar payload final
        payload = {
            "borrower": {
                "type": borrower_type,
                "name": borrower_name,
                "email": borrower_email,
                "federalTaxNumber": int(cpf),  # Converter para número inteiro
                "address": address
            },
            "cityServiceCode": service_code,  # Usar cityServiceCode em vez de serviceCode
            "description": service_description,
            "servicesAmount": str(services_amount),
            "environment": "Production" if self.environment.lower() == "production" else "Testing",
            "reference": reference,
            "additionalInformation": additional_information,
            "rpsSerialNumber": str(invoice.rps_serie),
            "rpsNumber": str(invoice.rps_numero)
        }
        
        print("\nDEBUG - Payload final:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        
        return payload
        
    def _get_city_code(self, state):
        """
        Retorna o código da cidade baseado no estado
        """
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
        return city_codes.get(state.upper(), '3550308')

    def _update_invoice_with_response(self, invoice, response):
        """
        Atualiza o objeto Invoice com os dados da resposta da API
        """
        print(f"\nDEBUG - Atualizando invoice {invoice.id} com resposta:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        # Verificar se a resposta contém erro
        if response.get('error'):
            invoice.status = 'error'
            invoice.error_message = response.get('message', 'Erro não especificado')
            invoice.save()
            return
            
        # Extrair ID externo
        invoice.external_id = response.get('id')
        
        # Mapear status da API para status interno
        status_mapping = {
            'Issued': 'approved',
            'Authorized': 'approved',
            'Processing': 'processing',
            'Pending': 'processing',
            'Error': 'error',
            'Draft': 'pending',
            'Cancelled': 'cancelled',
            'WaitingCalculateTaxes': 'processing',
            'WaitingSend': 'processing',
            'WaitingAuthorize': 'processing',
            'WaitingCancel': 'processing',
            'Cancelled': 'cancelled',
            'Rejected': 'error'
        }
        
        # Obter status da API
        api_status = response.get('status', 'Unknown')
        flow_status = response.get('flowStatus', '')
        
        print(f"DEBUG - Status da API: {api_status}")
        print(f"DEBUG - Flow Status: {flow_status}")
        
        # Determinar status interno
        if api_status in status_mapping:
            invoice.status = status_mapping[api_status]
            print(f"DEBUG - Status mapeado do api_status: {invoice.status}")
        elif flow_status in status_mapping:
            invoice.status = status_mapping[flow_status]
            print(f"DEBUG - Status mapeado do flow_status: {invoice.status}")
        else:
            invoice.status = 'error'
            invoice.error_message = f"Status desconhecido: {api_status} / {flow_status}"
            print(f"DEBUG - Status desconhecido, marcando como erro: {invoice.error_message}")
        
        # Atualizar outros campos
        invoice.focus_status = flow_status
        invoice.response_data = response
        
        if 'pdf' in response and response['pdf'] is not None:
            invoice.focus_pdf_url = response['pdf'].get('url')
            print(f"DEBUG - URL do PDF: {invoice.focus_pdf_url}")
            
        if 'xml' in response and response['xml'] is not None:
            invoice.focus_xml_url = response['xml'].get('url')
            print(f"DEBUG - URL do XML: {invoice.focus_xml_url}")
            
        invoice.emitted_at = timezone.now()
        invoice.save()
        
        print(f"DEBUG - Invoice atualizada:")
        print(f"Status: {invoice.status}")
        print(f"Status API: {api_status}")
        print(f"Flow Status: {flow_status}")
        if invoice.error_message:
            print(f"Mensagem de erro: {invoice.error_message}")

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
            
            # Log da resposta
            logger.info(f"Resposta da API NFE.io para nota {invoice.id}:")
            logger.info(f"Status: {response.status_code}")
            try:
                logger.info(f"Conteúdo: {json.dumps(response.json(), indent=2)}")
            except:
                logger.info(f"Conteúdo: {response.text}")
            
            # Verificar se a requisição foi bem-sucedida
            if response.status_code == 200:
                data = response.json()
                
                # Mapear status da API para status interno
                status_mapping = {
                    'Issued': 'approved',
                    'Authorized': 'approved',
                    'Cancelled': 'cancelled',
                    'Processing': 'processing',
                    'Pending': 'processing',
                    'Error': 'error',
                    'Draft': 'pending'
                }
                
                api_status = data.get('status', 'Unknown')
                internal_status = status_mapping.get(api_status, 'error')
                
                # Atualizar o status da nota
                invoice.status = internal_status
                invoice.external_status = api_status
                invoice.external_message = data.get('flowStatus', '')  # flowStatus é uma string
                invoice.last_checked = timezone.now()
                invoice.save()
                
                # Se a nota foi aprovada, atualizar URLs do PDF e XML
                if internal_status == 'approved':
                    if 'pdf' in data and data['pdf'] is not None:
                        invoice.focus_pdf_url = data['pdf'].get('url')
                    if 'xml' in data and data['xml'] is not None:
                        invoice.focus_xml_url = data['xml'].get('url')
                    invoice.save()
                
                return {
                    'success': True,
                    'status': internal_status,
                    'external_status': api_status,
                    'message': data.get('flowStatus', '')
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
                
                # Atualizar status da nota para erro
                invoice.status = 'error'
                invoice.error_message = error_message
                invoice.last_checked = timezone.now()
                invoice.save()
                
                return {
                    'success': False,
                    'status': 'error',
                    'message': error_message
                }
                
        except Exception as e:
            logger.error(f"Erro ao verificar status da nota fiscal: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Atualizar status da nota para erro
            invoice.status = 'error'
            invoice.error_message = f'Erro interno: {str(e)}'
            invoice.last_checked = timezone.now()
            invoice.save()
            
            return {
                'success': False,
                'status': 'error',
                'message': f'Erro interno: {str(e)}'
            }

    def _generate_rps_for_invoice(self, invoice, professor):
        """
        Gera número de RPS para a invoice
        """
        print(f"\nDEBUG - Gerando número RPS para invoice {invoice.id}...")
        
        # Verificar se já existe RPS
        if invoice.rps_numero and invoice.rps_serie:
            print(f"DEBUG - Invoice já possui RPS: Série {invoice.rps_serie}, Número {invoice.rps_numero}")
            return
        
        try:
            # Obter configuração do professor
            company_config = professor.company_config
            
            # Definir série RPS
            rps_serie = company_config.rps_serie
            
            # Obter próximo número RPS
            with transaction.atomic():
                # Recarregar com lock de tabela para evitar condição de corrida
                company_config = CompanyConfig.objects.select_for_update().get(id=company_config.id)
                
                # Obter próximo número
                rps_numero = company_config.rps_numero_atual
                
                # Incrementar número para próxima nota
                company_config.rps_numero_atual = F('rps_numero_atual') + 1
                company_config.save()
                
                # Recarregar para confirmar novos valores
                company_config.refresh_from_db()
                
                print(f"DEBUG - Número RPS atualizado: {rps_numero} -> {company_config.rps_numero_atual}")
            
            # Atualizar invoice com RPS
            invoice.rps_serie = rps_serie
            invoice.rps_numero = rps_numero
            invoice.rps_lote = company_config.rps_lote
            invoice.save()
            
            print(f"DEBUG - RPS gerado com sucesso: Série {rps_serie}, Número {rps_numero}, Lote {company_config.rps_lote}")
            
        except Exception as e:
            print(f"DEBUG - Erro ao gerar RPS: {str(e)}")
            raise e

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

    def get_pdf_url(self, company_id, invoice_focus_id):
        """
        Retorna a URL para acessar o PDF da nota fiscal.
        Em vez de retornar URL direta da API (que exige autenticação),
        retorna URL para uma view local que fará a requisição autenticada.
        """
        # Se estamos em modo de teste, retorna uma URL de teste
        if self.offline_mode:
            logger.info(f"Modo offline - retornando URL simulada para PDF")
            return f"https://example.com/test-pdf/{invoice_focus_id}.pdf"
        
        # Retornar URL para a view local que irá buscar o PDF
        from django.urls import reverse
        
        # Construir URL local para a view que fará download do PDF
        pdf_url = reverse('invoices:download_pdf', kwargs={'invoice_id': invoice_focus_id})
        
        logger.info(f"URL local para download do PDF gerada: {pdf_url}")
        return pdf_url

    def send_invoice(self, invoice):
        """
        Envia explicitamente uma nota fiscal que está no estado WaitingSend para processamento.
        Este método deve ser chamado quando a nota fiscal está no estado WaitingSend.
        """
        if not invoice.external_id:
            error_msg = "Nota fiscal não possui ID externo"
            logger.error(f"Erro ao enviar nota fiscal {invoice.id}: {error_msg}")
            invoice.error_message = error_msg
            invoice.save()
            return {"error": True, "message": error_msg}
        
        print(f"DEBUG - Enviando nota fiscal {invoice.id} (external_id: {invoice.external_id}) para processamento...")
        
        # Construir endpoint para envio da nota fiscal
        endpoint = f"v1/companies/{self.company_id}/serviceinvoices/{invoice.external_id}/send"
        
        # Fazer requisição POST sem payload
        response = self._make_request('POST', endpoint)
        
        # Processar resposta
        if not response.get('error'):
            print(f"DEBUG - Nota fiscal enviada com sucesso. Resposta: {response}")
            # Atualizar nota com resposta
            self._update_invoice_with_response(invoice, response)
            return response
        else:
            error_msg = response.get('message', 'Erro desconhecido ao enviar nota fiscal')
            print(f"DEBUG - Erro ao enviar nota fiscal: {error_msg}")
            invoice.error_message = error_msg
            invoice.save()
            return response
            
    def check_and_retry_waiting_invoices(self):
        """
        Verifica todas as notas fiscais no estado WaitingSend e tenta enviá-las novamente.
        Este método pode ser chamado periodicamente através de um cronjob ou Celery task.
        """
        try:
            # Buscar todas as notas com status 'processing' e focus_status 'WaitingSend'
            waiting_invoices = Invoice.objects.filter(
                status='processing', 
                focus_status='WaitingSend', 
                external_id__isnull=False
            )
            
            logger.info(f"Encontradas {waiting_invoices.count()} notas fiscais aguardando envio")
            
            # Para cada nota, tentar enviar novamente
            results = {
                'success': 0,
                'error': 0,
                'invoices': []
            }
            
            for invoice in waiting_invoices:
                logger.info(f"Tentando enviar nota fiscal {invoice.id} (external_id: {invoice.external_id})")
                
                # Tentar enviar a nota
                response = self.send_invoice(invoice)
                
                # Registrar resultado
                if not response.get('error'):
                    results['success'] += 1
                    results['invoices'].append({
                        'id': invoice.id,
                        'external_id': invoice.external_id,
                        'result': 'success'
                    })
                else:
                    results['error'] += 1
                    results['invoices'].append({
                        'id': invoice.id,
                        'external_id': invoice.external_id,
                        'result': 'error',
                        'error_message': response.get('message')
                    })
                
                # Aguardar um pouco entre as requisições para não sobrecarregar a API
                time.sleep(1)
            
            logger.info(f"Resultados do reenvio de notas: {results['success']} sucessos, {results['error']} erros")
            return results
            
        except Exception as e:
            logger.error(f"Erro ao verificar e reenviar notas fiscais: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'success': 0,
                'error': 1,
                'error_message': str(e)
            }
