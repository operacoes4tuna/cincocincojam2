// ... existing code ...

function checkInvoiceStatus(invoiceId) {
    console.log(`[NFe Status Check] Iniciando verificação para nota fiscal ID: ${invoiceId}`);
    
    // URL para verificação do status
    const url = `/invoices/check-status/${invoiceId}/json/`;
    
    fetch(url)
        .then(response => {
            console.log(`[NFe Status Check] Resposta HTTP: ${response.status} ${response.statusText}`);
            
            // Verificar se a resposta é bem-sucedida
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }
            
            // Verificar o tipo de conteúdo antes de tentar fazer o parse como JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            } else {
                // Se não for JSON, tratar como texto
                return response.text().then(text => {
                    console.log('[NFe Status Check] Resposta não é JSON:', text.substring(0, 100) + '...');
                    throw new Error('Resposta não é JSON válido');
                });
            }
        })
        .then(data => {
            console.log('[NFe Status Check] Dados recebidos:', data);
            
            // Atualizar a interface com o status atual
            updateInvoiceStatusUI(invoiceId, data.status, data.message);
            
            // Se ainda estiver em processamento, agendar nova verificação
            if (data.status === 'processing' || data.status === 'pending') {
                setTimeout(() => checkInvoiceStatus(invoiceId), 5000);
            }
        })
        .catch(error => {
            console.log('[NFe Status Check] Erro na verificação:', error);
            
            // Mostrar mensagem de erro na interface
            const statusElement = document.getElementById(`invoice-status-${invoiceId}`);
            if (statusElement) {
                statusElement.innerHTML = `<div class="alert alert-danger">Erro ao verificar status: ${error.message}</div>`;
            }
        });
}

function updateInvoiceStatusUI(invoiceId, status, message) {
    const statusElement = document.getElementById(`invoice-status-${invoiceId}`);
    if (!statusElement) return;
    
    let statusHtml = '';
    let buttonElement = document.querySelector(`[data-invoice-id="${invoiceId}"]`);
    
    // Remover classes de erro do botão
    if (buttonElement) {
        buttonElement.classList.remove('btn-danger', 'btn-success', 'btn-warning');
    }
    
    switch (status) {
        case 'approved':
            statusHtml = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i> Nota fiscal emitida com sucesso!
                    <a href="/invoices/detail/${invoiceId}/" class="btn btn-sm btn-outline-success ms-2">
                        <i class="fas fa-file-invoice"></i> Ver nota
                    </a>
                </div>
            `;
            if (buttonElement) {
                buttonElement.classList.add('btn-success');
                buttonElement.innerHTML = '<i class="fas fa-check-circle"></i> Nota Emitida';
            }
            break;
        case 'processing':
        case 'pending':
            statusHtml = `
                <div class="alert alert-warning">
                    <i class="fas fa-spinner fa-spin"></i> Processando nota fiscal...
                    <small class="d-block mt-1">${message || 'Aguarde enquanto processamos sua nota fiscal.'}</small>
                </div>
            `;
            if (buttonElement) {
                buttonElement.classList.add('btn-warning');
                buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando';
            }
            break;
        case 'error':
            statusHtml = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> Erro na emissão da nota fiscal.
                    <small class="d-block mt-1">${message || 'Ocorreu um erro ao processar sua nota fiscal.'}</small>
                    <a href="/invoices/retry/${invoiceId}/" class="btn btn-sm btn-outline-danger mt-2">
                        <i class="fas fa-redo"></i> Tentar novamente
                    </a>
                </div>
            `;
            if (buttonElement) {
                buttonElement.classList.add('btn-danger');
                buttonElement.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Erro';
            }
            break;
        default:
            statusHtml = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i> Status desconhecido: ${status}
                    <small class="d-block mt-1">${message || ''}</small>
                </div>
            `;
            if (buttonElement) {
                buttonElement.classList.add('btn-info');
                buttonElement.innerHTML = '<i class="fas fa-info-circle"></i> Status Desconhecido';
            }
    }
    
    statusElement.innerHTML = statusHtml;
}

// ... existing code ...