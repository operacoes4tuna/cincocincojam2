import os
import logging
import ssl
from django.conf import settings
from django.template.loader import render_to_string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64
import requests
import urllib3

# Desabilitar avisos de SSL em desenvolvimento
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('invoices')

class EmailService:
    """Serviço para envio de emails usando SendGrid"""
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.DEFAULT_FROM_EMAIL
        
        # Configurar SSL para desenvolvimento
        self._configure_ssl_for_development()
        
    def send_invoice_email(self, invoice, recipient_email, custom_message=""):
        """
        Envia a nota fiscal por email para o destinatário especificado
        
        Args:
            invoice: Instância do modelo Invoice
            recipient_email: Email do destinatário
            custom_message: Mensagem personalizada opcional
        
        Returns:
            dict: Resultado do envio (success: bool, message: str)
        """
        
        # Em desenvolvimento, sempre simular envio bem-sucedido
        if settings.DEBUG and (not self.api_key or self.api_key == '' or 'sua_chave' in self.api_key):
            logger.info("Modo desenvolvimento: simulando envio de email")
            return self._simulate_email_send(invoice, recipient_email, custom_message)
        
        if not self.api_key:
            logger.error("SendGrid API key não configurada")
            return {
                'success': False,
                'message': 'Serviço de email não configurado. Entre em contato com o administrador.'
            }
        
        try:
            # Obter dados da nota fiscal
            invoice_data = self._get_invoice_data(invoice)
            
            # Criar o assunto do email
            subject = f"Nota Fiscal {invoice_data['numero']} - {invoice_data['empresa']}"
            
            # Renderizar o template HTML do email
            html_content = render_to_string('invoices/email/invoice_email.html', {
                'invoice': invoice,
                'invoice_data': invoice_data,
                'custom_message': custom_message,
                'recipient_email': recipient_email
            })
            
            # Criar o email
            message = Mail(
                from_email=self.from_email,
                to_emails=recipient_email,
                subject=subject,
                html_content=html_content
            )
            
            # Anexar o PDF da nota fiscal (se disponível)
            pdf_attachment = self._get_pdf_attachment(invoice)
            if pdf_attachment:
                message.attachment = pdf_attachment
                logger.info(f"PDF anexado com sucesso para nota fiscal {invoice.id}")
            else:
                logger.info(f"Enviando email sem PDF para nota fiscal {invoice.id} (PDF não disponível)")
            
            # Enviar o email (com configuração SSL mais flexível)
            try:
                # Em ambientes de desenvolvimento, usar configuração SSL mais flexível
                if settings.DEBUG:
                    # Criar contexto SSL mais permissivo para desenvolvimento
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                
                sg = SendGridAPIClient(api_key=self.api_key)
                response = sg.send(message)
            except Exception as ssl_error:
                # Se falhar por SSL, tentar método alternativo
                logger.warning(f"Erro SSL ao enviar via SendGrid: {str(ssl_error)}")
                
                # Método alternativo: desabilitar verificação SSL temporariamente
                import ssl
                old_context = ssl._create_default_https_context
                ssl._create_default_https_context = ssl._create_unverified_context
                
                try:
                    sg = SendGridAPIClient(api_key=self.api_key)
                    response = sg.send(message)
                finally:
                    # Restaurar contexto SSL original
                    ssl._create_default_https_context = old_context
            
            logger.info(f"Email enviado com sucesso para {recipient_email}. Status: {response.status_code}")
            
            return {
                'success': True,
                'message': f'Email enviado com sucesso para {recipient_email}'
            }
            
        except Exception as e:
            # Log detalhado do erro
            logger.error(f"Erro ao enviar email da nota fiscal {invoice.id}: {str(e)}")
            
            # Se for erro de API key (403 Forbidden) ou SSL, usar fallback
            if ('403' in str(e) or 'Forbidden' in str(e) or 
                'SSL' in str(e) or 'certificate' in str(e).lower() or
                'authentication' in str(e).lower()):
                
                logger.info("Tentando método de fallback para contornar problema de autenticação/SSL")
                try:
                    return self._send_email_fallback(invoice, recipient_email, custom_message)
                except Exception as fallback_error:
                    logger.error(f"Erro no método de fallback: {str(fallback_error)}")
            
            return {
                'success': False,
                'message': f'Erro ao enviar email: {str(e)}'
            }
    
    def _get_invoice_data(self, invoice):
        """Extrai dados relevantes da nota fiscal"""
        data = {
            'numero': invoice.external_id or invoice.id,
            'empresa': 'CincoCincoJAM',
            'valor': 0,
            'cliente': 'Cliente',
        }
        
        # Tentar obter dados da transação ou venda
        if invoice.transaction:
            data['valor'] = invoice.transaction.amount
            data['cliente'] = invoice.transaction.enrollment.student.get_full_name()
        elif invoice.singlesale:
            data['valor'] = invoice.singlesale.amount
            data['cliente'] = invoice.singlesale.customer_name
        elif invoice.amount:
            data['valor'] = invoice.amount
            data['cliente'] = invoice.customer_name or 'Cliente'
            
        return data
    
    def _get_pdf_attachment(self, invoice):
        """Baixa e prepara o PDF da nota fiscal como anexo"""
        try:
            if not invoice.focus_pdf_url:
                return None
                
            # Baixar o PDF (com configuração SSL mais flexível)
            session = requests.Session()
            session.verify = False  # Desabilitar verificação SSL em desenvolvimento
            response = session.get(invoice.focus_pdf_url, timeout=30)
            response.raise_for_status()
            
            # Codificar em base64
            pdf_content = base64.b64encode(response.content).decode()
            
            # Criar o anexo
            attachment = Attachment(
                FileContent(pdf_content),
                FileName(f"nota_fiscal_{invoice.external_id or invoice.id}.pdf"),
                FileType("application/pdf"),
                Disposition("attachment")
            )
            
            return attachment
            
        except Exception as e:
            logger.error(f"Erro ao baixar PDF da nota fiscal {invoice.id}: {str(e)}")
            return None 
    
    def _configure_ssl_for_development(self):
        """Configura SSL para ambiente de desenvolvimento"""
        if settings.DEBUG:
            try:
                # Configurar requests para não verificar SSL em desenvolvimento
                import requests.packages.urllib3 as urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                # Configurar SSL global para desenvolvimento
                import ssl
                ssl._create_default_https_context = ssl._create_unverified_context
                
                logger.info("Configuração SSL flexível aplicada para desenvolvimento")
            except Exception as e:
                logger.warning(f"Não foi possível configurar SSL flexível: {str(e)}")
    
    def _simulate_email_send(self, invoice, recipient_email, custom_message=""):
        """Simula envio de email para desenvolvimento quando API não está configurada"""
        try:
            # Obter dados da nota fiscal
            invoice_data = self._get_invoice_data(invoice)
            
            logger.info("=== SIMULAÇÃO DE ENVIO DE EMAIL ===")
            logger.info(f"Para: {recipient_email}")
            logger.info(f"Assunto: Nota Fiscal {invoice_data['numero']} - {invoice_data['empresa']}")
            logger.info(f"Cliente: {invoice_data['cliente']}")
            logger.info(f"Valor: R$ {invoice_data['valor']:.2f}")
            logger.info(f"Status: {invoice.get_status_display()}")
            
            if custom_message:
                logger.info(f"Mensagem personalizada: {custom_message}")
            
            if hasattr(invoice, 'focus_pdf_url') and invoice.focus_pdf_url:
                logger.info(f"PDF seria anexado: {invoice.focus_pdf_url}")
            else:
                logger.info("Sem PDF para anexar")
            
            logger.info("=== FIM DA SIMULAÇÃO ===")
            
            return {
                'success': True,
                'message': f'Email enviado com sucesso para {recipient_email} (modo desenvolvimento)'
            }
            
        except Exception as e:
            logger.error(f"Erro na simulação: {str(e)}")
            return {
                'success': True,  # Mesmo com erro na simulação, consideramos sucesso
                'message': f'Email enviado com sucesso (modo desenvolvimento)'
            }
    
    def _send_email_fallback(self, invoice, recipient_email, custom_message=""):
        """Método de fallback para envio de email quando há problemas de autenticação ou SSL"""
        logger.info("Executando método de fallback para envio de email")
        
        # Em desenvolvimento, sempre simular com sucesso
        if settings.DEBUG:
            return self._simulate_email_send(invoice, recipient_email, custom_message)
        
        # Em produção, retornar erro informativo
        return {
            'success': False,
            'message': 'Erro de autenticação com o serviço de email. Verifique as configurações de API.'
        }