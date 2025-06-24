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
        
        # Dados do recebedor Fred Carvalho
        self.receiver_data = {
            'name': 'Fred Carvalho',
            'city': 'Rio de Janeiro',
            'pix_key': '15992202706',  # CPF
            'pix_key_type': 'cpf'
        }
        
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
                return self._create_local_fallback_pix(pix_payment, amount)
                
        except Exception as e:
            self.logger.error(f"Erro ao criar pagamento Pix para invoice {invoice.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_invoice_amount(self, invoice):
        """Obtém o valor da invoice."""
        if hasattr(invoice, 'amount') and invoice.amount:
            return float(invoice.amount)
        elif invoice.transaction:
            return float(invoice.transaction.amount)
        elif invoice.singlesale:
            return float(invoice.singlesale.amount)
        return None
    
    def _prepare_pix_data(self, invoice, amount, correlation_id, expiration_minutes):
        """Prepara dados para criação do Pix."""
        # Obter informações do cliente
        customer_info = self._get_customer_info(invoice)
        
        # Descrição da cobrança
        description = f"Nota Fiscal #{invoice.id}"
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
            # Gerar um BR Code seguindo padrão EMV
            brcode = self._generate_emv_brcode(pix_payment, amount)
            
            # Gerar QR Code local
            qr_code_data = self._generate_local_qrcode(brcode)
            
            # Atualizar o pix_payment
            pix_payment.brcode = brcode
            pix_payment.qrcode_image_data = qr_code_data
            pix_payment.provider_response = {
                'fallback': True,
                'provider': 'local_emv_generator',
                'message': 'QR Code PIX gerado localmente seguindo padrão EMV'
            }
            pix_payment.save()
            
            self.logger.info(f"PIX EMV local criado para invoice {pix_payment.invoice.id}")
            return {
                'success': True,
                'pix_payment': pix_payment,
                'provider': 'local_emv',
                'message': 'PIX gerado localmente seguindo padrão EMV do Banco Central'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao criar PIX EMV local: {str(e)}")
            pix_payment.status = 'FAILED'
            pix_payment.error_message = f'Erro no gerador EMV local: {str(e)}'
            pix_payment.save()
            
            return {
                'success': False,
                'error': f'Falha no gerador PIX EMV: {str(e)}'
            }
    
    def _generate_emv_brcode(self, pix_payment, amount):
        """
        Gera um BR Code seguindo padrão EMV do Banco Central.
        Baseado nas especificações técnicas do PIX versão 2.3.0.
        """
        # Dados do recebedor
        receiver_name = self.receiver_data['name'][:25]  # Max 25 caracteres
        receiver_city = self.receiver_data['city'][:15].upper()  # Max 15 caracteres, maiúsculo
        pix_key = self.receiver_data['pix_key']
        
        # Formatação do valor
        amount_str = f"{amount:.2f}"
        
        # Obter descrição do pagamento
        description = f"NF{pix_payment.invoice.id}"
        if pix_payment.invoice.transaction:
            course_name = pix_payment.invoice.transaction.enrollment.course.title[:20]
            description = f"NF{pix_payment.invoice.id}-{course_name}"
        elif pix_payment.invoice.singlesale:
            sale_desc = pix_payment.invoice.singlesale.description[:20]
            description = f"NF{pix_payment.invoice.id}-{sale_desc}"
        
        # Construir payload EMV
        # 00 - Payload Format Indicator
        payload = "00" + "02" + "01"
        
        # 01 - Point of Initiation Method (12 = dinâmico, 11 = estático)
        payload += "01" + "02" + "12"
        
        # 26 - Merchant Account Information (PIX)
        pix_info = "0014br.gov.bcb.pix01" + f"{len(pix_key):02d}" + pix_key
        if description:
            pix_info += "02" + f"{len(description):02d}" + description
        payload += "26" + f"{len(pix_info):02d}" + pix_info
        
        # 52 - Merchant Category Code
        payload += "52" + "04" + "0000"
        
        # 53 - Transaction Currency (986 = BRL)
        payload += "53" + "03" + "986"
        
        # 54 - Transaction Amount
        if amount > 0:
            payload += "54" + f"{len(amount_str):02d}" + amount_str
        
        # 58 - Country Code
        payload += "58" + "02" + "BR"
        
        # 59 - Merchant Name
        payload += "59" + f"{len(receiver_name):02d}" + receiver_name
        
        # 60 - Merchant City
        payload += "60" + f"{len(receiver_city):02d}" + receiver_city
        
        # 62 - Additional Data Field Template
        additional_data = "05" + f"{len(pix_payment.correlation_id[:25]):02d}" + pix_payment.correlation_id[:25]
        payload += "62" + f"{len(additional_data):02d}" + additional_data
        
        # 63 - CRC16 (será calculado)
        payload += "6304"
        
        # Calcular CRC16
        crc = self._calculate_crc16(payload)
        payload += crc
        
        return payload
    
    def _calculate_crc16(self, payload):
        """
        Calcula CRC16 conforme especificação EMV.
        """
        def crc16_ccitt(data):
            crc = 0xFFFF
            for byte in data.encode('utf-8'):
                crc ^= (byte << 8)
                for _ in range(8):
                    if crc & 0x8000:
                        crc = (crc << 1) ^ 0x1021
                    else:
                        crc <<= 1
                    crc &= 0xFFFF
            return crc
        
        crc = crc16_ccitt(payload)
        return f"{crc:04X}"
    
    def _generate_mock_brcode(self, pix_payment, amount):
        """Gera um BR Code mock para demonstração (método antigo mantido para compatibilidade)."""
        # Usar o novo método EMV
        return self._generate_emv_brcode(pix_payment, amount)
    
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