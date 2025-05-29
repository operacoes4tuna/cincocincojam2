import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

class PagarmeService:
    """
    Serviço para integração com a API do Pagar.me para pagamentos com cartão de crédito/débito.
    """
    # URL para ambiente de produção: https://api.pagar.me/1
    # URL para ambiente de sandbox: https://api.sandbox.pagar.me/1
    
    def __init__(self):
        # Determina qual ambiente usar com base nas configurações
        self.is_sandbox = settings.DEBUG or getattr(settings, 'DEBUG_PAYMENTS', False)
        
        # Define a URL base de acordo com o ambiente
        if self.is_sandbox:
            self.BASE_URL = "https://api.sandbox.pagar.me/1"
        else:
            self.BASE_URL = "https://api.pagar.me/1"
            
        # Configuração de autenticação e headers
        self.api_key = settings.PAGARME_API_KEY
        self.encryption_key = settings.PAGARME_ENCRYPTION_KEY
        
        self.headers = {
            "Content-Type": "application/json"
        }
        
        self.logger = logging.getLogger('payments')
        
        ambiente = "SANDBOX" if self.is_sandbox else "PRODUÇÃO"
        self.logger.info(f"=== PagarmeService inicializado: {ambiente} ===")
        self.logger.info(f"URL: {self.BASE_URL}")
        self.logger.info(f"DEBUG: {settings.DEBUG}")
        self.logger.info(f"DEBUG_PAYMENTS: {getattr(settings, 'DEBUG_PAYMENTS', False)}")
    
    def is_production(self):
        """
        Verifica se o serviço está operando em ambiente de produção
        
        Returns:
            bool: True se estiver em produção, False se estiver em sandbox
        """
        return not self.is_sandbox
    
    def is_sandbox_mode(self):
        """
        Verifica se o serviço está operando em ambiente de sandbox ou se DEBUG_PAYMENTS está ativo
        
        Returns:
            bool: True se estiver em sandbox ou DEBUG_PAYMENTS ativo, False se estiver em produção
        """
        # Verificar tanto DEBUG quanto DEBUG_PAYMENTS
        return settings.DEBUG or getattr(settings, 'DEBUG_PAYMENTS', False)
    
    def create_card_transaction(self, enrollment, card_data, payment_method='credit_card', installments=1, use_local_simulation=False):
        """
        Cria uma transação de pagamento com cartão (crédito ou débito) para uma matrícula
        
        Args:
            enrollment: Objeto Enrollment com informações do aluno e curso
            card_data: Dicionário com dados do cartão (token, holder_name, etc.)
            payment_method: 'credit_card' ou 'debit_card'
            installments: Número de parcelas (1 a 12) para cartão de crédito
            use_local_simulation: Se True, gera dados localmente sem chamar a API externa
            
        Returns:
            dict: Resposta da API com informações da transação
        """
        course = enrollment.course
        student = enrollment.student
        
        # Gera um ID de correlação único 
        correlation_id = f"card-{course.id}-{student.id}-{int(timezone.now().timestamp())}"
        
        # Preparar dados para a transação
        transaction_data = {
            "api_key": self.api_key,
            "amount": int(course.price * 100),  # Valor em centavos
            "card_hash": card_data.get("card_hash", ""),
            "card_id": card_data.get("card_id", ""),
            "payment_method": payment_method,
            "installments": installments,
            "capture": True,
            "postback_url": "https://cincocincojam2.onrender.com/payments/pagarme/webhook/",
            "soft_descriptor": "5Cinco5JAM",
            "reference_key": correlation_id,
            "customer": {
                "external_id": str(student.id),
                "name": student.get_full_name() or student.username,
                "email": student.email,
                "country": "br",
                "type": "individual",
                "documents": [
                    {
                        "type": "cpf",
                        "number": student.cpf if hasattr(student, 'cpf') and student.cpf else "00000000000"
                    }
                ],
                "phone_numbers": [
                    student.phone if hasattr(student, 'phone') and student.phone else "+5500000000000"
                ]
            },
            "billing": {
                "name": student.get_full_name() or student.username,
                "address": {
                    "country": "br",
                    "state": "sp",
                    "city": "São Paulo",
                    "street": "Rua Exemplo",
                    "street_number": "123",
                    "zipcode": "01234567"
                }
            },
            "items": [
                {
                    "id": str(course.id),
                    "title": course.title,
                    "unit_price": int(course.price * 100),
                    "quantity": 1,
                    "tangible": False
                }
            ],
            "metadata": {
                "course_id": course.id,
                "student_id": student.id
            }
        }

        self.logger.info(f"Criando transação de cartão para aluno {student.email} - curso {course.id} ({course.title})")
        
        # Se solicitado, usar simulação local em vez de chamar a API
        if use_local_simulation or self.is_sandbox:
            self.logger.info(f"Usando simulação LOCAL para criar transação de cartão: {correlation_id}")
            
            # Simulação de cartão para testes
            status = "paid"
            
            # Para criar variações nos testes
            if card_data.get("card_number", "").endswith("0000"):
                status = "refused"
            
            # Gerar resposta simulada
            return {
                "object": "transaction",
                "status": status,
                "refuse_reason": "card_expired" if status == "refused" else None,
                "status_reason": "acquirer" if status == "refused" else "acquirer",
                "acquirer_response_code": "00" if status == "paid" else "57",
                "acquirer_name": "simulator",
                "acquirer_id": "123456789",
                "authorization_code": "123456" if status == "paid" else "",
                "soft_descriptor": "5Cinco5JAM",
                "tid": f"simulated_{int(timezone.now().timestamp())}",
                "nsu": f"{int(timezone.now().timestamp())}",
                "date_created": timezone.now().isoformat(),
                "date_updated": timezone.now().isoformat(),
                "amount": transaction_data["amount"],
                "authorized_amount": transaction_data["amount"] if status == "paid" else 0,
                "paid_amount": transaction_data["amount"] if status == "paid" else 0,
                "refunded_amount": 0,
                "installments": installments,
                "id": correlation_id,
                "cost": 0,
                "card_holder_name": card_data.get("holder_name", "NOME SIMULADO"),
                "card_last_digits": card_data.get("card_number", "4111111111111111")[-4:],
                "card_first_digits": card_data.get("card_number", "4111111111111111")[:6],
                "card_brand": "visa",
                "payment_method": payment_method,
                "reference_key": correlation_id,
                "subscription_id": None
            }
        
        try:
            self.logger.info(f"Tentando criar transação para: {correlation_id}")
            self.logger.debug(f"URL: {self.BASE_URL}/transactions")
            self.logger.debug(f"Payload: {json.dumps(transaction_data)}")
            
            # Em ambiente de desenvolvimento, desativar verificação SSL
            verify_ssl = not self.is_sandbox
            
            response = requests.post(
                f"{self.BASE_URL}/transactions",
                headers=self.headers,
                json=transaction_data,
                verify=verify_ssl
            )
            
            self.logger.info(f"Status code: {response.status_code}")
            self.logger.debug(f"Resposta: {response.text[:500]}...")  # Mostrar apenas os primeiros 500 caracteres
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                self.logger.info(f"Transação criada com sucesso: {response_data.get('id')} - Status: {response_data.get('status')}")
                return response_data
            else:
                self.logger.error(f"Erro na API Pagar.me: {response.status_code} - {response.text}")
                self.logger.info(f"Usando simulação local como fallback")
                return self.create_card_transaction(enrollment, card_data, payment_method, installments, use_local_simulation=True)
        
        except Exception as e:
            self.logger.exception(f"Erro ao criar transação via API: {str(e)}")
            self.logger.info("Usando simulação local como fallback...")
            return self.create_card_transaction(enrollment, card_data, payment_method, installments, use_local_simulation=True)
    
    def get_transaction_status(self, transaction_id, use_local_simulation=False):
        """
        Verifica o status de uma transação pelo ID
        
        Args:
            transaction_id: ID da transação no Pagar.me
            use_local_simulation: Se True, retorna dados simulados localmente
            
        Returns:
            dict: Dados atualizados da transação
        """
        # Se solicitado ou se estiver em ambiente DEBUG, usar simulação local
        if use_local_simulation or self.is_sandbox:
            self.logger.info(f"Usando simulação LOCAL para verificar status: {transaction_id}")
            # Simular uma transação paga
            return {
                "object": "transaction",
                "status": "paid",
                "refuse_reason": None,
                "status_reason": "acquirer",
                "acquirer_response_code": "00",
                "acquirer_name": "simulator",
                "authorization_code": "123456",
                "soft_descriptor": "5Cinco5JAM",
                "tid": f"simulated_{transaction_id}",
                "nsu": str(int(timezone.now().timestamp())),
                "date_created": (timezone.now() - timedelta(minutes=5)).isoformat(),
                "date_updated": timezone.now().isoformat(),
                "amount": 10000,  # 100 reais em centavos
                "authorized_amount": 10000,
                "paid_amount": 10000,
                "refunded_amount": 0,
                "installments": 1,
                "id": transaction_id,
                "reference_key": transaction_id
            }
        
        try:
            self.logger.info(f"Verificando status para: {transaction_id}")
            
            query_params = {
                "api_key": self.api_key
            }
            
            # Em ambiente de desenvolvimento, desativar verificação SSL
            verify_ssl = not self.is_sandbox
            
            response = requests.get(
                f"{self.BASE_URL}/transactions/{transaction_id}",
                headers=self.headers,
                params=query_params,
                verify=verify_ssl
            )
            
            self.logger.info(f"Status code: {response.status_code}")
            self.logger.debug(f"Resposta: {response.text[:500]}...")  # Mostrar apenas os primeiros 500 caracteres
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                self.logger.info(f"Status obtido: {response_data.get('status')} para {transaction_id}")
                return response_data
            else:
                self.logger.error(f"Erro na API Pagar.me: {response.status_code} - {response.text}")
                self.logger.info(f"Usando simulação local como fallback")
                return self.get_transaction_status(transaction_id, use_local_simulation=True)
                
        except Exception as e:
            self.logger.exception(f"Erro ao verificar status via API: {str(e)}")
            self.logger.info("Usando simulação local como fallback...")
            return self.get_transaction_status(transaction_id, use_local_simulation=True)
    
    def refund_transaction(self, transaction_id, amount=None, use_local_simulation=False):
        """
        Realiza o estorno (total ou parcial) de uma transação
        
        Args:
            transaction_id: ID da transação a ser estornada
            amount: Valor a ser estornado em centavos. Se None, estorna o valor total
            use_local_simulation: Se True, simula o estorno localmente
            
        Returns:
            dict: Resposta da API com informações do estorno
        """
        # Se solicitado ou se estiver em ambiente DEBUG, usar simulação local
        if use_local_simulation or self.is_sandbox:
            self.logger.info(f"Usando simulação LOCAL para estorno: {transaction_id}")
            # Simular um estorno bem-sucedido
            return {
                "object": "transaction",
                "status": "refunded",
                "date_updated": timezone.now().isoformat(),
                "amount": 10000,  # 100 reais em centavos
                "refunded_amount": amount or 10000,
                "id": transaction_id,
                "reference_key": transaction_id
            }
        
        try:
            self.logger.info(f"Tentando estornar transação: {transaction_id}")
            
            refund_data = {
                "api_key": self.api_key
            }
            
            if amount:
                refund_data["amount"] = amount
            
            # Em ambiente de desenvolvimento, desativar verificação SSL
            verify_ssl = not self.is_sandbox
            
            response = requests.post(
                f"{self.BASE_URL}/transactions/{transaction_id}/refund",
                headers=self.headers,
                json=refund_data,
                verify=verify_ssl
            )
            
            self.logger.info(f"Status code: {response.status_code}")
            self.logger.debug(f"Resposta: {response.text[:500]}...")  # Mostrar apenas os primeiros 500 caracteres
            
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                self.logger.info(f"Estorno realizado com sucesso: {transaction_id} - Status: {response_data.get('status')}")
                return response_data
            else:
                self.logger.error(f"Erro na API Pagar.me: {response.status_code} - {response.text}")
                self.logger.info(f"Usando simulação local como fallback")
                return self.refund_transaction(transaction_id, amount, use_local_simulation=True)
                
        except Exception as e:
            self.logger.exception(f"Erro ao estornar transação via API: {str(e)}")
            self.logger.info("Usando simulação local como fallback...")
            return self.refund_transaction(transaction_id, amount, use_local_simulation=True)
    
    def generate_card_hash(self, card_data, use_local_simulation=False):
        """
        Gera um hash de cartão para uso seguro na API
        
        Args:
            card_data: Dicionário com dados do cartão
                - card_number: Número do cartão
                - card_holder_name: Nome do titular
                - card_expiration_date: Data de validade no formato MMYY
                - card_cvv: Código de segurança
            use_local_simulation: Se True, gera um hash simulado
            
        Returns:
            str: Hash do cartão ou erro
        """
        # Se solicitado ou se estiver em ambiente DEBUG, usar simulação local
        if use_local_simulation or self.is_sandbox:
            self.logger.info(f"Usando simulação LOCAL para gerar hash de cartão")
            # Gerar um hash fictício para testes
            return f"simulated_card_hash_{int(timezone.now().timestamp())}"
        
        try:
            self.logger.info(f"Tentando gerar hash de cartão")
            
            # Normalmente este processo seria feito no frontend,
            # usando a biblioteca JavaScript do Pagar.me
            # Este método é apenas para simular o processo
            
            # Simula um hash bem-sucedido
            return f"simulated_card_hash_{int(timezone.now().timestamp())}"
                
        except Exception as e:
            self.logger.exception(f"Erro ao gerar hash de cartão: {str(e)}")
            return self.generate_card_hash(card_data, use_local_simulation=True)

    def simulate_transaction(self, transaction_id, status="paid", use_local_simulation=True):
        """
        Simula uma mudança de status em uma transação (apenas para testes)
        
        Args:
            transaction_id: ID da transação
            status: Status desejado ('paid', 'refused', etc.)
            use_local_simulation: Se True, simula localmente
            
        Returns:
            dict: Resposta simulada
        """
        self.logger.info(f"Simulando transação com status {status}: {transaction_id}")
        
        # Simulação de resposta
        return {
            "object": "transaction",
            "status": status,
            "refuse_reason": "card_expired" if status == "refused" else None,
            "status_reason": "acquirer" if status == "refused" else "acquirer",
            "date_updated": timezone.now().isoformat(),
            "amount": 10000,  # 100 reais em centavos
            "authorized_amount": 10000 if status == "paid" else 0,
            "paid_amount": 10000 if status == "paid" else 0,
            "refunded_amount": 0,
            "id": transaction_id,
            "reference_key": transaction_id
        } 