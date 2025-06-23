import io
import base64
import logging
import qrcode
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from payments.openpix_service import OpenPixService
from .models import Invoice, InvoicePixPayment

logger = logging.getLogger('invoices')


class InvoicePixService:
    """
    Serviço especializado para gerar pagamentos Pix vinculados a notas fiscais.
    Integra com OpenPix e fornece fallback local para QR codes.
    """
    
    def __init__(self):
        try:
            self.openpix_service = OpenPixService()
        except Exception as e:
            logger.error(f"Erro ao inicializar OpenPixService: {str(e)}")
            self.openpix_service = None
        self.logger = logger
        
    def create_pix_payment_for_invoice(self, invoice, expiration_minutes=60):
        """
        Cria um pagamento Pix para uma nota fiscal.
        
        Args:
            invoice: Instance do modelo Invoice
            expiration_minutes: Tempo de expiração em minutos (padrão: 60)
            
        Returns:
            dict: Dados do pagamento Pix criado ou erro
        """
        try:
            # Verificar se já existe um pagamento Pix ativo para esta invoice
            existing_pix = InvoicePixPayment.objects.filter(
                invoice=invoice,
                status='PENDING'
            ).first()
            
            if existing_pix and existing_pix.is_active():
                self.logger.info(f"Pagamento Pix já existe para invoice {invoice.id}: {existing_pix.id}")
                return {
                    'success': True,
                    'existing': True,
                    'pix_payment': existing_pix
                }
            
            # Determinar o valor da invoice
            amount = self._get_invoice_amount(invoice)
            if not amount:
                return {
                    'success': False,
                    'error': 'Não foi possível determinar o valor da nota fiscal'
                }
            
            # Gerar ID de correlação único
            correlation_id = f"invoice-{invoice.id}-{int(timezone.now().timestamp())}"
            
            # Calcular data de expiração
            expires_at = timezone.now() + timedelta(minutes=expiration_minutes)
            
            # Criar o InvoicePixPayment primeiro
            pix_payment = InvoicePixPayment.objects.create(
                invoice=invoice,
                correlation_id=correlation_id,
                amount=amount,
                expires_at=expires_at,
                status='PENDING'
            )
            
            # Preparar dados para o OpenPix
            pix_data = self._prepare_pix_data(invoice, amount, correlation_id, expiration_minutes)
            
            # Tentar criar via OpenPix se disponível
            if self.openpix_service:
                try:
                    openpix_response = self.openpix_service.create_charge_dict(
                        pix_data, 
                        correlation_id=correlation_id,
                        use_local_simulation=False
                    )
                    
                    if openpix_response and not openpix_response.get('error'):
                        # Sucesso com OpenPix
                        pix_payment.brcode = openpix_response.get('brCode', '')
                        pix_payment.qrcode_image_url = openpix_response.get('qrCodeImage', '')
                        pix_payment.external_id = openpix_response.get('correlationID', correlation_id)
                        pix_payment.provider_response = openpix_response
                        pix_payment.save()
                        
                        self.logger.info(f"Pagamento Pix criado via OpenPix para invoice {invoice.id}")
                        return {
                            'success': True,
                            'pix_payment': pix_payment,
                            'provider': 'openpix'
                        }
                    else:
                        # Erro com OpenPix, usar fallback local
                        self.logger.warning(f"Falha no OpenPix para invoice {invoice.id}: {openpix_response}")
                        return self._create_local_fallback_pix(pix_payment, amount)
                        
                except Exception as e:
                    self.logger.error(f"Erro ao criar Pix via OpenPix para invoice {invoice.id}: {str(e)}")
                    return self._create_local_fallback_pix(pix_payment, amount)
            else:
                # OpenPix não disponível, usar fallback local
                self.logger.warning(f"OpenPix não disponível para invoice {invoice.id}, usando fallback local")
                return self._create_local_fallback_pix(pix_payment, amount)
                
        except Exception as e:
            self.logger.error(f"Erro geral ao criar pagamento Pix para invoice {invoice.id}: {str(e)}")
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }
    
    def _get_invoice_amount(self, invoice):
        """Obtém o valor da invoice de diferentes fontes."""
        if invoice.amount:
            return invoice.amount
        elif invoice.transaction:
            return invoice.transaction.amount
        elif invoice.singlesale:
            return invoice.singlesale.amount
        return None
    
    def _prepare_pix_data(self, invoice, amount, correlation_id, expiration_minutes):
        """Prepara os dados para criação do Pix."""
        # Obter informações do cliente
        customer_info = self._get_customer_info(invoice)
        
        # Descrição da cobrança
        description = f"Pagamento da Nota Fiscal #{invoice.id}"
        if invoice.transaction:
            description += f" - {invoice.transaction.enrollment.course.title}"
        elif invoice.singlesale:
            description += f" - {invoice.singlesale.description}"
        
        return {
            "correlationID": correlation_id,
            "value": int(amount * 100),  # Valor em centavos
            "comment": description,
            "customer": customer_info,
            "expiresIn": expiration_minutes * 60,  # Converter para segundos
            "additionalInfo": [
                {
                    "key": "Nota Fiscal",
                    "value": f"#{invoice.id}"
                },
                {
                    "key": "Tipo",
                    "value": "Nota Fiscal Eletrônica"
                }
            ]
        }
    
    def _get_customer_info(self, invoice):
        """Obtém informações do cliente da invoice."""
        if invoice.transaction:
            student = invoice.transaction.enrollment.student
            return {
                "name": student.get_full_name() or student.username,
                "email": student.email,
                "phone": getattr(student, 'phone', '') or '',
                "taxID": getattr(student, 'cpf', '') or ''
            }
        elif invoice.singlesale:
            sale = invoice.singlesale
            return {
                "name": sale.customer_name,
                "email": sale.customer_email,
                "phone": sale.customer_phone or '',
                "taxID": sale.customer_cpf or ''
            }
        elif invoice.customer_name:
            return {
                "name": invoice.customer_name,
                "email": invoice.customer_email or '',
                "phone": '',
                "taxID": invoice.customer_tax_id or ''
            }
        else:
            return {
                "name": "Cliente",
                "email": "",
                "phone": "",
                "taxID": ""
            }
    
    def _create_local_fallback_pix(self, pix_payment, amount):
        """Cria um Pix de fallback local quando a API externa falha."""
        try:
            # Gerar um BR Code simulado (formato simplificado para demonstração)
            brcode = self._generate_mock_brcode(pix_payment, amount)
            
            # Gerar QR Code local
            qr_code_data = self._generate_local_qrcode(brcode)
            
            # Atualizar o pix_payment
            pix_payment.brcode = brcode
            pix_payment.qrcode_image_data = qr_code_data
            pix_payment.provider_response = {
                'fallback': True,
                'provider': 'local_simulation',
                'message': 'QR Code gerado localmente como fallback'
            }
            pix_payment.save()
            
            self.logger.info(f"Fallback local criado para invoice {pix_payment.invoice.id}")
            return {
                'success': True,
                'pix_payment': pix_payment,
                'provider': 'local_fallback',
                'warning': 'Usando simulação local - não é um Pix real'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao criar fallback local: {str(e)}")
            pix_payment.status = 'FAILED'
            pix_payment.error_message = f'Erro no fallback local: {str(e)}'
            pix_payment.save()
            
            return {
                'success': False,
                'error': f'Falha no fallback local: {str(e)}'
            }
    
    def _generate_mock_brcode(self, pix_payment, amount):
        """Gera um BR Code mock para demonstração."""
        # Formatar valor para PIX (sem ponto decimal)
        valor_formatado = f"{amount:.2f}".replace('.', '')
        
        # Obter nome do cliente
        customer_name = "Cliente Demo"
        if pix_payment.invoice.transaction:
            customer_name = pix_payment.invoice.transaction.enrollment.student.get_full_name()[:25]
        elif pix_payment.invoice.singlesale:
            customer_name = pix_payment.invoice.singlesale.customer_name[:25]
        
        # Código PIX de demonstração (formato simplificado)
        mock_brcode = f"00020101021226930014br.gov.bcb.pix2571demo.cincocinco.com/pix/{pix_payment.correlation_id}5204000053039865406{valor_formatado}5802BR5925{customer_name}6009Sao Paulo62090505#{pix_payment.invoice.id}6304"
        
        # Calcular um checksum simples (não é o CRC16 real do PIX)
        checksum = str(sum(ord(c) for c in mock_brcode) % 10000).zfill(4)
        return mock_brcode + checksum
    
    def _generate_local_qrcode(self, brcode):
        """Gera um QR Code local e retorna como base64."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(brcode)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_data = buffer.getvalue()
        buffer.close()
        
        return base64.b64encode(img_data).decode('utf-8')
    
    def check_payment_status(self, pix_payment):
        """
        Verifica o status de um pagamento Pix.
        
        Args:
            pix_payment: Instance do InvoicePixPayment
            
        Returns:
            dict: Status atualizado do pagamento
        """
        try:
            if pix_payment.status != 'PENDING':
                return {
                    'success': True,
                    'status': pix_payment.status,
                    'message': f'Pagamento já está como {pix_payment.get_status_display()}'
                }
            
            # Se não está mais ativo (expirado), marcar como expirado
            if not pix_payment.is_active():
                pix_payment.mark_as_expired()
                return {
                    'success': True,
                    'status': 'EXPIRED',
                    'message': 'Pagamento expirado'
                }
            
            # Verificar via OpenPix se não for fallback local
            if pix_payment.provider_response and not pix_payment.provider_response.get('fallback'):
                try:
                    status_response = self.openpix_service.get_charge_status(
                        pix_payment.correlation_id,
                        use_local_simulation=False
                    )
                    
                    if status_response and status_response.get('status') == 'COMPLETED':
                        pix_payment.mark_as_paid()
                        return {
                            'success': True,
                            'status': 'PAID',
                            'message': 'Pagamento confirmado!',
                            'paid_at': pix_payment.paid_at
                        }
                        
                except Exception as e:
                    self.logger.error(f"Erro ao verificar status via OpenPix: {str(e)}")
            
            # Ainda pendente
            return {
                'success': True,
                'status': 'PENDING',
                'message': 'Pagamento ainda pendente'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status do pagamento {pix_payment.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def simulate_payment_confirmation(self, pix_payment):
        """
        Simula a confirmação de um pagamento (apenas para desenvolvimento/teste).
        """
        if settings.DEBUG:
            pix_payment.mark_as_paid()
            self.logger.info(f"Pagamento simulado como pago: {pix_payment.id}")
            return True
        return False 