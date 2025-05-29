from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Course

@login_required
def professor_courses(request):
    """
    API para retornar os cursos do professor logado.
    """
    try:
        # Verificar se o usuário é um professor
        if request.user.user_type != 'PROFESSOR':
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        
        # Buscar cursos do professor (todos, não apenas os publicados)
        courses = Course.objects.filter(
            professor=request.user
        )
        
        # Formatar resposta
        courses_data = [{
            'id': course.id,
            'title': course.title,
            'status': course.status,
            'short_description': course.short_description,
            'student_count': course.get_enrolled_students_count()
        } for course in courses]
        
        return JsonResponse({
            'count': len(courses_data),
            'courses': courses_data
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500) 