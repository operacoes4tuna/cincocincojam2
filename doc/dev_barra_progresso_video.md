# Implementação da Barra de Progresso de Vídeo para Cursos - 55Jam

Este documento descreve a implementação da barra de progresso de vídeo para a plataforma de cursos da 55Jam, incluindo o rastreamento de progresso dos alunos, armazenamento de posição de vídeo e visualização do progresso para alunos e professores.

## 1. Visão Geral

A funcionalidade de barra de progresso de vídeo foi desenvolvida para enriquecer a experiência do aluno durante o consumo de conteúdo em vídeo, permitindo:

- Rastrear o progresso de visualização de vídeos do YouTube
- Salvar automaticamente a posição atual de reprodução
- Restaurar a posição de reprodução quando o aluno retorna à aula
- Marcar aulas como concluídas automaticamente quando o aluno assiste a uma porcentagem específica
- Visualizar quais partes do vídeo já foram assistidas

> ⚠️ **ATENÇÃO**: Esta funcionalidade está parcialmente implementada. A interface visual e o banco de dados estão prontos, mas a integração com a API do YouTube ainda precisa ser finalizada, pois não está detectando corretamente o avanço do vídeo.

## 2. Arquivos Modificados e Criados

### 2.1. Modelos de Dados
- `courses/models.py` - Adição do modelo `VideoProgress`

### 2.2. API e Endpoints
- `courses/api.py` - Implementação de endpoints para gerenciar o progresso de vídeo
- `courses/urls.py` - Adição de rotas para os endpoints de API

### 2.3. Frontend
- `static/js/video-player.js` - Criação do tracker JavaScript para monitoramento de vídeo
- `static/css/custom.css` - Estilos para a barra de progresso e elementos visuais

### 2.4. Templates
- `templates/courses/student/course_learn.html` - Modificação para incluir a barra de progresso

## 3. Detalhes das Implementações

### 3.1. Modelo VideoProgress

O modelo `VideoProgress` foi criado para armazenar detalhes sobre o progresso de visualização de cada vídeo:

```python
class VideoProgress(models.Model):
    """
    Modelo para rastrear o progresso detalhado de visualização de vídeos.
    """
    # Relacionamento
    lesson_progress = models.OneToOneField(
        LessonProgress,
        on_delete=models.CASCADE,
        related_name='video_progress',
        verbose_name=_('progresso da aula')
    )
    
    # Campos de rastreamento
    current_position = models.PositiveIntegerField(
        _('posição atual (segundos)'),
        default=0,
        help_text=_('Posição atual em segundos de onde o aluno parou de assistir')
    )
    video_duration = models.PositiveIntegerField(
        _('duração total (segundos)'),
        default=0,
        help_text=_('Duração total do vídeo em segundos')
    )
    watched_percentage = models.PositiveIntegerField(
        _('porcentagem assistida'),
        default=0,
        help_text=_('Porcentagem do vídeo que foi assistida (0-100)')
    )
    watched_segments = models.JSONField(
        _('segmentos assistidos'),
        null=True,
        blank=True,
        help_text=_('Registra os segmentos do vídeo já assistidos pelo aluno')
    )
    last_updated = models.DateTimeField(_('última atualização'), auto_now=True)
```

O modelo inclui um método `update_progress` para atualizar o progresso e, se necessário, marcar a aula como concluída automaticamente quando a porcentagem de visualização atinge o limiar de 90%.

### 3.2. API de Progresso de Vídeo

Foram implementados três endpoints de API:

1. **update_video_progress** - Atualiza o progresso de um vídeo
2. **get_video_progress** - Obtém o progresso atual de um vídeo específico
3. **get_course_video_progress** - Obtém o progresso de todas as aulas de um curso

Exemplo da implementação do endpoint de atualização:

```python
@login_required
@require_POST
def update_video_progress(request):
    """
    API endpoint para atualizar o progresso do vídeo.
    Recebe os dados do player de vídeo e atualiza o progresso do aluno.
    """
    # Verifica se a requisição tem os dados necessários
    lesson_id = request.POST.get('lesson_id')
    current_time = request.POST.get('current_time')  # tempo atual em segundos
    duration = request.POST.get('duration')  # duração total em segundos
    watched_segments = request.POST.get('watched_segments')  # formato JSON
    
    # ... validação e processamento ...
    
    # Atualiza o progresso
    video_progress.update_progress(current_time, watched_segments)
    
    # Resposta com o progresso atualizado
    return JsonResponse({
        'success': True,
        'message': 'Progresso atualizado com sucesso.',
        'data': {
            'lesson_id': lesson_id,
            'current_time': current_time,
            'duration': video_progress.video_duration,
            'percentage': video_progress.watched_percentage,
            'is_completed': lesson_progress.is_completed,
        }
    })
```

### 3.3. Tracker JavaScript (VideoProgressTracker)

Foi implementada uma classe JavaScript para monitorar o progresso dos vídeos:

```javascript
class VideoProgressTracker {
    constructor(config) {
        // Configurações
        this.videoId = config.videoElementId;
        this.progressBarId = config.progressBarId;
        this.lessonId = config.lessonId;
        this.csrfToken = config.csrfToken;
        this.autoMarkComplete = config.autoMarkComplete || false;
        this.completionThreshold = config.completionThreshold || 90;
        this.debug = config.debug || false;

        // Estado interno
        this.player = null;
        this.videoElement = document.getElementById(this.videoId);
        this.progressBar = this.progressBarId ? document.getElementById(this.progressBarId) : null;
        // ...outras propriedades...
        
        // Inicializar
        this.init();
    }
    
    // ... métodos para manipulação de eventos, cálculo de progresso, 
    // comunicação com a API, etc ...
}
```

A classe inclui funcionalidades para:
- Detectar automaticamente vídeos do YouTube e outros formatos
- Inicializar a API do YouTube quando necessário
- Rastrear segmentos assistidos do vídeo
- Salvar e carregar o progresso através da API
- Atualizar a interface visual (barra de progresso)

### 3.4. Interface Visual

Foi implementada uma interface visual para exibir o progresso:

```html
<div class="video-container">
    <!-- Indicador de conclusão -->
    {% if current_lesson.id in completed_lessons %}
        <div class="lesson-completed-badge">
            <i class="fas fa-check-circle"></i> Concluída
        </div>
    {% endif %}
    
    <!-- Player de vídeo -->
    <div class="ratio ratio-16x9 mb-2">
        <!-- iframe do YouTube -->
    </div>
    
    <!-- Barra de progresso -->
    <div class="progress-container">
        <div id="video-progress-bar-{{ current_lesson.id }}" 
             class="video-progress-bar" 
             role="progressbar" 
             aria-valuenow="0" 
             aria-valuemin="0" 
             aria-valuemax="100"></div>
    </div>
    
    <!-- Indicador de porcentagem -->
    <div class="d-flex justify-content-between">
        <span class="small">Progresso:</span>
        <span class="small" id="video-progress-bar-{{ current_lesson.id }}-text">0%</span>
    </div>
</div>
```

Os estilos CSS incluem:
- Barra de progresso com animação suave
- Indicador de conclusão da aula
- Visualização de segmentos assistidos
- Adaptação para tema claro e escuro

## 4. Recursos Implementados

### 4.1. Rastreamento Automático
- Detecção automática do tipo de vídeo (YouTube ou HTML5)
- Inicialização apropriada baseada no tipo de vídeo
- Cálculo de porcentagem de visualização

### 4.2. Armazenamento de Estado
- Armazenamento da posição atual do vídeo
- Rastreamento de segmentos assistidos
- Cálculo de porcentagem total assistida

### 4.3. Conclusão Automática
- Marcação automática de aula como concluída quando o aluno assiste a uma porcentagem configurável do vídeo
- Atualização da interface quando a aula é concluída

### 4.4. Persistência de Dados
- Salvamento periódico do progresso durante a reprodução
- Salvamento explícito ao pausar ou encerrar o vídeo
- Restauração da posição quando o aluno retorna à aula

## 5. Limitações Atuais e Itens Pendentes

> ⚠️ **IMPORTANTE**: A funcionalidade possui limitações que precisam ser resolvidas em futuras iterações.

### 5.1. Integração com YouTube
- **Problema**: A detecção do avanço do vídeo do YouTube não está funcionando corretamente.
- **Causa**: Possivelmente relacionado a restrições da API do YouTube ou erros na inicialização do player.
- **Solução pendente**: Revisar a inicialização da API do YouTube e garantir que os eventos estejam sendo capturados.

### 5.2. Testes de Integração
- Necessidade de testes mais abrangentes com diferentes tipos de vídeos
- Verificação de funcionamento em diversos navegadores

### 5.3. Otimizações de Performance
- Otimizar o armazenamento e processamento de segmentos assistidos
- Reduzir a frequência de chamadas à API para vídeos longos

## 6. Próximos Passos

Para completar a implementação, as seguintes ações são necessárias:

1. **Corrigir a integração com a API do YouTube**:
   - Verificar se o parâmetro `enablejsapi=1` está sendo corretamente aplicado
   - Garantir que os eventos do player estejam sendo registrados
   - Testar com diferentes tipos de incorporação do YouTube

2. **Implementar testes de unidade e integração**:
   - Testar o modelo `VideoProgress`
   - Testar os endpoints de API
   - Testar a classe JavaScript `VideoProgressTracker`

3. **Melhorar a visualização para professores**:
   - Adicionar relatórios de engajamento com vídeos
   - Visualização de heatmaps mostrando quais partes dos vídeos são mais assistidas

4. **Otimizar o sistema de segmentos**:
   - Implementar algoritmos mais eficientes para mesclar segmentos sobrepostos
   - Limitar o tamanho máximo do JSON de segmentos para vídeos muito longos

## 7. Guia para Desenvolvedores

Para trabalhar com esta funcionalidade, sigam estas diretrizes:

1. **Não modificar a estrutura do modelo** - A estrutura do modelo `VideoProgress` foi projetada para ser flexível e eficiente.

2. **Testar com vídeos reais** - Ao fazer modificações, sempre teste com vídeos reais do YouTube.

3. **Verificar o Console** - Ative o modo debug (`debug: true`) para ver logs no console do navegador que ajudam no diagnóstico.

4. **Respeitar a API do YouTube** - Esteja ciente das limitações e políticas da API do YouTube para incorporação de vídeos.

5. **Manter compatibilidade** - Qualquer modificação deve manter compatibilidade com os registros de progresso existentes. 