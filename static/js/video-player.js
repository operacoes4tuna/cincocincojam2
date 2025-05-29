/**
 * VideoProgressTracker
 * Classe para rastrear o progresso de vídeos do YouTube e outros players.
 * 
 * Recursos:
 * - Monitora o progresso de reprodução do vídeo
 * - Salva a posição atual periodicamente na API
 * - Retoma a reprodução de onde o usuário parou
 * - Rastreia segmentos assistidos do vídeo
 * - Marca aula como concluída automaticamente quando o aluno assiste a uma porcentagem definida
 */
class VideoProgressTracker {
    /**
     * Construtor
     * @param {Object} config Configurações do rastreador
     * @param {String} config.videoElementId ID do elemento iframe do vídeo
     * @param {String} config.progressBarId ID do elemento da barra de progresso (opcional)
     * @param {Number} config.lessonId ID da aula
     * @param {String} config.csrfToken Token CSRF para requisições POST
     * @param {Boolean} config.autoMarkComplete Se deve marcar a aula como concluída automaticamente
     * @param {Number} config.completionThreshold Porcentagem para considerar aula concluída (padrão: 90%)
     * @param {Boolean} config.debug Habilita logs de depuração
     * @param {Boolean} config.isHtml5Video Se é um vídeo HTML5 nativo
     */
    constructor(config) {
        // Configurações
        this.videoId = config.videoElementId;
        this.progressBarId = config.progressBarId;
        this.lessonId = config.lessonId;
        this.csrfToken = config.csrfToken;
        this.autoMarkComplete = config.autoMarkComplete || false;
        this.completionThreshold = config.completionThreshold || 90;
        this.debug = config.debug || false;
        this.isHtml5Video = config.isHtml5Video || false;

        // Estado interno
        this.player = null;
        this.videoElement = document.getElementById(this.videoId);
        this.progressBar = this.progressBarId ? document.getElementById(this.progressBarId) : null;
        this.progressTextElement = document.getElementById(this.progressBarId + '-text') || null;
        this.currentTime = 0;
        this.duration = 0;
        this.isPlaying = false;
        this.isPlayerReady = false;
        this.lastUpdateTime = 0;
        this.updateInterval = 5000; // Atualiza a cada 5 segundos
        this.segments = []; // Segmentos assistidos: [[start1, end1], [start2, end2], ...]
        this.currentSegment = null;
        this.isComplete = false;
        
        // Inicializar
        this.init();
    }

    /**
     * Inicializa o rastreador
     */
    init() {
        this.log('Inicializando rastreador de progresso de vídeo');
        
        // Se for explicitamente marcado como vídeo HTML5
        if (this.isHtml5Video) {
            this.log('Vídeo HTML5 detectado (configuração explícita), inicializando eventos');
            this.initHTML5VideoEvents();
        }
        // Detectar tipo de vídeo baseado no elemento
        else if (this.isYouTubeVideo()) {
            this.log('YouTube detectado, inicializando API');
            this.initYouTubeAPI();
        } else {
            this.log('Elemento de vídeo padrão, inicializando eventos HTML5');
            this.initHTML5VideoEvents();
        }
        
        // Carregar progresso salvo
        this.loadSavedProgress();
    }

    /**
     * Verifica se é um vídeo do YouTube
     */
    isYouTubeVideo() {
        return this.videoElement && this.videoElement.tagName === 'IFRAME' && 
               (this.videoElement.src.includes('youtube.com') || this.videoElement.src.includes('youtu.be'));
    }

    /**
     * Inicializa a API do YouTube
     */
    initYouTubeAPI() {
        // Cria ou carrega a API do YouTube
        if (!window.YT) {
            // Callback global para YouTube API
            window.onYouTubeIframeAPIReady = () => {
                this.setupYouTubePlayer();
            };
            
            // Carrega a API
            const tag = document.createElement('script');
            tag.src = 'https://www.youtube.com/iframe_api';
            const firstScriptTag = document.getElementsByTagName('script')[0];
            firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        } else if (window.YT.Player) {
            // API já carregada
            this.setupYouTubePlayer();
        } else {
            // API carregando, aguardar evento
            const originalCallback = window.onYouTubeIframeAPIReady || function() {};
            window.onYouTubeIframeAPIReady = () => {
                originalCallback();
                this.setupYouTubePlayer();
            };
        }
    }

    /**
     * Configura o player do YouTube
     */
    setupYouTubePlayer() {
        const videoId = this.extractYouTubeVideoId();
        
        if (!videoId) {
            this.log('ID do vídeo do YouTube não encontrado', 'error');
            return;
        }
        
        // Obtém atributos do iframe existente
        const existingIframe = this.videoElement;
        const width = existingIframe.width || existingIframe.clientWidth || '100%';
        const height = existingIframe.height || existingIframe.clientHeight || '100%';
        
        // Cria um ID único para o novo player
        const newPlayerId = 'youtube-player-' + this.lessonId;
        
        // Substitui o iframe existente por um div para o player
        const playerDiv = document.createElement('div');
        playerDiv.id = newPlayerId;
        existingIframe.parentNode.replaceChild(playerDiv, existingIframe);
        
        // Atualiza a referência do elemento de vídeo
        this.videoElement = playerDiv;
        
        // Inicializa o player do YouTube
        this.player = new YT.Player(newPlayerId, {
            videoId: videoId,
            width: width,
            height: height,
            playerVars: {
                'rel': 0,
                'modestbranding': 1,
                'playsinline': 1
            },
            events: {
                'onReady': this.onYouTubePlayerReady.bind(this),
                'onStateChange': this.onYouTubePlayerStateChange.bind(this)
            }
        });
    }

    /**
     * Extrai o ID do vídeo do YouTube da URL
     */
    extractYouTubeVideoId() {
        const iframe = this.videoElement;
        if (!iframe || !iframe.src) return null;
        
        const url = iframe.src;
        const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
        const match = url.match(regExp);
        
        return (match && match[2].length === 11) ? match[2] : null;
    }

    /**
     * Manipulador de evento quando o player do YouTube está pronto
     */
    onYouTubePlayerReady(event) {
        this.log('Player do YouTube pronto');
        this.isPlayerReady = true;
        this.duration = this.player.getDuration();
        
        // Registra intervalo para monitorar o progresso
        setInterval(() => {
            if (this.isPlaying) {
                this.updateCurrentTime();
            }
        }, 1000);
        
        // Carrega o progresso salvo e continua de onde parou
        this.loadSavedProgress().then(() => {
            if (this.currentTime > 0 && this.currentTime < this.duration - 10) {
                // Se temos uma posição salva, que não seja próxima do final
                this.player.seekTo(this.currentTime, true);
            }
        });
    }

    /**
     * Manipulador de eventos para mudanças de estado do player do YouTube
     */
    onYouTubePlayerStateChange(event) {
        // Estados do player do YouTube:
        // -1 (não iniciado), 0 (concluído), 1 (reproduzindo), 2 (pausado), 3 (buffer), 5 (vídeo sugerido)
        switch(event.data) {
            case YT.PlayerState.PLAYING:
                this.log('Vídeo reproduzindo');
                this.isPlaying = true;
                this.startSegment();
                break;
            case YT.PlayerState.PAUSED:
                this.log('Vídeo pausado');
                this.isPlaying = false;
                this.endSegment();
                this.saveProgress(); // Salva o progresso ao pausar
                break;
            case YT.PlayerState.ENDED:
                this.log('Vídeo concluído');
                this.isPlaying = false;
                this.endSegment();
                this.currentTime = this.duration;
                this.saveProgress(); // Salva o progresso ao finalizar
                break;
        }
    }

    /**
     * Inicializa eventos para vídeo HTML5 padrão
     */
    initHTML5VideoEvents() {
        if (!this.videoElement) {
            this.log('Elemento de vídeo não encontrado', 'error');
            return;
        }
        
        if (this.videoElement.tagName !== 'VIDEO') {
            this.log('Elemento não é um vídeo HTML5', 'warn');
            return;
        }
        
        this.log('Inicializando eventos para vídeo HTML5');
        this.isPlayerReady = true;
        
        // Marcamos como pronto imediatamente se já tiver metadados carregados
        if (this.videoElement.readyState >= 1) {
            this.duration = this.videoElement.duration;
            this.log('Vídeo já tem metadados carregados, duração:', this.duration);
        }
        
        this.videoElement.addEventListener('play', () => {
            this.log('Vídeo HTML5: play');
            this.isPlaying = true;
            this.startSegment();
        });
        
        this.videoElement.addEventListener('pause', () => {
            this.log('Vídeo HTML5: pause');
            this.isPlaying = false;
            this.endSegment();
            this.saveProgress();
        });
        
        this.videoElement.addEventListener('ended', () => {
            this.log('Vídeo HTML5: ended');
            this.isPlaying = false;
            this.endSegment();
            this.currentTime = this.duration;
            this.saveProgress();
            
            // Se o vídeo terminou, podemos marcar a aula como concluída
            if (this.autoMarkComplete) {
                const watchedPercentage = this.getWatchedPercentage();
                if (watchedPercentage >= this.completionThreshold) {
                    this.markLessonAsCompleted(watchedPercentage);
                }
            }
        });
        
        this.videoElement.addEventListener('timeupdate', () => {
            this.updateCurrentTime();
            
            // Verificar se atingiu o threshold para completar
            if (this.autoMarkComplete && !this.isComplete) {
                const watchedPercentage = this.getWatchedPercentage();
                if (watchedPercentage >= this.completionThreshold) {
                    this.markLessonAsCompleted(watchedPercentage);
                }
            }
        });
        
        this.videoElement.addEventListener('loadedmetadata', () => {
            this.log('Vídeo HTML5: loadedmetadata');
            this.duration = this.videoElement.duration;
            this.log('Duração do vídeo:', this.duration);
            
            this.loadSavedProgress().then(() => {
                if (this.currentTime > 0 && this.currentTime < this.duration - 10) {
                    this.log('Retomando de:', this.currentTime);
                    this.videoElement.currentTime = this.currentTime;
                }
            });
        });
        
        // Atualizar duração assim que possível
        if (this.videoElement.readyState >= 1) {
            this.duration = this.videoElement.duration;
        }
    }

    /**
     * Atualiza o tempo atual do vídeo
     */
    updateCurrentTime() {
        if (this.isYouTubeVideo() && this.player && this.isPlayerReady) {
            this.currentTime = this.player.getCurrentTime();
        } else if (this.videoElement && this.videoElement.tagName === 'VIDEO') {
            this.currentTime = this.videoElement.currentTime;
        }
        
        // Atualiza a barra de progresso, se existir
        this.updateProgressBar();
        
        // Salva o progresso periodicamente
        const now = Date.now();
        if (now - this.lastUpdateTime > this.updateInterval) {
            this.saveProgress();
            this.lastUpdateTime = now;
        }
    }

    /**
     * Atualiza a barra de progresso visual
     */
    updateProgressBar() {
        if (!this.progressBar) return;
        
        const percentage = this.getProgressPercentage();
        this.progressBar.style.width = percentage + '%';
        this.progressBar.setAttribute('aria-valuenow', percentage);
        
        if (this.progressTextElement) {
            this.progressTextElement.textContent = percentage + '%';
        }
    }

    /**
     * Calcula a porcentagem atual de progresso
     */
    getProgressPercentage() {
        if (!this.duration) return 0;
        return Math.min(100, Math.floor((this.currentTime / this.duration) * 100));
    }

    /**
     * Inicia um novo segmento de visualização
     */
    startSegment() {
        if (this.currentSegment === null) {
            this.currentSegment = [Math.floor(this.currentTime), null];
        }
    }

    /**
     * Finaliza o segmento atual de visualização
     */
    endSegment() {
        if (this.currentSegment !== null) {
            this.currentSegment[1] = Math.floor(this.currentTime);
            
            // Adiciona apenas se for um segmento válido (duração > 1 segundo)
            if (this.currentSegment[1] - this.currentSegment[0] > 1) {
                this.segments.push([...this.currentSegment]);
            }
            
            this.currentSegment = null;
        }
    }

    /**
     * Mescla segmentos sobrepostos para otimizar o armazenamento
     */
    optimizeSegments() {
        if (!this.segments.length) return [];
        
        // Ordena os segmentos pelo tempo de início
        const sorted = [...this.segments].sort((a, b) => a[0] - b[0]);
        const result = [sorted[0]];
        
        for (let i = 1; i < sorted.length; i++) {
            const current = sorted[i];
            const last = result[result.length - 1];
            
            // Se o segmento atual começa antes ou junto com o fim do último segmento
            if (current[0] <= last[1] + 1) {
                // Estende o último segmento se o atual termina depois
                if (current[1] > last[1]) {
                    last[1] = current[1];
                }
            } else {
                // Adiciona novo segmento se não há sobreposição
                result.push(current);
            }
        }
        
        return result;
    }

    /**
     * Calcula o tempo total assistido com base nos segmentos
     */
    getTotalWatchedTime() {
        const optimized = this.optimizeSegments();
        return optimized.reduce((total, segment) => {
            return total + (segment[1] - segment[0]);
        }, 0);
    }

    /**
     * Calcula a porcentagem do vídeo que foi assistida
     */
    getWatchedPercentage() {
        if (!this.duration) return 0;
        
        const totalWatched = this.getTotalWatchedTime();
        return Math.min(100, Math.floor((totalWatched / this.duration) * 100));
    }

    /**
     * Carrega o progresso salvo da API
     */
    async loadSavedProgress() {
        try {
            const response = await fetch(`/courses/api/video-progress/${this.lessonId}/`);
            
            if (!response.ok) {
                throw new Error(`Erro ao carregar progresso: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.data) {
                this.log('Progresso carregado:', data.data);
                this.currentTime = data.data.current_time || 0;
                this.duration = data.data.duration || 0;
                this.isComplete = data.data.is_completed || false;
                
                // Atualiza a barra de progresso
                this.updateProgressBar();
                
                return data.data;
            }
        } catch (error) {
            this.log('Erro ao carregar progresso: ' + error.message, 'error');
        }
        
        return null;
    }

    /**
     * Salva o progresso atual na API
     */
    async saveProgress() {
        // Finaliza o segmento atual se estiver ativo
        if (this.currentSegment !== null) {
            this.endSegment();
            this.startSegment(); // Reinicia o segmento
        }
        
        // Otimiza os segmentos para enviar
        const optimizedSegments = this.optimizeSegments();
        
        const formData = new FormData();
        formData.append('lesson_id', this.lessonId);
        formData.append('current_time', Math.floor(this.currentTime));
        
        if (this.duration) {
            formData.append('duration', Math.floor(this.duration));
        }
        
        if (optimizedSegments.length) {
            formData.append('watched_segments', JSON.stringify(optimizedSegments));
        }
        
        try {
            const response = await fetch('/courses/api/video-progress/update/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Erro ao salvar progresso: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.log('Progresso salvo:', data.data);
                
                // Atualiza o status de conclusão
                if (data.data.is_completed && !this.isComplete) {
                    this.isComplete = true;
                    this.log('Aula marcada como concluída');
                    
                    // Dispara evento para notificar conclusão da aula
                    const event = new CustomEvent('lessonCompleted', {
                        detail: {
                            lessonId: this.lessonId,
                            percentage: data.data.percentage
                        }
                    });
                    document.dispatchEvent(event);
                }
                
                return data.data;
            } else {
                throw new Error(data.message || 'Erro desconhecido ao salvar progresso');
            }
        } catch (error) {
            this.log('Erro ao salvar progresso: ' + error.message, 'error');
        }
        
        return null;
    }

    /**
     * Marca a aula como concluída e dispara um evento
     */
    markLessonAsCompleted(percentage) {
        if (this.isComplete) return;
        
        this.log(`Marcando aula ${this.lessonId} como concluída (${percentage}%)`);
        this.isComplete = true;
        
        // Dispara evento de aula concluída
        const event = new CustomEvent('lessonCompleted', {
            detail: {
                lessonId: this.lessonId,
                percentage: percentage
            }
        });
        document.dispatchEvent(event);
        
        // Tenta enviar para o backend também
        this.saveProgress();
    }

    /**
     * Método auxiliar para logs
     */
    log(message, level = 'info') {
        if (!this.debug) return;
        
        const prefix = `[VideoProgress:${this.lessonId}]`;
        
        switch (level) {
            case 'error':
                console.error(prefix, message);
                break;
            case 'warn':
                console.warn(prefix, message);
                break;
            default:
                console.log(prefix, message);
        }
    }
} 