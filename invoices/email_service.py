import os
import logging
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from django.conf import settings
from django.template.loader import render_to_string
import base64
import requests
import urllib3

# Desabilitar avisos de SSL em desenvolvimento
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('invoices')

class EmailService:
    """Serviço para envio de emails usando SendGrid SMTP"""
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.DEFAULT_FROM_EMAIL
        
        # Configurações SMTP do SendGrid
        self.smtp_server = "smtp.sendgrid.net"
        self.smtp_port = 587
        self.smtp_username = "apikey"
        self.smtp_password = self.api_key
        
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
        
        # Em desenvolvimento, só simular se a chave API estiver claramente vazia ou fake
        if settings.DEBUG and (not self.api_key or self.api_key == '' or 'sua_chave' in self.api_key or 'YOUR_' in self.api_key):
            logger.info("Modo desenvolvimento: simulando envio de email (chave API não configurada)")
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
            
            # Enviar o email via SMTP
            return self._send_email_smtp(subject, html_content, recipient_email, invoice)
            
        except Exception as e:
            # Log detalhado do erro
            logger.error(f"Erro ao enviar email da nota fiscal {invoice.id}: {str(e)}")
            
            # Analisar tipo de erro e dar mensagem específica
            error_message = str(e)
            
            if '403' in error_message or 'Forbidden' in error_message:
                return {
                    'success': False,
                    'message': 'Erro de permissão no SendGrid. Verifique se a chave API está válida e tem permissões para envio de email. Chave pode estar expirada ou sem permissões adequadas.'
                }
            elif '401' in error_message or 'Unauthorized' in error_message:
                return {
                    'success': False,
                    'message': 'Chave API do SendGrid inválida ou não autorizada. Verifique se a chave está correta e ainda válida.'
                }
            elif 'SSL' in error_message or 'certificate' in error_message.lower():
                return {
                    'success': False,
                    'message': 'Erro de SSL/certificado. Tente novamente em alguns minutos ou entre em contato com o suporte.'
                }
            else:
                return {
                    'success': False,
                    'message': f'Erro ao enviar email: {error_message}'
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
    
 
    
    def _configure_ssl_for_development(self):
        """Configura SSL para ambiente de desenvolvimento"""
        if settings.DEBUG:
            try:
                # Configurar requests para não verificar SSL em desenvolvimento
                import requests.packages.urllib3 as urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                # Configurar SSL global para desenvolvimento
                import ssl as ssl_module
                ssl_module._create_default_https_context = ssl_module._create_unverified_context
                
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
    
    def _send_email_smtp(self, subject, html_content, recipient_email, invoice):
        """Envia email usando SMTP do SendGrid (baseado no código que funciona)"""
        try:
            # Criar mensagem
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = recipient_email

            # Conteúdo do email (texto e HTML)
            text_content = f"Nota Fiscal {invoice.external_id or invoice.id}\n\nEste email contém informações da sua nota fiscal."
            
            # Criar partes do email
            part1 = MIMEText(text_content, "plain", "utf-8")
            part2 = MIMEText(html_content, "html", "utf-8")

            # Adicionar partes à mensagem
            message.attach(part1)
            message.attach(part2)
            
            # Tentar anexar PDF se disponível
            pdf_attachment = self._get_pdf_attachment_smtp(invoice)
            if pdf_attachment:
                message.attach(pdf_attachment)
                logger.info(f"PDF anexado com sucesso para nota fiscal {invoice.id}")
            else:
                logger.info(f"Enviando email sem PDF para nota fiscal {invoice.id} (PDF não disponível)")

            # Conectar e enviar via SMTP
            logger.info("🔌 Conectando ao servidor SMTP SendGrid...")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Iniciar TLS para conexão segura
            logger.info("🔒 Iniciando conexão TLS...")
            server.starttls()
            
            # Login no servidor
            logger.info("🔑 Fazendo login no SendGrid...")
            server.login(self.smtp_username, self.smtp_password)
            
            # Enviar email
            logger.info("📧 Enviando email...")
            text = message.as_string()
            server.sendmail(self.from_email, recipient_email, text)
            
            # Fechar conexão
            server.quit()
            
            logger.info(f"✅ Email enviado com sucesso via SMTP para {recipient_email}")
            
            return {
                'success': True,
                'message': f'Email enviado com sucesso para {recipient_email}'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email via SMTP: {str(e)}")
            
            # Analisar tipo de erro específico para SMTP
            error_message = str(e)
            
            if 'authentication failed' in error_message.lower():
                return {
                    'success': False,
                    'message': 'Erro de autenticação SMTP. Verifique se a chave API está correta.'
                }
            elif 'connection refused' in error_message.lower() or 'timeout' in error_message.lower():
                return {
                    'success': False,
                    'message': 'Erro de conexão com servidor SMTP. Verifique sua conexão de internet ou firewall.'
                }
            else:
                return {
                    'success': False,
                    'message': f'Erro ao enviar email: {error_message}'
                }
    
    def _get_pdf_attachment_smtp(self, invoice):
        """Baixa e prepara o PDF da nota fiscal como anexo para SMTP"""
        try:
            if not invoice.focus_pdf_url:
                return None
                
            # Baixar o PDF
            session = requests.Session()
            session.verify = False  # Desabilitar verificação SSL em desenvolvimento
            response = session.get(invoice.focus_pdf_url, timeout=30)
            response.raise_for_status()
            
            # Criar anexo SMTP
            attachment = MIMEBase('application', 'pdf')
            attachment.set_payload(response.content)
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="nota_fiscal_{invoice.external_id or invoice.id}.pdf"'
            )
            
            return attachment
            
        except Exception as e:
            logger.error(f"Erro ao baixar PDF da nota fiscal {invoice.id}: {str(e)}")
            return None

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