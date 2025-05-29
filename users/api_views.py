from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from core.models import User

@login_required
def student_list(request):
    """
    API para listar todos os estudantes (visível apenas para professores e admins).
    """
    try:
        # Verificar permissões
        if request.user.user_type not in ['PROFESSOR', 'ADMIN']:
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        
        # Buscar todos os estudantes ativos
        students = User.objects.filter(
            user_type='STUDENT',
            is_active=True
        )
        
        # Formatar resposta
        students_data = [{
            'id': student.id,
            'name': student.get_full_name() or student.email,
            'email': student.email,
            'avatar': student.profile_image.url if hasattr(student, 'profile_image') and student.profile_image else None
        } for student in students]
        
        return JsonResponse({
            'count': len(students_data),
            'students': students_data
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500) 