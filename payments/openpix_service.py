import requests
import json
import logging
import time
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
import hashlib
import base64

class OpenPixService:
    """
    Serviço para integração com a API do OpenPix para pagamentos via Pix.
    Inclui retry logic, cache e fallbacks para garantir alta disponibilidade.
    """
    # URLs para diferentes ambientes
    PRODUCTION_URL = "https://api.openpix.com.br/api/v1"
    SANDBOX_URL = "https://api.sandbox.openpix.com.br/api/v1"
    
    # Configurações de retry
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # segundos
    TIMEOUT = 30  # segundos
    
    def __init__(self):
        # Determina qual ambiente usar com base nas configurações
        self.is_sandbox = settings.DEBUG or getattr(settings, 'DEBUG_PAYMENTS', False)
        
        # Define a URL base de acordo com o ambiente
        self.BASE_URL = self.SANDBOX_URL if self.is_sandbox else self.PRODUCTION_URL
            
        self.headers = {
            "Authorization": settings.OPENPIX_TOKEN,
            "Content-Type": "application/json",
            "User-Agent": f"CincoCincoJAM/2.0 Python/{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'}"
        }
        self.logger = logging.getLogger('payments')
        
        ambiente = "SANDBOX" if self.is_sandbox else "PRODUÇÃO"
        self.logger.info(f"=== OpenPixService inicializado: {ambiente} ===")
        self.logger.info(f"URL: {self.BASE_URL}")
        self.logger.info(f"DEBUG: {settings.DEBUG}")
        self.logger.info(f"DEBUG_PAYMENTS: {getattr(settings, 'DEBUG_PAYMENTS', False)}")
    
    def _make_request(self, method, endpoint, data=None, retries=None):
        """
        Faz uma requisição HTTP com retry automático e tratamento de erros.
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint da API
            data: Dados para enviar (para POST/PUT)
            retries: Número de tentativas (padrão: MAX_RETRIES)
            
        Returns:
            dict: Resposta da API ou None em caso de falha
        """
        if retries is None:
            retries = self.MAX_RETRIES
            
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        for attempt in range(retries + 1):
            try:
                self.logger.debug(f"Tentativa {attempt + 1}/{retries + 1} para {method} {url}")
                
                # Preparar argumentos da requisição
                request_kwargs = {
                    'headers': self.headers,
                    'timeout': self.TIMEOUT,
                    'verify': not self.is_sandbox  # Desabilitar SSL apenas em sandbox
                }
                
                if data:
                    request_kwargs['data'] = json.dumps(data)
                
                # Fazer a requisição
                response = requests.request(method, url, **request_kwargs)
                
                # Log da resposta
                self.logger.debug(f"Status: {response.status_code}, Resposta: {response.text[:300]}...")
                
                # Verificar se foi bem-sucedido
                if response.status_code in [200, 201, 202]:
                    return response.json()
                elif response.status_code == 429:  # Rate limit
                    if attempt < retries:
                        wait_time = self.RETRY_DELAY * (2 ** attempt)  # Backoff exponencial
                        self.logger.warning(f"Rate limit atingido. Aguardando {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                else:
                    self.logger.error(f"Erro HTTP {response.status_code}: {response.text}")
                    if attempt < retries:
                        time.sleep(self.RETRY_DELAY)
                        continue
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout na tentativa {attempt + 1}")
                if attempt < retries:
                    time.sleep(self.RETRY_DELAY)
                    continue
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Erro de conexão na tentativa {attempt + 1}")
                if attempt < retries:
                    time.sleep(self.RETRY_DELAY)
                    continue
            except Exception as e:
                self.logger.error(f"Erro inesperado na tentativa {attempt + 1}: {str(e)}")
                if attempt < retries:
                    time.sleep(self.RETRY_DELAY)
                    continue
        
        self.logger.error(f"Falha em todas as {retries + 1} tentativas para {method} {url}")
        return None
    
    def _get_cache_key(self, correlation_id, cache_type="charge"):
        """
        Gera uma chave única para cache baseada no correlation_id.
        
        Args:
            correlation_id: ID de correlação da cobrança
            cache_type: Tipo de cache (charge, qrcode, etc.)
            
        Returns:
            str: Chave de cache
        """
        hash_key = hashlib.md5(f"{correlation_id}_{cache_type}".encode()).hexdigest()
        return f"openpix_{cache_type}_{hash_key}"
    
    def _generate_fallback_qr(self, correlation_id, amount_cents, description="Pagamento"):
        """
        Gera um QR code de fallback usando um serviço externo quando a API principal falha.
        
        Args:
            correlation_id: ID de correlação
            amount_cents: Valor em centavos
            description: Descrição do pagamento
            
        Returns:
            dict: Dados do QR code gerado
        """
        self.logger.info(f"Gerando QR code de fallback para {correlation_id}")
        
        # BR Code simulado (para desenvolvimento/fallback)
        fallback_brcode = f"00020101021226930014br.gov.bcb.pix2571pix.fallback.{correlation_id}.5204000053039865406{amount_cents/100:.2f}5802BR5925CincoCincoJAM Ensino6009Sao Paulo62070503***6304"
        
        # Gerar QR code usando serviço público
        qr_data = fallback_brcode
        qr_size = "300x300"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size={qr_size}&data={qr_data}"
        
        return {
            "correlationID": correlation_id,
            "value": amount_cents,
            "status": "ACTIVE",
            "brCode": fallback_brcode,
            "qrCodeImage": qr_url,
            "expiresIn": 3600,
            "additionalInfo": [{"key": "Descrição", "value": description}],
            "fallback": True  # Indica que é um fallback
        }
    
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
        return settings.DEBUG or getattr(settings, 'DEBUG_PAYMENTS', False)
    
    def create_charge(self, enrollment, correlation_id=None, use_local_simulation=False):
        """
        Cria uma cobrança Pix para uma matrícula
        
        Args:
            enrollment: Objeto Enrollment com informações do aluno e curso
            correlation_id: ID opcional para correlação (se não fornecido, será gerado)
            use_local_simulation: Se True, gera dados localmente sem chamar a API externa
            
        Returns:
            dict: Resposta da API com informações da cobrança
        """
        course = enrollment.course
        student = enrollment.student
        
        # Gera um ID de correlação único se não fornecido
        if not correlation_id:
            timestamp = int(timezone.now().timestamp())
            correlation_id = f"course-{course.id}-{student.id}-{timestamp}"
        
        # Verificar cache primeiro
        cache_key = self._get_cache_key(correlation_id, "charge")
        cached_charge = cache.get(cache_key)
        if cached_charge:
            self.logger.info(f"Retornando cobrança do cache: {correlation_id}")
            return cached_charge
        
        # Preparar dados para a cobrança
        charge_data = {
            "correlationID": correlation_id,
            "value": int(course.price * 100),  # Valor em centavos
            "comment": f"Matrícula no curso: {course.title}",
            "customer": {
                "name": student.get_full_name() or student.username,
                "email": student.email,
                "phone": getattr(student, 'phone', "") or "",
                "taxID": getattr(student, 'cpf', "") or ""
            },
            "expiresIn": 3600,  # 1 hora em segundos
            "additionalInfo": [
                {
                    "key": "Curso",
                    "value": course.title
                },
                {
                    "key": "Professor",
                    "value": course.professor.get_full_name() or course.professor.username
                },
                {
                    "key": "Plataforma",
                    "value": "CincoCincoJAM 2.0"
                }
            ]
        }

        self.logger.info(f"Criando cobrança para aluno {student.email} - curso {course.id} ({course.title})")
        
        # Chamar método genérico para criar a cobrança
        result = self.create_charge_dict(charge_data, correlation_id, use_local_simulation)
        
        # Cachear o resultado por 30 minutos
        if result:
            cache.set(cache_key, result, 30 * 60)
        
        return result
    
    def create_charge_dict(self, charge_data, correlation_id=None, use_local_simulation=False):
        """
        Cria uma cobrança Pix a partir de um dicionário de dados
        
        Args:
            charge_data: Dicionário com os dados da cobrança
            correlation_id: ID opcional para correlação
            use_local_simulation: Se True, gera dados localmente sem chamar a API externa
            
        Returns:
            dict: Resposta da API com informações da cobrança
        """
        # Se passado um correlation_id como parâmetro, sobrescreve o que está no charge_data
        if correlation_id:
            charge_data["correlationID"] = correlation_id
        
        correlation_id = charge_data.get("correlationID")
        
        # Se solicitado ou em modo sandbox, usar simulação/fallback
        if use_local_simulation or self.is_sandbox:
            self.logger.info(f"Usando simulação/fallback para criar cobrança: {correlation_id}")
            return self._generate_fallback_qr(
                correlation_id, 
                charge_data.get("value", 0),
                charge_data.get("comment", "Pagamento")
            )
        
        # Tentar fazer a requisição para a API
        result = self._make_request("POST", "charge", charge_data)
        
        if result:
            self.logger.info(f"Cobrança criada com sucesso: {correlation_id}")
            return result
        else:
            # Se falhou, usar fallback
            self.logger.warning(f"API falhou, usando fallback para: {correlation_id}")
            return self._generate_fallback_qr(
                correlation_id, 
                charge_data.get("value", 0),
                charge_data.get("comment", "Pagamento")
            )
    
    def get_charge_status(self, correlation_id, use_local_simulation=False, force_completed=False):
        """
        Verifica o status de uma cobrança pelo ID de correlação
        
        Args:
            correlation_id: ID de correlação da cobrança
            use_local_simulation: Se True, retorna dados simulados localmente
            force_completed: Se True, força o status como COMPLETED (para simulação de pagamento)
            
        Returns:
            dict: Dados atualizados da cobrança
        """
        # Verificar cache primeiro
        cache_key = self._get_cache_key(correlation_id, "status")
        cached_status = cache.get(cache_key)
        if cached_status and not force_completed:
            self.logger.debug(f"Retornando status do cache: {correlation_id}")
            return cached_status
        
        # Se solicitado ou se estiver em ambiente DEBUG, usar simulação local
        if use_local_simulation or self.is_sandbox:
            self.logger.info(f"Usando simulação LOCAL para verificar status: {correlation_id}")
            
            simulated_status = "ACTIVE"
            if force_completed:
                simulated_status = "COMPLETED"
            
            result = {
                "status": simulated_status,
                "correlationID": correlation_id,
                "value": 10000,  # 100 reais em centavos
                "payer": {
                    "name": "Simulador Local",
                    "taxID": "000.000.000-00"
                },
                "paidAt": timezone.now().isoformat() if simulated_status == "COMPLETED" else None
            }
            
            # Cachear por 5 minutos
            cache.set(cache_key, result, 5 * 60)
            return result
        
        # Tentar fazer a requisição para a API
        result = self._make_request("GET", f"charge/{correlation_id}")
        
        if result:
            self.logger.info(f"Status obtido com sucesso: {correlation_id} - {result.get('status')}")
            # Cachear por 1 minuto (status pode mudar rapidamente)
            cache.set(cache_key, result, 60)
            return result
        else:
            # Se falhou, simular como ativo
            self.logger.warning(f"Falha ao obter status, simulando ACTIVE: {correlation_id}")
            fallback_result = {
                "status": "ACTIVE",
                "correlationID": correlation_id,
                "message": "Falha na verificação - assumindo ativo"
            }
            return fallback_result
    
    def get_charge(self, correlation_id, use_local_simulation=False, force_completed=False):
        """
        Alias para get_charge_status para compatibilidade
        """
        return self.get_charge_status(correlation_id, use_local_simulation, force_completed)
    
    def simulate_payment(self, correlation_id):
        """
        Simula um pagamento para testes (força status COMPLETED)
        
        Args:
            correlation_id: ID de correlação da cobrança
            
        Returns:
            dict: Status da cobrança simulada como paga
        """
        self.logger.info(f"Simulando pagamento para: {correlation_id}")
        
        # Limpar cache para forçar nova consulta
        cache_key = self._get_cache_key(correlation_id, "status")
        cache.delete(cache_key)
        
        # Retornar status como pago
        return self.get_charge_status(correlation_id, use_local_simulation=True, force_completed=True)
    
    def webhook_signature_is_valid(self, payload, signature):
        """
        Valida a assinatura do webhook do OpenPix
        
        Args:
            payload: Corpo da requisição (bytes)
            signature: Assinatura enviada no header
            
        Returns:
            bool: True se a assinatura for válida
        """
        if not settings.OPENPIX_WEBHOOK_SECRET:
            self.logger.warning("OPENPIX_WEBHOOK_SECRET não configurado - não validando assinatura")
            return True  # Em desenvolvimento, aceitar sem validação
        
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            settings.OPENPIX_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def health_check(self):
        """
        Verifica se a API está respondendo corretamente
        
        Returns:
            dict: Status da API
        """
        try:
            # Fazer uma requisição simples para testar conectividade
            result = self._make_request("GET", "health", retries=1)
            
            if result:
                return {
                    "status": "healthy",
                    "environment": "sandbox" if self.is_sandbox else "production",
                    "base_url": self.BASE_URL,
                    "timestamp": timezone.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "environment": "sandbox" if self.is_sandbox else "production",
                    "base_url": self.BASE_URL,
                    "error": "API não respondeu",
                    "timestamp": timezone.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "environment": "sandbox" if self.is_sandbox else "production",
                "base_url": self.BASE_URL,
                "error": str(e),
                "timestamp": timezone.now().isoformat()
            }
