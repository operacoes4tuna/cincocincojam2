from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from .models import Lesson, LessonProgress, VideoProgress, Enrollment


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
    watched_segments = request.POST.get('watched_segments')  # formato JSON string: [[start1, end1], [start2, end2], ...]
    
    if not lesson_id or not current_time:
        return JsonResponse({
            'success': False,
            'message': 'Parâmetros incompletos. É necessário fornecer lesson_id e current_time.'
        }, status=400)
    
    try:
        # Converte parâmetros para os tipos corretos
        lesson_id = int(lesson_id)
        current_time = int(float(current_time))
        
        if duration:
            duration = int(float(duration))
        
        if watched_segments:
            import json
            watched_segments = json.loads(watched_segments)
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({
            'success': False,
            'message': 'Formato inválido de parâmetros. Verifique os tipos de dados enviados.'
        }, status=400)
    
    # Busca a aula
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Verifica se o aluno está matriculado no curso da aula
    try:
        enrollment = Enrollment.objects.get(
            student=request.user,
            course=lesson.course,
            status=Enrollment.Status.ACTIVE
        )
    except Enrollment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Você não está matriculado neste curso ou sua matrícula não está ativa.'
        }, status=403)
    
    # Obtém ou cria o progresso da aula
    lesson_progress, created = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )
    
    # Obtém ou cria o progresso do vídeo
    video_progress, created = VideoProgress.objects.get_or_create(
        lesson_progress=lesson_progress,
        defaults={
            'video_duration': duration or 0,
        }
    )
    
    # Se temos a duração e ela mudou, atualiza
    if duration and video_progress.video_duration != duration:
        video_progress.video_duration = duration
    
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


@login_required
def get_video_progress(request, lesson_id):
    """
    API endpoint para obter o progresso atual do vídeo para uma aula específica.
    """
    # Busca a aula
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Verifica se o aluno está matriculado no curso da aula
    try:
        enrollment = Enrollment.objects.get(
            student=request.user,
            course=lesson.course,
            status=Enrollment.Status.ACTIVE
        )
    except Enrollment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Você não está matriculado neste curso ou sua matrícula não está ativa.'
        }, status=403)
    
    # Obtém o progresso da aula
    try:
        lesson_progress = LessonProgress.objects.get(
            enrollment=enrollment,
            lesson=lesson
        )
        
        # Tenta obter o progresso do vídeo
        try:
            video_progress = lesson_progress.video_progress
            
            return JsonResponse({
                'success': True,
                'data': {
                    'lesson_id': lesson_id,
                    'current_time': video_progress.current_position,
                    'duration': video_progress.video_duration,
                    'percentage': video_progress.watched_percentage,
                    'is_completed': lesson_progress.is_completed,
                    'last_updated': video_progress.last_updated.isoformat() if video_progress.last_updated else None,
                }
            })
        except VideoProgress.DoesNotExist:
            # Não há progresso de vídeo ainda
            return JsonResponse({
                'success': True,
                'data': {
                    'lesson_id': lesson_id,
                    'current_time': 0,
                    'duration': 0,
                    'percentage': 0,
                    'is_completed': lesson_progress.is_completed,
                    'last_updated': None,
                }
            })
    except LessonProgress.DoesNotExist:
        # Não há progresso da aula ainda
        return JsonResponse({
            'success': True,
            'data': {
                'lesson_id': lesson_id,
                'current_time': 0,
                'duration': 0,
                'percentage': 0,
                'is_completed': False,
                'last_updated': None,
            }
        })


@login_required
def get_course_video_progress(request, course_id):
    """
    API endpoint para obter o progresso de todas as aulas de um curso.
    Útil para exibir o progresso geral do aluno no curso.
    """
    # Verifica se o aluno está matriculado no curso
    try:
        enrollment = Enrollment.objects.get(
            student=request.user,
            course_id=course_id,
            status=Enrollment.Status.ACTIVE
        )
    except Enrollment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Você não está matriculado neste curso ou sua matrícula não está ativa.'
        }, status=403)
    
    # Obtém todas as aulas do curso
    lessons = Lesson.objects.filter(course_id=course_id, status=Lesson.Status.PUBLISHED)
    
    # Obtém todos os progressos de aula para este aluno neste curso
    lesson_progresses = LessonProgress.objects.filter(
        enrollment=enrollment,
        lesson__in=lessons
    ).select_related('lesson', 'video_progress')
    
    # Mapeia os progressos por ID da aula para fácil acesso
    progress_map = {lp.lesson_id: lp for lp in lesson_progresses}
    
    # Prepara os dados
    lessons_data = []
    total_percentage = 0
    lessons_with_progress = 0
    
    for lesson in lessons:
        lesson_data = {
            'id': lesson.id,
            'title': lesson.title,
            'order': lesson.order,
            'has_video': bool(lesson.video_url),
        }
        
        if lesson.id in progress_map:
            lp = progress_map[lesson.id]
            lesson_data['is_completed'] = lp.is_completed
            lesson_data['last_accessed'] = lp.last_accessed_at.isoformat() if lp.last_accessed_at else None
            
            try:
                vp = lp.video_progress
                lesson_data['video_progress'] = {
                    'current_time': vp.current_position,
                    'duration': vp.video_duration,
                    'percentage': vp.watched_percentage,
                    'last_updated': vp.last_updated.isoformat() if vp.last_updated else None,
                }
                
                # Contabiliza para média total
                if vp.video_duration > 0:
                    total_percentage += vp.watched_percentage
                    lessons_with_progress += 1
            except VideoProgress.DoesNotExist:
                lesson_data['video_progress'] = None
        else:
            lesson_data['is_completed'] = False
            lesson_data['last_accessed'] = None
            lesson_data['video_progress'] = None
        
        lessons_data.append(lesson_data)
    
    # Calcula média total
    avg_progress = 0
    if lessons_with_progress > 0:
        avg_progress = total_percentage / lessons_with_progress
    
    # Estatísticas gerais
    completed_lessons = sum(1 for lp in lesson_progresses if lp.is_completed)
    total_lessons = lessons.count()
    
    return JsonResponse({
        'success': True,
        'data': {
            'course_id': course_id,
            'lessons': lessons_data,
            'statistics': {
                'total_lessons': total_lessons,
                'completed_lessons': completed_lessons,
                'completion_percentage': int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0,
                'avg_video_progress': int(avg_progress),
            }
        }
    }) 