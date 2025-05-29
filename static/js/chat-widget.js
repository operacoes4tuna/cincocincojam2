// Funcionalidade do widget de chat persistente
document.addEventListener('DOMContentLoaded', function() {
    // Elementos do widget
    const chatButton = document.getElementById('chat-widget-button');
    const chatPopup = document.getElementById('chat-widget-popup');
    const chatClose = document.getElementById('chat-widget-close');
    const chatExpand = document.getElementById('chat-widget-expand');
    const chatForm = document.getElementById('chat-widget-form');
    const chatInput = document.getElementById('chat-widget-input');
    const chatMessages = document.getElementById('chat-widget-messages');
    
    // Estado do widget
    let isExpanded = localStorage.getItem('chat_expanded') === 'true';
    let isVisible = localStorage.getItem('chat_visible') === 'true';
    let isInitialized = false;
    
    // Variável para armazenar o ID da sessão
    let sessionId = localStorage.getItem('chat_session_id');
    
    // Função para obter o token CSRF
    function getCsrfToken() {
        // Tenta obter o token da tag meta
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        // Se não encontrou na meta tag, tenta obter do cookie
        if (!csrfToken) {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith('csrftoken=')) {
                    return cookie.substring('csrftoken='.length);
                }
            }
        }
        
        return csrfToken;
    }
    
    // Inicialização
    function init() {
        // Limpa sessão antiga se solicitado (para debugging)
        if (window.location.search.includes('clear_chat_session=1')) {
            console.log("Limpando sessão de chat...");
            localStorage.removeItem('chat_session_id');
            sessionId = null;
        }
        
        // Configura os eventos
        chatButton.addEventListener('click', openChat);
        chatClose.addEventListener('click', closeChat);
        chatExpand.addEventListener('click', toggleExpand);
        chatForm.addEventListener('submit', handleFormSubmit);
        
        // Restaura o estado de expansão
        if (isExpanded) {
            applyExpandedState();
        }
        
        // Restaura o estado de visibilidade
        if (isVisible) {
            chatPopup.classList.add('active');
        }
        
        // Verifica se temos uma sessão existente
        if (sessionId) {
            loadChatHistory(sessionId);
            
            // Se o chat estava visível, foca no campo de entrada
            if (isVisible) {
                setTimeout(() => chatInput.focus(), 300);
            }
        }
    }
    
    // Abrir o chat
    function openChat() {
        chatPopup.classList.add('active');
        isVisible = true;
        localStorage.setItem('chat_visible', 'true');
        
        if (!sessionId) {
            createNewSession();
        } else if (!isInitialized) {
            loadChatHistory(sessionId);
        }
        
        chatInput.focus();
    }
    
    // Fechar o chat
    function closeChat() {
        chatPopup.classList.remove('active');
        isVisible = false;
        localStorage.setItem('chat_visible', 'false');
    }
    
    // Expandir/contrair o chat
    function toggleExpand() {
        isExpanded = !isExpanded;
        
        if (isExpanded) {
            applyExpandedState();
        } else {
            applyContractedState();
        }
        
        // Salva o estado de expansão
        localStorage.setItem('chat_expanded', isExpanded.toString());
        
        setTimeout(() => chatInput.focus(), 300);
    }
    
    // Aplicar estado expandido - versão maior do chat
    function applyExpandedState() {
        // Adiciona classes ao chat
        chatPopup.classList.add('expanded');
        chatExpand.classList.add('is-expanded');
        
        // Atualiza atributos e ícones
        chatExpand.setAttribute('title', 'Contrair chat');
        chatExpand.querySelector('i').classList.remove('fa-expand-alt');
        chatExpand.querySelector('i').classList.add('fa-compress-alt');
        
        // Centraliza o scroll no conteúdo da janela
        if (chatMessages.lastElementChild) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
    
    // Aplicar estado contraído - retorna ao tamanho normal
    function applyContractedState() {
        // Remove classes do chat
        chatPopup.classList.remove('expanded');
        chatExpand.classList.remove('is-expanded');
        
        // Atualiza atributos e ícones
        chatExpand.setAttribute('title', 'Expandir chat');
        chatExpand.querySelector('i').classList.remove('fa-compress-alt');
        chatExpand.querySelector('i').classList.add('fa-expand-alt');
    }
    
    // Manipular o envio do formulário
    function handleFormSubmit(event) {
        event.preventDefault();
        
        const messageText = chatInput.value.trim();
        if (!messageText) return;
        
        // Remover apenas a mensagem inicial de boas-vindas se ela existir
        const welcomeMessage = chatMessages.querySelector('.text-center.text-muted.my-4');
        if (welcomeMessage) {
            chatMessages.removeChild(welcomeMessage);
        }
        
        // Cria o elemento de mensagem do usuário
        const userMessageElement = document.createElement('div');
        userMessageElement.className = 'chat-message user-message';
        userMessageElement.textContent = messageText;
        chatMessages.appendChild(userMessageElement);
        
        // Limpa o campo de entrada
        chatInput.value = '';
        
        // Mostra o indicador de digitação
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'chat-message bot-message';
        typingIndicator.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Digitando...';
        chatMessages.appendChild(typingIndicator);
        
        // Rola para o final
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Verifica se temos uma sessão
        if (!sessionId) {
            createNewSession(() => {
                // Depois que a sessão for criada, envia a mensagem
                sendDirectMessage(messageText, typingIndicator);
            });
        } else {
            // Se já temos uma sessão, envia a mensagem diretamente
            sendDirectMessage(messageText, typingIndicator);
        }
    }
    
    // Envia a mensagem diretamente
    function sendDirectMessage(message, typingIndicator) {
        const csrfToken = getCsrfToken();
        
        // Usar fetch com FormData
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('message', message);
        
        // Configurações da requisição
        const fetchOptions = {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        // Adicionar o token CSRF à requisição se disponível
        if (csrfToken) {
            fetchOptions.headers['X-CSRFToken'] = csrfToken;
        }
        
        console.log("Enviando mensagem para sessão:", sessionId);
        
        fetch('/assistant/api/message/send/', fetchOptions)
            .then(response => {
                if (!response.ok) {
                    if (response.status === 404) {
                        console.error("Endpoint não encontrado. Verifique a URL.");
                        // Se a sessão não for encontrada, tentar criar uma nova
                        if (sessionId) {
                            console.log("Tentando criar uma nova sessão...");
                            localStorage.removeItem('chat_session_id');
                            sessionId = null;
                            createNewSession(() => {
                                sendDirectMessage(message, typingIndicator);
                            });
                            return Promise.reject("Sessão não encontrada. Criando nova sessão.");
                        }
                    }
                    return Promise.reject(`Erro HTTP: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Remove o indicador de digitação
                if (typingIndicator && typingIndicator.parentNode === chatMessages) {
                    chatMessages.removeChild(typingIndicator);
                }
                
                if (data.success) {
                    // Cria a resposta do bot com suporte a markdown
                    const botMessageElement = document.createElement('div');
                    botMessageElement.className = 'chat-message bot-message';
                    
                    // Converte markdown em HTML
                    let formattedResponse = data.response;
                    
                    // Formatação básica de markdown
                    // Títulos
                    formattedResponse = formattedResponse.replace(/^### (.*$)/gim, '<h3>$1</h3>');
                    formattedResponse = formattedResponse.replace(/^## (.*$)/gim, '<h2>$1</h2>');
                    formattedResponse = formattedResponse.replace(/^# (.*$)/gim, '<h1>$1</h1>');
                    
                    // Negrito e itálico
                    formattedResponse = formattedResponse.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
                    formattedResponse = formattedResponse.replace(/\*(.*?)\*/gim, '<em>$1</em>');
                    
                    // Listas
                    formattedResponse = formattedResponse.replace(/^\d+\. (.*$)/gim, '<ol><li>$1</li></ol>');
                    formattedResponse = formattedResponse.replace(/^\* (.*$)/gim, '<ul><li>$1</li></ul>');
                    formattedResponse = formattedResponse.replace(/^- (.*$)/gim, '<ul><li>$1</li></ul>');
                    
                    // Citações
                    formattedResponse = formattedResponse.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');
                    
                    // Links
                    formattedResponse = formattedResponse.replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank">$1</a>');
                    
                    // Código inline
                    formattedResponse = formattedResponse.replace(/`([^`]+)`/gim, '<code>$1</code>');
                    
                    // Blocos de código
                    formattedResponse = formattedResponse.replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>');
                    
                    // Parágrafos - substituir quebras de linha por <br>
                    formattedResponse = formattedResponse.replace(/\n/gim, '<br>');
                    
                    botMessageElement.innerHTML = formattedResponse;
                    chatMessages.appendChild(botMessageElement);
                    
                    // Rola para o final
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            })
            .catch(error => {
                console.error('Erro ao enviar mensagem:', error);
                
                // Remove o indicador de digitação se ainda estiver presente
                if (typingIndicator && typingIndicator.parentNode === chatMessages) {
                    chatMessages.removeChild(typingIndicator);
                }
                
                // Adiciona mensagem de erro
                const errorElement = document.createElement('div');
                errorElement.className = 'chat-message bot-message error';
                errorElement.innerHTML = 'Desculpe, ocorreu um erro. Por favor, tente novamente mais tarde.';
                chatMessages.appendChild(errorElement);
                
                // Rola para o final
                chatMessages.scrollTop = chatMessages.scrollHeight;
            });
    }
    
    // Função para criar uma nova sessão
    function createNewSession(callback) {
        const csrfToken = getCsrfToken();
        
        // Usar FormData para a requisição
        const formData = new FormData();
        
        // Configurações da requisição
        const fetchOptions = {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        // Adicionar o token CSRF à requisição se disponível
        if (csrfToken) {
            fetchOptions.headers['X-CSRFToken'] = csrfToken;
        }
        
        console.log("Criando nova sessão...");
        
        fetch('/assistant/api/session/create/', fetchOptions)
            .then(response => {
                if (!response.ok) {
                    console.error(`Erro HTTP: ${response.status}`);
                    return Promise.reject(`Erro HTTP: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    console.log("Sessão criada com ID:", data.session_id);
                    sessionId = data.session_id;
                    localStorage.setItem('chat_session_id', sessionId);
                    isInitialized = true;
                    
                    if (typeof callback === 'function') {
                        callback();
                    }
                }
            })
            .catch(error => {
                console.error('Erro ao criar sessão:', error);
                
                // Mostra mensagem de erro
                chatMessages.innerHTML = '';
                const errorElement = document.createElement('div');
                errorElement.className = 'text-center text-danger my-3';
                errorElement.textContent = 'Não foi possível iniciar o chat. Por favor, tente novamente mais tarde.';
                chatMessages.appendChild(errorElement);
            });
    }
    
    // Função para carregar o histórico de mensagens
    function loadChatHistory(sessionId) {
        // Mostra um indicador de carregamento apenas se o chat estiver vazio
        let loadingIndicator = null;
        if (chatMessages.childElementCount === 0) {
            loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'text-center text-muted my-3';
            loadingIndicator.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Carregando mensagens...';
            chatMessages.appendChild(loadingIndicator);
        }
        
        // Adicionar timestamp para evitar cache
        const timestamp = Date.now();
        const url = `/assistant/api/message/history/?session_id=${sessionId}&_=${timestamp}`;
        
        console.log("Carregando histórico da sessão:", sessionId);

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    if (response.status === 404) {
                        console.error("Sessão não encontrada ou endpoint inválido");
                        // Se a sessão não for encontrada, criar uma nova
                        localStorage.removeItem('chat_session_id');
                        sessionId = null;
                        createNewSession();
                        return Promise.reject("Sessão não encontrada");
                    }
                    return Promise.reject(`Erro HTTP: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (loadingIndicator && loadingIndicator.parentNode === chatMessages) {
                    chatMessages.removeChild(loadingIndicator);
                }
                
                if (data.success) {
                    // Verifica se já tem mensagens na interface
                    const hasExistingMessages = Array.from(chatMessages.children).some(
                        child => child.classList.contains('chat-message')
                    );
                    
                    // Se não tiver mensagens na interface nem no banco
                    if (!hasExistingMessages && data.messages.length === 0) {
                        // Mostra a mensagem de boas-vindas apenas se não houver mensagens
                        // e não existirem já na interface
                        chatMessages.innerHTML = '';
                        const welcomeElement = document.createElement('div');
                        welcomeElement.className = 'text-center text-muted my-4';
                        welcomeElement.innerHTML = '<p>Olá! Como posso ajudar?</p>';
                        chatMessages.appendChild(welcomeElement);
                    } 
                    // Se não tiver mensagens na interface mas tiver no banco
                    else if (!hasExistingMessages && data.messages.length > 0) {
                        // Limpa e adiciona as mensagens do histórico
                        chatMessages.innerHTML = '';
                        data.messages.forEach(msg => {
                            const messageElement = document.createElement('div');
                            messageElement.className = `chat-message ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`;
                            messageElement.textContent = msg.content;
                            chatMessages.appendChild(messageElement);
                        });
                        // Rola para o final
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                    // Se já tiver mensagens na interface, não fazemos nada
                    // para preservar a conversa atual
                    
                    isInitialized = true;
                }
            })
            .catch(error => {
                console.error('Erro ao carregar histórico:', error);
                
                if (loadingIndicator && loadingIndicator.parentNode === chatMessages) {
                    chatMessages.removeChild(loadingIndicator);
                }
                
                // Se não houver mensagens, mostra a mensagem de boas-vindas
                if (chatMessages.childElementCount === 0) {
                    const welcomeElement = document.createElement('div');
                    welcomeElement.className = 'text-center text-muted my-4';
                    welcomeElement.innerHTML = '<p>Olá! Como posso ajudar?</p>';
                    chatMessages.appendChild(welcomeElement);
                }
            });
    }
    
    // Inicializa o widget
    init();
});
