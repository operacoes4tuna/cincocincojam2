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
        
        # Configurações da NFE.io para download de PDF
        self.nfeio_api_key = getattr(settings, 'NFEIO_API_KEY', None)
        self.nfeio_company_id = getattr(settings, 'NFEIO_COMPANY_ID', None)
        self.nfeio_base_url = 'https://api.nfe.io'
        
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
        
        # LOG INICIAL PARA DEBUG
        logger.info(f"=== INICIANDO ENVIO DE EMAIL ===")
        logger.info(f"Invoice ID: {invoice.id}")
        logger.info(f"Status: {invoice.status}")
        logger.info(f"External ID: {invoice.external_id}")
        logger.info(f"Focus PDF URL: {invoice.focus_pdf_url}")
        logger.info(f"Para: {recipient_email}")
        logger.info(f"SendGrid API Key configurada: {'Sim' if self.api_key else 'Não'}")
        
        # Em desenvolvimento, só simular se a chave API estiver claramente vazia ou fake
        if settings.DEBUG and (not self.api_key or self.api_key == '' or 'sua_chave' in self.api_key or 'YOUR_' in self.api_key):
            logger.info("⚠️ Modo desenvolvimento: simulando envio de email (chave API não configurada)")
            return self._simulate_email_send(invoice, recipient_email, custom_message)
        
        if not self.api_key:
            logger.error("❌ SendGrid API key não configurada")
            return {
                'success': False,
                'message': 'Serviço de email não configurado. Entre em contato com o administrador.'
            }
        
        try:
            logger.info("📋 Preparando dados do email...")
            
            # Obter dados da nota fiscal
            invoice_data = self._get_invoice_data(invoice)
            
            # Criar o assunto do email
            subject = f"Nota Fiscal {invoice_data['numero']} - {invoice_data['empresa']}"
            logger.info(f"📧 Assunto: {subject}")
            
            # Renderizar o template HTML do email
            html_content = render_to_string('invoices/email/invoice_email.html', {
                'invoice': invoice,
                'invoice_data': invoice_data,
                'custom_message': custom_message,
                'recipient_email': recipient_email
            })
            
            logger.info("📤 Iniciando envio via SMTP...")
            
            # Enviar o email via SMTP
            return self._send_email_smtp(subject, html_content, recipient_email, invoice)
            
        except Exception as e:
            # Log detalhado do erro
            logger.error(f"❌ Erro ao enviar email da nota fiscal {invoice.id}: {str(e)}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
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
            
            # Testar se o PDF pode ser anexado
            if hasattr(invoice, 'focus_pdf_url') and invoice.focus_pdf_url:
                logger.info(f"PDF disponível: {invoice.focus_pdf_url}")
                
                # Testar o anexo do PDF
                pdf_attachment = self._get_pdf_attachment_smtp(invoice)
                if pdf_attachment:
                    logger.info("✅ PDF seria anexado com sucesso ao email!")
                else:
                    logger.warning("⚠️ PDF disponível mas falha ao criar anexo")
            else:
                logger.info("ℹ️ Sem PDF para anexar")
            
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
            logger.info("📝 Criando estrutura do email...")
            
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
            
            # ✅ ANEXAR PDF - SEMPRE TENTAR SE POSSÍVEL
            logger.info("📎 Verificando se pode anexar PDF...")
            
            # Debug das condições para anexo
            logger.info(f"📋 Condições para anexo:")
            logger.info(f"   - focus_pdf_url: {'✅ Sim' if invoice.focus_pdf_url else '❌ Não'}")
            logger.info(f"   - external_id: {'✅ Sim' if invoice.external_id else '❌ Não'}")
            logger.info(f"   - NFE.io API Key: {'✅ Sim' if self.nfeio_api_key else '❌ Não'}")
            logger.info(f"   - NFE.io Company ID: {'✅ Sim' if self.nfeio_company_id else '❌ Não'}")
            
            # 🚀 PROTOCOLO AGRESSIVO DE ANEXO PDF
            pdf_attachment = None
            
            # SEMPRE tentar protocolo FORÇADO primeiro (funciona melhor)
            logger.info("🎯 Tentando protocolo FORÇADO de anexo...")
            try:
                pdf_attachment = self.force_pdf_attachment(invoice)
            except Exception as force_error:
                logger.error(f"🚨 Protocolo forçado falhou: {str(force_error)}")
            
            # Se protocolo forçado falhou, tentar método normal
            if not pdf_attachment:
                logger.warning("⚠️ Protocolo forçado falhou, tentando método normal...")
                try:
                    pdf_attachment = self._get_pdf_attachment_smtp(invoice)
                except Exception as pdf_error:
                    logger.error(f"🚨 Método normal também falhou: {str(pdf_error)}")
            
            # Anexar se conseguimos o PDF
            if pdf_attachment:
                message.attach(pdf_attachment)
                logger.info(f"🎉 PDF ANEXADO COM SUCESSO para nota fiscal {invoice.id}")
            else:
                logger.error(f"❌ FALHA TOTAL: Não foi possível anexar PDF para nota fiscal {invoice.id}")
                logger.error("💡 Possíveis causas:")
                logger.error(f"   - External ID: {'✅' if invoice.external_id else '❌'} {invoice.external_id}")
                logger.error(f"   - Focus PDF URL: {'✅' if invoice.focus_pdf_url else '❌'} {invoice.focus_pdf_url}")
                logger.error(f"   - NFE.io API Key: {'✅' if self.nfeio_api_key else '❌'}")
                logger.error(f"   - Status: {invoice.status}")
                logger.warning("📧 Email será enviado SEM anexo")

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
            
            # Mensagem de sucesso detalhada
            pdf_status = "com PDF anexado" if pdf_attachment else "sem PDF"
            logger.info(f"✅ Email enviado com sucesso via SMTP para {recipient_email} ({pdf_status})")
            
            return {
                'success': True,
                'message': f'Email enviado com sucesso para {recipient_email} ({pdf_status})'
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
        """
        Baixa e prepara o PDF da nota fiscal como anexo para SMTP.
        Versão FORÇADA - tenta anexar sempre que possível.
        """
        try:
            logger.info(f"🔍 Iniciando processo de anexo PDF para nota fiscal {invoice.id}")
            
            # Verificar se temos URL do PDF
            if not invoice.focus_pdf_url:
                logger.warning(f"❌ Invoice {invoice.id} não possui focus_pdf_url")
                logger.warning("💡 A nota fiscal precisa estar processada/aprovada para ter PDF")
                return None
            
            logger.info(f"✅ PDF URL encontrada: {invoice.focus_pdf_url[:100]}...")
            
            # FORÇAR ANEXO - TENTAR TODOS OS MÉTODOS POSSÍVEIS
            pdf_content = None
            
            # Método 1: API autenticada da NFE.io (se temos credenciais)
            if self.nfeio_api_key and self.nfeio_company_id and invoice.external_id:
                logger.info("🔐 Tentando Método 1: Download via API autenticada NFE.io")
                pdf_content = self._download_pdf_via_api(invoice)
                if pdf_content:
                    logger.info(f"✅ Método 1 SUCESSO: PDF baixado via API (tamanho: {len(pdf_content)} bytes)")
                else:
                    logger.warning("⚠️ Método 1 FALHOU: API NFE.io não funcionou")
            else:
                logger.info("ℹ️ Método 1 IGNORADO: Credenciais NFE.io não disponíveis ou external_id ausente")
            
            # Método 2: Download direto da URL (sempre tentar se Método 1 falhou)
            if not pdf_content:
                logger.info("🌐 Tentando Método 2: Download direto da URL")
                pdf_content = self._download_pdf_direct_content(invoice)
                if pdf_content:
                    logger.info(f"✅ Método 2 SUCESSO: PDF baixado diretamente (tamanho: {len(pdf_content)} bytes)")
                else:
                    logger.warning("⚠️ Método 2 FALHOU: Download direto não funcionou")
            
            # Verificar se conseguimos o PDF
            if not pdf_content:
                logger.error(f"❌ FALHA TOTAL: Não foi possível obter o PDF da nota fiscal {invoice.id}")
                logger.error("💡 Possíveis causas:")
                logger.error("   - URL do PDF inválida ou expirada")
                logger.error("   - Problemas de conectividade")
                logger.error("   - PDF ainda não gerado pela NFE.io")
                return None
            
            # Validar se é realmente um PDF
            if not pdf_content.startswith(b'%PDF'):
                logger.error(f"❌ CONTEÚDO INVÁLIDO: Download não retornou um PDF válido (tamanho: {len(pdf_content)} bytes)")
                logger.error(f"Primeiros 100 bytes: {pdf_content[:100]}")
                return None
            
            # Criar anexo SMTP
            logger.info("📎 Criando anexo SMTP...")
            attachment = MIMEBase('application', 'pdf')
            attachment.set_payload(pdf_content)
            encoders.encode_base64(attachment)
            
            filename = f"nota_fiscal_{invoice.external_id or invoice.id}.pdf"
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )
            
            logger.info(f"🎉 PDF ANEXADO COM SUCESSO para nota fiscal {invoice.id} (arquivo: {filename})")
            return attachment
            
        except Exception as e:
            logger.error(f"🚨 ERRO CRÍTICO ao preparar anexo PDF da nota fiscal {invoice.id}: {str(e)}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return None
    
    def _download_pdf_via_api(self, invoice):
        """
        Baixa o PDF usando a API autenticada da NFE.io
        """
        try:
            if not invoice.external_id:
                logger.warning(f"Invoice {invoice.id} não possui external_id")
                return None
            
            # Construir URL da API
            api_url = f"{self.nfeio_base_url}/v1/companies/{self.nfeio_company_id}/serviceinvoices/{invoice.external_id}/pdf"
            
            # Headers com autenticação
            headers = {
                'Authorization': f'Basic {self.nfeio_api_key}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Baixando PDF via API NFE.io: {api_url}")
            
            # Fazer requisição
            session = requests.Session()
            if settings.DEBUG:
                session.verify = False  # Desabilitar verificação SSL em desenvolvimento
            
            response = session.get(api_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"PDF baixado com sucesso via API para invoice {invoice.id} (tamanho: {len(response.content)} bytes)")
                return response.content
            else:
                logger.warning(f"Falha no download via API. Status: {response.status_code}, Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Erro no download via API NFE.io: {str(e)}")
            return None
    
    def _download_pdf_direct_content(self, invoice):
        """
        Tenta baixar o PDF diretamente da URL (método de fallback)
        """
        try:
            logger.info(f"Tentando download direto do PDF: {invoice.focus_pdf_url}")
            
            # Configurar sessão
            session = requests.Session()
            if settings.DEBUG:
                session.verify = False  # Desabilitar verificação SSL em desenvolvimento
            
            # Tentar com diferentes headers
            headers_options = [
                # Tentar com autenticação da NFE.io se disponível
                {
                    'Authorization': f'Basic {self.nfeio_api_key}',
                    'User-Agent': 'CincoCincoJAM/1.0'
                } if self.nfeio_api_key else {},
                # Tentar sem autenticação
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                # Tentar sem headers extras
                {}
            ]
            
            for i, headers in enumerate(headers_options):
                try:
                    logger.info(f"Tentativa {i+1} de download direto")
                    response = session.get(invoice.focus_pdf_url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        # Verificar se é realmente um PDF
                        if response.content.startswith(b'%PDF'):
                            logger.info(f"PDF baixado com sucesso (tentativa {i+1}, tamanho: {len(response.content)} bytes)")
                            return response.content
                        else:
                            logger.warning(f"Resposta não é um PDF válido (tentativa {i+1})")
                    else:
                        logger.warning(f"Status {response.status_code} na tentativa {i+1}")
                        
                except Exception as e:
                    logger.warning(f"Erro na tentativa {i+1}: {str(e)}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Erro no download direto: {str(e)}")
            return None
    
    def _download_pdf_direct(self, invoice):
        """
        Método legado mantido para compatibilidade
        """
        try:
            pdf_content = self._download_pdf_direct_content(invoice)
            if not pdf_content:
                return None
            
            # Criar anexo SMTP
            attachment = MIMEBase('application', 'pdf')
            attachment.set_payload(pdf_content)
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="nota_fiscal_{invoice.external_id or invoice.id}.pdf"'
            )
            
            return attachment
            
        except Exception as e:
            logger.error(f"Erro no método legado: {str(e)}")
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

    def debug_pdf_attachment(self, invoice):
        """
        Método para debug detalhado do processo de anexo do PDF.
        Use este método para investigar problemas.
        """
        logger.info("=== DEBUG PDF ATTACHMENT ===")
        logger.info(f"Invoice ID: {invoice.id}")
        logger.info(f"External ID: {invoice.external_id}")
        logger.info(f"Status: {invoice.status}")
        logger.info(f"Focus Status: {invoice.focus_status}")
        logger.info(f"Focus PDF URL: {invoice.focus_pdf_url}")
        
        # Verificar credenciais NFE.io
        logger.info(f"NFE.io API Key configurada: {'Sim' if self.nfeio_api_key else 'Não'}")
        logger.info(f"NFE.io Company ID: {self.nfeio_company_id}")
        
        if invoice.focus_pdf_url:
            # Tentar download para debug
            logger.info("Tentando debug do download...")
            
            # Método 1: Via API
            if self.nfeio_api_key and self.nfeio_company_id and invoice.external_id:
                logger.info("Testando download via API NFE.io...")
                pdf_content = self._download_pdf_via_api(invoice)
                if pdf_content:
                    logger.info(f"✅ Download via API bem-sucedido (tamanho: {len(pdf_content)} bytes)")
                else:
                    logger.warning("❌ Download via API falhou")
            
            # Método 2: Download direto
            logger.info("Testando download direto...")
            pdf_content = self._download_pdf_direct_content(invoice)
            if pdf_content:
                logger.info(f"✅ Download direto bem-sucedido (tamanho: {len(pdf_content)} bytes)")
            else:
                logger.warning("❌ Download direto falhou")
        else:
            logger.warning("❌ Invoice não possui focus_pdf_url")
        
        logger.info("=== FIM DEBUG ===")
        
        # Tentar criar anexo real
        attachment = self._get_pdf_attachment_smtp(invoice)
        if attachment:
            logger.info("✅ Anexo criado com sucesso!")
            return True
        else:
            logger.warning("❌ Falha ao criar anexo")
            return False

    def force_pdf_attachment(self, invoice):
        """
        Método FORÇADO para anexar PDF - tenta TODAS as estratégias possíveis.
        Este método tenta anexar o PDF mesmo quando focus_pdf_url não existe.
        """
        logger.info(f"🚀 FORÇANDO ANEXO DE PDF para invoice {invoice.id}")
        
        # ESTRATÉGIA 1: Buscar direto na API NFE.io (mesmo sem focus_pdf_url)
        if invoice.external_id and self.nfeio_api_key:
            logger.info("🎯 Estratégia 1: Buscar PDF direto na API NFE.io")
            pdf_content = self.get_pdf_from_nfeio_api(invoice)
            if pdf_content:
                logger.info("✅ Estratégia 1 SUCESSO: PDF obtido da API")
                return self._create_pdf_attachment(pdf_content, invoice)
            else:
                logger.warning("⚠️ Estratégia 1 FALHOU: API NFE.io não retornou PDF")
        
        # ESTRATÉGIA 2: Usar focus_pdf_url se existir
        if invoice.focus_pdf_url:
            logger.info("🎯 Estratégia 2: Download da focus_pdf_url")
            logger.info(f"📂 URL do PDF: {invoice.focus_pdf_url}")
            
            try:
                import requests
                
                session = requests.Session()
                if settings.DEBUG:
                    session.verify = False
                
                # Headers básicos
                headers = {
                    'User-Agent': 'CincoCincoJAM/1.0 Email Service',
                    'Accept': 'application/pdf,*/*'
                }
                
                # Se temos credenciais NFE.io, usar
                if self.nfeio_api_key:
                    headers['Authorization'] = f'Basic {self.nfeio_api_key}'
                    logger.info("🔐 Usando credenciais NFE.io")
                
                logger.info("⬇️ Fazendo download do PDF...")
                response = session.get(invoice.focus_pdf_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    content = response.content
                    if content and len(content) > 100 and content.startswith(b'%PDF'):
                        logger.info(f"✅ Estratégia 2 SUCESSO: PDF baixado ({len(content)} bytes)")
                        return self._create_pdf_attachment(content, invoice)
                
                logger.warning(f"⚠️ Estratégia 2 FALHOU: Status {response.status_code}")
                
            except Exception as e:
                logger.error(f"🚨 Erro na Estratégia 2: {str(e)}")
        
        # ESTRATÉGIA 3: Buscar por outros métodos (se necessário)
        logger.error(f"❌ TODAS AS ESTRATÉGIAS FALHARAM para invoice {invoice.id}")
        return None
    
    def _create_pdf_attachment(self, pdf_content, invoice):
        """
        Cria o anexo SMTP a partir do conteúdo do PDF
        """
        try:
            attachment = MIMEBase('application', 'pdf')
            attachment.set_payload(pdf_content)
            encoders.encode_base64(attachment)
            
            filename = f"nota_fiscal_{invoice.external_id or invoice.id}.pdf"
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )
            
            logger.info(f"🎉 ANEXO CRIADO COM SUCESSO: {filename}")
            return attachment
            
        except Exception as e:
            logger.error(f"🚨 Erro ao criar anexo: {str(e)}")
            return None

    def get_pdf_from_nfeio_api(self, invoice):
        """
        Busca o PDF diretamente da API NFE.io, mesmo quando focus_pdf_url não está preenchido.
        Este método tenta obter o PDF usando apenas o external_id.
        """
        try:
            if not invoice.external_id:
                logger.warning(f"❌ Invoice {invoice.id} não possui external_id - impossível buscar na API")
                return None
                
            if not self.nfeio_api_key or not self.nfeio_company_id:
                logger.warning(f"❌ Credenciais NFE.io não configuradas")
                return None
            
            logger.info(f"🔍 Buscando PDF na API NFE.io para external_id: {invoice.external_id}")
            
            # Construir URL da API
            api_url = f"{self.nfeio_base_url}/v1/companies/{self.nfeio_company_id}/serviceinvoices/{invoice.external_id}/pdf"
            
            # Headers com autenticação
            headers = {
                'Authorization': f'Basic {self.nfeio_api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'CincoCincoJAM/1.0'
            }
            
            logger.info(f"📡 Requisição API: GET {api_url}")
            
            # Fazer requisição
            session = requests.Session()
            if settings.DEBUG:
                session.verify = False
            
            response = session.get(api_url, headers=headers, timeout=30)
            
            logger.info(f"📊 Status da resposta: {response.status_code}")
            
            if response.status_code == 200:
                content = response.content
                
                # Verificar se é um PDF válido
                if content and len(content) > 100 and content.startswith(b'%PDF'):
                    logger.info(f"✅ PDF obtido com sucesso da API NFE.io (tamanho: {len(content)} bytes)")
                    
                    # Atualizar o focus_pdf_url no banco se não existir
                    if not invoice.focus_pdf_url:
                        invoice.focus_pdf_url = api_url
                        invoice.save()
                        logger.info(f"💾 focus_pdf_url atualizado no banco de dados")
                    
                    return content
                else:
                    logger.error(f"❌ Resposta da API não é um PDF válido")
                    logger.error(f"Tamanho: {len(content) if content else 0} bytes")
                    if content:
                        logger.error(f"Primeiros 50 bytes: {content[:50]}")
                    return None
            else:
                logger.error(f"❌ Erro na API NFE.io: {response.status_code}")
                logger.error(f"Resposta: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"🚨 Erro ao buscar PDF na API NFE.io: {str(e)}")
            return None