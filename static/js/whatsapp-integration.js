/**
 * Integração com WhatsApp Web API
 * Permite compartilhar mensagens e arquivos PDF através do WhatsApp
 */

class WhatsAppIntegration {
    constructor() {
        this.apiUrl = 'https://web.whatsapp.com/send';
        this.maxFileSize = 64 * 1024 * 1024; // 64MB limite do WhatsApp
    }

    /**
     * Compartilha uma mensagem simples no WhatsApp
     * @param {string} message - Mensagem a ser compartilhada
     * @param {string} phoneNumber - Número de telefone (opcional)
     */
    shareMessage(message, phoneNumber = '') {
        const encodedMessage = encodeURIComponent(message);
        let url = `${this.apiUrl}?text=${encodedMessage}`;
        
        if (phoneNumber) {
            // Remove caracteres não numéricos do telefone
            const cleanPhone = phoneNumber.replace(/\D/g, '');
            url = `https://wa.me/${cleanPhone}?text=${encodedMessage}`;
        }
        
        window.open(url, '_blank', 'width=600,height=600');
    }

    /**
     * Converte arquivo para base64
     * @param {Blob} file - Arquivo a ser convertido
     * @returns {Promise<string>} - Promise com o arquivo em base64
     */
    async fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(file);
        });
    }

    /**
     * Baixa o PDF da nota fiscal e prepara para compartilhamento
     * @param {string} pdfUrl - URL do PDF
     * @param {string} invoiceId - ID da nota fiscal
     * @param {string} customerName - Nome do cliente
     * @returns {Promise<boolean>} - True se o processo foi bem-sucedido
     */
    async downloadAndSharePdf(pdfUrl, invoiceId, customerName = '') {
        try {
            // Mostrar indicador de carregamento
            this.showLoadingIndicator('Preparando PDF para WhatsApp...');

            // Usar nossa view personalizada para download
            const downloadUrl = `/invoices/whatsapp-pdf/${invoiceId}/`;
            
            // Fazer download do PDF
            const response = await fetch(downloadUrl, {
                credentials: 'same-origin'  // Incluir cookies de autenticação
            });
            
            if (!response.ok) {
                throw new Error(`Erro ao baixar PDF: ${response.status}`);
            }

            const blob = await response.blob();
            
            // Verificar tamanho do arquivo
            if (blob.size > this.maxFileSize) {
                throw new Error('Arquivo muito grande para envio pelo WhatsApp (máximo 64MB)');
            }

            // Criar mensagem de compartilhamento
            const message = this.createInvoiceMessage(invoiceId, customerName, pdfUrl);
            
            // Tentar usar a API nativa de compartilhamento se disponível
            if (navigator.share && navigator.canShare) {
                const file = new File([blob], `nota_fiscal_${invoiceId}.pdf`, { type: 'application/pdf' });
                
                if (navigator.canShare({ files: [file] })) {
                    await navigator.share({
                        title: `Nota Fiscal #${invoiceId}`,
                        text: message,
                        files: [file]
                    });
                    this.hideLoadingIndicator();
                    return true;
                }
            }

            // Fallback: abrir WhatsApp Web com mensagem e instruções
            this.shareMessage(message + '\n\n📎 O PDF será baixado automaticamente. Após o download, anexe o arquivo à conversa no WhatsApp.');
            
            // Iniciar download do PDF automaticamente
            this.downloadFile(blob, `nota_fiscal_${invoiceId}.pdf`);
            
            this.hideLoadingIndicator();
            this.showSuccessMessage('PDF preparado! Anexe o arquivo baixado à conversa no WhatsApp.');
            
            return true;

        } catch (error) {
            console.error('Erro ao compartilhar PDF:', error);
            this.hideLoadingIndicator();
            this.showErrorMessage(`Erro ao preparar PDF: ${error.message}`);
            
            // Fallback: compartilhar apenas a mensagem com link
            const fallbackMessage = this.createInvoiceMessage(invoiceId, customerName, pdfUrl);
            this.shareMessage(fallbackMessage);
            
            return false;
        }
    }

    /**
     * Força o download de um arquivo
     * @param {Blob} blob - Arquivo a ser baixado
     * @param {string} filename - Nome do arquivo
     */
    downloadFile(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Cria mensagem formatada para nota fiscal
     * @param {string} invoiceId - ID da nota fiscal
     * @param {string} customerName - Nome do cliente
     * @param {string} pdfUrl - URL do PDF
     * @returns {string} - Mensagem formatada
     */
    createInvoiceMessage(invoiceId, customerName = '', pdfUrl = '') {
        const greeting = customerName ? `Olá, ${customerName}!` : 'Olá!';
        const company = 'CincoCincoJAM - Escola de Música';
        
        let message = `${greeting}\n\n`;
        message += `📄 Segue sua Nota Fiscal #${invoiceId}\n\n`;
        
        if (pdfUrl) {
            message += `🔗 Link para visualizar/baixar:\n${pdfUrl}\n\n`;
        }
        
        message += `🎵 ${company}\n`;
        message += `📧 Dúvidas? Entre em contato conosco!\n\n`;
        message += `✅ Esta é uma nota fiscal eletrônica válida`;
        
        return message;
    }

    /**
     * Compartilha nota fiscal via WhatsApp
     * @param {string} pdfUrl - URL do PDF
     * @param {string} invoiceId - ID da nota fiscal
     * @param {string} customerName - Nome do cliente (opcional)
     * @param {string} phoneNumber - Número do cliente (opcional)
     */
    async shareInvoice(pdfUrl, invoiceId, customerName = '', phoneNumber = '') {
        try {
            // Se for mobile, tentar envio com PDF
            if (this.isMobile()) {
                await this.downloadAndSharePdf(pdfUrl, invoiceId, customerName);
            } else {
                // Para desktop, baixar PDF e abrir WhatsApp
                await this.downloadAndSharePdf(pdfUrl, invoiceId, customerName);
            }
        } catch (error) {
            console.error('Erro ao compartilhar nota fiscal:', error);
            // Fallback: mensagem simples
            const message = this.createInvoiceMessage(invoiceId, customerName, pdfUrl);
            this.shareMessage(message, phoneNumber);
        }
    }

    /**
     * Detecta se é dispositivo móvel
     * @returns {boolean} - True se for mobile
     */
    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    /**
     * Mostra indicador de carregamento
     * @param {string} message - Mensagem de carregamento
     */
    showLoadingIndicator(message = 'Carregando...') {
        // Remover indicador existente se houver
        this.hideLoadingIndicator();
        
        const loader = document.createElement('div');
        loader.id = 'whatsapp-loader';
        loader.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                color: white;
                font-family: Arial, sans-serif;
            ">
                <div style="
                    background: #25D366;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                ">
                    <div style="
                        border: 3px solid #ffffff;
                        border-top: 3px solid transparent;
                        border-radius: 50%;
                        width: 30px;
                        height: 30px;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 10px;
                    "></div>
                    <div>${message}</div>
                </div>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        `;
        document.body.appendChild(loader);
    }

    /**
     * Remove indicador de carregamento
     */
    hideLoadingIndicator() {
        const loader = document.getElementById('whatsapp-loader');
        if (loader) {
            loader.remove();
        }
    }

    /**
     * Mostra mensagem de sucesso
     * @param {string} message - Mensagem de sucesso
     */
    showSuccessMessage(message) {
        this.showToast(message, 'success');
    }

    /**
     * Mostra mensagem de erro
     * @param {string} message - Mensagem de erro
     */
    showErrorMessage(message) {
        this.showToast(message, 'error');
    }

    /**
     * Mostra toast notification
     * @param {string} message - Mensagem
     * @param {string} type - Tipo (success, error, info)
     */
    showToast(message, type = 'info') {
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            info: '#17a2b8'
        };

        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${colors[type]};
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            font-family: Arial, sans-serif;
            max-width: 300px;
            animation: slideIn 0.3s ease-out;
        `;
        
        toast.innerHTML = message;
        
        // Adicionar CSS de animação
        if (!document.getElementById('toast-animations')) {
            const style = document.createElement('style');
            style.id = 'toast-animations';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        
        // Remover após 5 segundos
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 5000);
    }
}

// Instância global
window.whatsAppIntegration = new WhatsAppIntegration();

/**
 * Função global para compatibilidade com templates existentes
 * @param {string} pdfUrl - URL do PDF
 * @param {string} invoiceId - ID da nota fiscal
 * @param {string} customerName - Nome do cliente (opcional)
 * @param {string} phoneNumber - Telefone do cliente (opcional)
 */
function compartilharWhatsApp(pdfUrl, invoiceId, customerName = '', phoneNumber = '') {
    window.whatsAppIntegration.shareInvoice(pdfUrl, invoiceId, customerName, phoneNumber);
}

/**
 * Função para compartilhar apenas mensagem (versão simplificada)
 * @param {string} message - Mensagem
 * @param {string} phoneNumber - Telefone (opcional)
 */
function compartilharMensagemWhatsApp(message, phoneNumber = '') {
    window.whatsAppIntegration.shareMessage(message, phoneNumber);
} 