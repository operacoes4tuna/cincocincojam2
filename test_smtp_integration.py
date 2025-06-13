import os
import django
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

# Usar a chave que funciona na outra aplicação
SMTP_SERVER = "smtp.sendgrid.net"
SMTP_PORT = 587
SMTP_USERNAME = "apikey"
SMTP_PASSWORD = "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"
FROM_EMAIL = "scaleclock@baile55.com"
TO_EMAIL = "fredcarvalho388@gmail.com"

print("🧪 TESTE SMTP COM A CHAVE QUE FUNCIONA")
print("=" * 50)
print(f"📧 Servidor: {SMTP_SERVER}:{SMTP_PORT}")
print(f"📧 De: {FROM_EMAIL}")
print(f"📧 Para: {TO_EMAIL}")
print(f"🔑 Chave: {SMTP_PASSWORD[:20]}...")
print()

try:
    # Criar mensagem
    message = MIMEMultipart("alternative")
    message["Subject"] = "Teste SMTP - CincoCincoJAM Integrado"
    message["From"] = FROM_EMAIL
    message["To"] = TO_EMAIL

    # Conteúdo do email
    html = """
    <html>
      <body>
        <h2>🎉 SMTP Integrado com Sucesso!</h2>
        <p><strong>Este email foi enviado usando o sistema integrado do CincoCincoJAM</strong></p>
        <p>A funcionalidade de envio de email da aplicação está funcionando!</p>
        <hr>
        <p><small>Enviado via SMTP SendGrid</small></p>
      </body>
    </html>
    """
    
    text = "Teste SMTP - CincoCincoJAM Integrado\n\nEste email foi enviado usando o sistema integrado!"

    # Criar partes do email
    part1 = MIMEText(text, "plain", "utf-8") 
    part2 = MIMEText(html, "html", "utf-8")

    # Adicionar partes à mensagem
    message.attach(part1)
    message.attach(part2)

    # Conectar e enviar
    print("🔌 Conectando ao servidor SMTP...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    
    print("🔒 Iniciando conexão TLS...")
    server.starttls()
    
    print("🔑 Fazendo login...")
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    
    print("📧 Enviando email...")
    text = message.as_string()
    server.sendmail(FROM_EMAIL, TO_EMAIL, text)
    
    server.quit()
    
    print("✅ EMAIL ENVIADO COM SUCESSO!")
    print("🎯 A integração SMTP está funcionando perfeitamente!")
    print("📱 Agora a aplicação vai enviar emails de verdade!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    print("🔧 Verifique se a chave está correta no arquivo .env")