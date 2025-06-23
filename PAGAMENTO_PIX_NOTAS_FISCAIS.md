# 💰 Pagamento Pix para Notas Fiscais

## 📋 Visão Geral

Esta funcionalidade substitui completamente a opção de "Pagar boleto" por um sistema moderno de **Pagamento via Pix com QR Code dinâmico** que é gerado automaticamente após a emissão de notas fiscais via API da NFE.io.

## 🚀 Características Principais

### ✅ **Substituição do Boleto por Pix**
- ❌ Removido: Botões de "Gerar boleto" e "Enviar boleto"
- ✅ Adicionado: Botão "Pagar com Pix" com QR Code dinâmico
- 🔄 Geração automática após aprovação da nota fiscal

### 🎯 **QR Code Dinâmico**
- 📱 QR Code gerado automaticamente com valor da nota fiscal
- 💰 Valor já preenchido - cliente não precisa digitar nada
- ⏰ Expiração configurável (padrão: 60 minutos)
- 🔄 Fallback local se API externa falhar

### 🔒 **Segurança e Confiabilidade**
- 🛡️ Integração com OpenPix (API segura e confiável)
- 🔄 Sistema de fallback local para continuidade
- ✅ Validação de status em tempo real
- 📊 Logs detalhados para auditoria

## 🛠️ Componentes Implementados

### 📄 **Novos Modelos**
```python
# invoices/models.py
class InvoicePixPayment(models.Model):
    - Vinculação com nota fiscal (OneToOne)
    - Status do pagamento (PENDING, PAID, EXPIRED, etc.)
    - QR Code e BR Code
    - Controle de expiração
    - Metadados da API
```

### 🔧 **Serviços**
```python
# invoices/pix_service.py
class InvoicePixService:
    - Criação de pagamentos Pix
    - Integração com OpenPix
    - Fallback local para QR codes
    - Verificação de status
    - Simulação para desenvolvimento
```

### 🌐 **Views e URLs**
```python
# invoices/views.py
- create_invoice_pix_payment()   # Criar Pix para nota fiscal
- invoice_pix_detail()           # Exibir detalhes do Pix
- check_invoice_pix_status()     # Verificar status (AJAX)
- simulate_invoice_pix_payment() # Simular pagamento (dev)
```

### 🎨 **Templates**
```html
<!-- invoices/templates/invoices/invoice_pix_detail.html -->
- Interface moderna para pagamento Pix
- QR Code responsivo
- Código copia e cola
- Verificação automática de status
- Feedback visual em tempo real
```

## 📊 **Fluxo de Uso**

### 1️⃣ **Professor Emite Nota Fiscal**
```
Professor → Emitir NFe → NFE.io processa → Status "approved"
```

### 2️⃣ **Sistema Exibe Botão Pix**
```
Nota Aprovada → Botão "Pagar com Pix" aparece automaticamente
```

### 3️⃣ **Geração do Pagamento Pix**
```
Clique no botão → InvoicePixService → OpenPix API → QR Code gerado
```

### 4️⃣ **Cliente Paga via Pix**
```
Cliente → Escaneia QR Code → App do banco → Paga automaticamente
```

### 5️⃣ **Confirmação Automática**
```
OpenPix → Webhook → Status atualizado → Interface atualizada
```

## 🔧 **Configuração e Instalação**

### 📦 **Dependências Adicionadas**
```bash
pip install qrcode[pil]
```

### 🗄️ **Migração do Banco**
```bash
python manage.py makemigrations invoices
python manage.py migrate
```

### ⚙️ **Configuração OpenPix**
```python
# settings.py
OPENPIX_TOKEN = "sua_chave_openpix"
DEBUG_PAYMENTS = False  # Para produção
```

## 🎯 **Interface do Usuário**

### 📱 **Tela de Detalhes da Nota Fiscal**
- ✅ Botão "Pagar com Pix" (substitui "Gerar boleto")
- 🔄 Status do pagamento em tempo real
- 📊 Histórico de transações

### 💳 **Tela de Pagamento Pix**
- 📱 QR Code responsivo e moderno
- 📋 Código copia e cola
- ⏰ Contador de expiração
- 🔄 Verificação automática de status
- ✅ Confirmação visual quando pago

### 📋 **Lista de Vendas (Professor)**
- 🎯 Botão "Gerar Pix" (substitui "Gerar boleto")
- 📊 Ações em massa para Pix
- 🔄 Status visual dos pagamentos

## 🚦 **Status dos Pagamentos**

| Status | Descrição | Interface |
|--------|-----------|-----------|
| `PENDING` | Aguardando pagamento | ⏳ QR Code ativo + botão verificar |
| `PAID` | Pagamento confirmado | ✅ Badge verde "Pago via Pix" |
| `EXPIRED` | Pagamento expirado | ⏰ Botão "Gerar Novo Pix" |
| `CANCELLED` | Pagamento cancelado | ❌ Status de cancelamento |
| `FAILED` | Erro no pagamento | ⚠️ Mensagem de erro |

## 🛡️ **Segurança e Fallbacks**

### 🔒 **OpenPix (Produção)**
- ✅ API oficial brasileira para Pix
- 🏛️ Certificada pelo Banco Central
- 🔐 Criptografia end-to-end
- 📊 Compliance total com regulamentações

### 🔄 **Fallback Local (Contingência)**
- 🖥️ QR codes gerados localmente
- 🎯 Mantém funcionalidade mesmo se API falhar
- ⚠️ Marcado claramente como simulação
- 🛠️ Ideal para desenvolvimento e testes

### 🧪 **Modo Desenvolvimento**
- 🎮 Botão "Simular Pagamento"
- 📝 Logs detalhados
- 🔍 Debug mode ativado
- ⚡ Resposta instantânea

## 📈 **Benefícios da Implementação**

### 💰 **Para o Negócio**
- ⚡ Pagamentos instantâneos (vs. boletos de 1-3 dias)
- 💯 Taxa de conversão maior
- 🎯 UX moderna e intuitiva
- 📊 Menor abandono de carrinho

### 👥 **Para os Usuários**
- 📱 Pagamento em segundos via app do banco
- 💰 Valor já preenchido automaticamente
- ✅ Confirmação instantânea
- 🔒 Máxima segurança (Pix oficial)

### 🔧 **Para Desenvolvedores**
- 🧩 Código modular e escalável
- 📚 Documentação completa
- 🔄 Fácil manutenção
- 🧪 Testável em desenvolvimento

## 🎮 **Como Testar**

### 🧪 **Em Desenvolvimento**
1. Configure `DEBUG = True`
2. Emita uma nota fiscal
3. Clique em "Pagar com Pix"
4. Use o botão "Simular Pagamento (Dev)"
5. Verifique a mudança de status

### 🏛️ **Em Produção**
1. Configure token OpenPix real
2. Configure `DEBUG_PAYMENTS = False`
3. Teste com Pix real (valores baixos)
4. Monitore logs para validação

## 🔧 **Customização**

### ⏰ **Tempo de Expiração**
```python
# Alterar em invoices/views.py
result = pix_service.create_pix_payment_for_invoice(
    invoice, 
    expiration_minutes=120  # 2 horas ao invés de 1
)
```

### 🎨 **Aparência**
```css
/* Customizar em invoice_pix_detail.html */
.qr-code-container {
    background: your-brand-color;
    border-radius: 20px;
}
```

### 📊 **Logs e Monitoramento**
```python
# settings.py
LOGGING = {
    'loggers': {
        'invoices': {
            'level': 'INFO',  # DEBUG para mais detalhes
        }
    }
}
```

## 🔮 **Próximos Passos**

### 🚀 **Implementações Futuras**
- [ ] Webhooks automáticos do OpenPix
- [ ] Notificações por email quando pago
- [ ] Dashboard de analytics de pagamentos
- [ ] Integração com outros provedores Pix
- [ ] Pagamentos recorrentes via Pix

### 📊 **Melhorias de UX**
- [ ] PWA para página de pagamento
- [ ] Push notifications
- [ ] Compartilhamento direto do QR Code
- [ ] Histórico de pagamentos para cliente

## 🆘 **Solução de Problemas**

### ❓ **Problemas Comuns**

**QR Code não aparece:**
- ✅ Verifique se a nota está "approved"
- ✅ Confirme configuração OpenPix
- ✅ Veja logs em `invoices.log`

**Erro na criação do Pix:**
- ✅ Verifique conexão com internet
- ✅ Confirme token OpenPix válido
- ✅ Use fallback local se necessário

**Status não atualiza:**
- ✅ Verifique JavaScript no template
- ✅ Confirme URLs estão corretas
- ✅ Use botão "Verificar Pagamento"

### 📞 **Suporte Técnico**
- 📧 Email: dev@cincocincojam.com
- 📚 Documentação: `/doc/dev_pagamento_pix.md`
- 🐛 Issues: GitHub repository
- 💬 Slack: #dev-pagamentos

## 📜 **Licença e Créditos**

Esta implementação foi desenvolvida para substituir completamente o sistema de boletos por uma solução moderna de Pix, mantendo a máxima compatibilidade com o sistema existente e seguindo as melhores práticas de desenvolvimento Django.

**Tecnologias utilizadas:**
- 🐍 Django 4.2+
- 💳 OpenPix API
- 📱 QRCode Python Library
- 🎨 Bootstrap 5
- ⚡ JavaScript Vanilla

---
**Desenvolvido com ❤️ para CincoCincoJAM 2.0** 