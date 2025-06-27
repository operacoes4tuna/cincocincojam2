# Integração WhatsApp - Compartilhamento de PDFs de Notas Fiscais

## Visão Geral

Esta implementação permite que os usuários compartilhem notas fiscais pelo WhatsApp diretamente através da aplicação. O sistema baixa automaticamente o PDF da nota fiscal e facilita o envio através do WhatsApp Web ou aplicativo nativo.

## Funcionalidades Implementadas

### 1. Download Automático de PDF
- **Endpoint dedicado**: `/invoices/whatsapp-pdf/{invoice_id}/`
- **Autenticação**: Verifica permissões do usuário
- **Proxy de PDF**: Baixa o PDF da API NFE.io com credenciais adequadas
- **Headers CORS**: Permite acesso via JavaScript

### 2. Integração WhatsApp Web API
- **Mensagens formatadas**: Texto profissional com informações da nota fiscal
- **Detecção de dispositivo**: Comportamento adaptado para mobile/desktop
- **Web Share API**: Usa API nativa de compartilhamento quando disponível
- **Fallback inteligente**: Alternativas quando APIs nativas não estão disponíveis

### 3. Interface de Usuário
- **Indicadores visuais**: Loading spinner com cores do WhatsApp
- **Notificações toast**: Feedback de sucesso/erro para o usuário
- **Botões integrados**: Substituição dos botões antigos de WhatsApp
- **Responsividade**: Funciona bem em mobile e desktop

## Arquivos Modificados/Criados

### Backend
- `invoices/views.py`: Nova view `serve_pdf_for_whatsapp()`
- `invoices/urls.py`: Nova rota para servir PDFs

### Frontend
- `static/js/whatsapp-integration.js`: Sistema completo de integração
- `static/css/whatsapp-button.css`: Estilos específicos (já existia)
- `templates/base.html`: Inclusão do novo JavaScript

### Templates Atualizados
- `invoices/templates/invoices/invoice_detail.html`
- `payments/templates/payments/transaction_list.html`

## Como Funciona

### Fluxo Principal

1. **Usuário clica no botão WhatsApp** em uma nota fiscal aprovada
2. **Sistema detecta o dispositivo** (mobile ou desktop)
3. **Download automático** do PDF através da view dedicada
4. **Verificação de tamanho** (máximo 64MB do WhatsApp)
5. **Tentativa de uso da Web Share API** (se disponível no mobile)
6. **Fallback**: Abre WhatsApp Web + download local do PDF
7. **Instrução ao usuário** para anexar o arquivo baixado

### Detecção de Dispositivo

```javascript
isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}
```

### Formatação de Mensagem

```javascript
createInvoiceMessage(invoiceId, customerName, pdfUrl) {
    const greeting = customerName ? `Olá, ${customerName}!` : 'Olá!';
    let message = `${greeting}\n\n`;
    message += `📄 Segue sua Nota Fiscal #${invoiceId}\n\n`;
    message += `🔗 Link: ${pdfUrl}\n\n`;
    message += `🎵 CincoCincoJAM - Escola de Música\n`;
    message += `✅ Esta é uma nota fiscal eletrônica válida`;
    return message;
}
```

## Segurança

### Autenticação e Autorização
- Verifica se usuário está logado
- Valida permissões específicas:
  - **Professores**: Podem acessar notas de seus cursos/vendas
  - **Estudantes**: Podem acessar suas próprias notas
  - **Administradores**: Acesso total

### Validações
- Verifica se a nota fiscal existe
- Confirma se o PDF está disponível
- Valida tamanho do arquivo (limite do WhatsApp)
- Headers CORS seguros

## Uso nos Templates

### Função Principal
```javascript
// Uso básico
compartilharWhatsApp(pdfUrl, invoiceId, customerName, phoneNumber);

// Apenas mensagem
compartilharMensagemWhatsApp(message, phoneNumber);
```

### Exemplo nos Templates
```html
<a href="#" class="btn btn-success" 
   onclick="compartilharWhatsApp('{{ invoice.focus_pdf_url }}', '{{ invoice.id }}', '{{ invoice.customer_name|escapejs }}'); return false;" 
   title="Enviar PDF por WhatsApp">
    <i class="fab fa-whatsapp"></i> Enviar por WhatsApp
</a>
```

## APIs Utilizadas

### Web Share API (Quando Disponível)
```javascript
if (navigator.share && navigator.canShare({ files: [file] })) {
    await navigator.share({
        title: `Nota Fiscal #${invoiceId}`,
        text: message,
        files: [file]
    });
}
```

### WhatsApp Web API
```javascript
const whatsappUrl = `https://wa.me/?text=${encodedMessage}`;
// ou com número específico:
const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodedMessage}`;
```

## Tratamento de Erros

### Cenários Cobertos
1. **PDF não disponível**: Fallback para mensagem com link
2. **Erro de download**: Notificação ao usuário + fallback
3. **Arquivo muito grande**: Alerta sobre limite do WhatsApp
4. **Permissões negadas**: Mensagem de erro e redirecionamento

### Logs de Debug
```javascript
console.error('Erro ao compartilhar PDF:', error);
logger.error(f"Erro ao servir PDF para WhatsApp: {str(e)}")
```

## Configuração

### Dependências
- Font Awesome (para ícones)
- Bootstrap (para estilos)
- Fetch API (nativa do navegador)

### Variáveis de Ambiente
Usa as mesmas configurações da integração NFE.io existente:
- `NFEIO_API_KEY`
- `NFEIO_COMPANY_ID`

## Testes

### Arquivo de Demonstração
- `static/js/whatsapp-demo.html`: Interface para testar funcionalidades
- Demonstra todos os recursos implementados
- Logs de atividade em tempo real

### Como Testar
1. Acesse uma nota fiscal aprovada
2. Clique no botão "Enviar por WhatsApp"
3. Verifique o comportamento conforme o dispositivo:
   - **Mobile**: Tentativa de compartilhamento nativo
   - **Desktop**: WhatsApp Web + download automático

## Melhorias Futuras

### Possíveis Implementações
1. **Cache de PDFs**: Armazenar temporariamente para performance
2. **Compressão**: Reduzir tamanho de PDFs grandes
3. **QR Code**: Gerar códigos QR para compartilhamento offline
4. **Templates personalizáveis**: Permitir customização das mensagens
5. **Analytics**: Rastrear compartilhamentos via WhatsApp

### Integração com APIs de WhatsApp Business
- WhatsApp Business API para empresas
- Envio automático de notas fiscais
- Templates pré-aprovados pelo WhatsApp

## Troubleshooting

### Problemas Comuns

**PDF não baixa:**
- Verificar permissões de usuário
- Confirmar se `focus_pdf_url` está preenchido
- Checar logs do servidor Django

**WhatsApp não abre:**
- Verificar se WhatsApp está instalado (mobile)
- Testar com WhatsApp Web (desktop)
- Confirmar se URLs estão bem formatadas

**Erro de CORS:**
- Verificar headers na view `serve_pdf_for_whatsapp`
- Confirmar configurações de CORS no Django

### Debug
```javascript
// Ativar logs detalhados
window.whatsAppIntegration.debug = true;
```

## Compatibilidade

### Navegadores Suportados
- **Chrome/Edge**: 89+ (Web Share API completa)
- **Firefox**: 86+ (funcionalidades básicas)
- **Safari**: 14+ (Web Share API limitada)
- **Mobile**: Android 6+, iOS 13+

### Dispositivos
- **Desktop**: Todas as funcionalidades via WhatsApp Web
- **Mobile**: Funcionalidades nativas + WhatsApp app
- **Tablet**: Comportamento híbrido conforme o navegador

---

**Data de implementação**: Janeiro 2025  
**Responsável**: Sistema de Notas Fiscais CincoCincoJAM  
**Status**: ✅ Produção 