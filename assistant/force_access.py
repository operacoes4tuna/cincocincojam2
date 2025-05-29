"""
Módulo para forçar acesso a todos os dados do banco sem restrições
"""
from django.db.models import Q, Sum, Count
from core.models import User
from courses.models import Course, Enrollment
from payments.models import PaymentTransaction

def get_all_clients():
    """
    Retorna todos os clientes/alunos da plataforma
    """
    try:
        # Buscar todos os usuários com matrículas
        students = User.objects.filter(
            enrollments__isnull=False
        ).distinct().order_by('username')
        
        result = "# 👥 Lista de Clientes/Alunos\n"
        result += f"**Total de clientes**: {students.count()}\n\n"
        
        # Formatar informações dos clientes
        for i, student in enumerate(students, 1):
            # Contar matrículas
            enrollments = Enrollment.objects.filter(student=student)
            # Calcular valor gasto
            payments = PaymentTransaction.objects.filter(
                user=student,
                status='PAID'
            )
            total_spent = payments.aggregate(Sum('amount'))['amount__sum'] or 0
            
            result += f"**{i}. {student.get_full_name() or student.username}** | "
            result += f"Email: {student.email} | "
            result += f"Cursos: {enrollments.count()} | "
            result += f"Valor gasto: R$ {float(total_spent):.2f}\n"
        
        return result
    except Exception as e:
        return f"Erro ao acessar clientes: {str(e)}"

def get_courses_with_students():
    """
    Retorna todos os cursos com seus alunos matriculados
    """
    try:
        # Buscar todos os cursos com matrículas
        courses = Course.objects.annotate(
            student_count=Count('enrollment')
        ).order_by('-student_count')
        
        result = "# 📚 Cursos e Alunos Matriculados\n\n"
        
        for i, course in enumerate(courses, 1):
            # Buscar matrículas deste curso
            enrollments = Enrollment.objects.filter(course=course).select_related('student')
            
            # Calcular receita do curso
            course_revenue = PaymentTransaction.objects.filter(
                enrollment__course=course,
                status='PAID'
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            result += f"## {i}. {course.title}\n"
            result += f"**Professor**: {course.professor.get_full_name() or course.professor.username} | "
            result += f"**Preço**: R$ {float(course.price):.2f} | "
            result += f"**Alunos**: {course.student_count} | "
            result += f"**Receita total**: R$ {float(course_revenue):.2f}\n\n"
            
            # Listar alunos deste curso
            result += "### Alunos matriculados:\n"
            for j, enrollment in enumerate(enrollments[:20], 1):
                student = enrollment.student
                result += f"{j}. {student.get_full_name() or student.username} ({student.email})\n"
            
            if enrollments.count() > 20:
                result += f"... _e mais {enrollments.count() - 20} alunos_\n"
                
            result += "\n"
            
        return result
    except Exception as e:
        return f"Erro ao acessar cursos e alunos: {str(e)}"

def process_any_query(query):
    """
    Processa qualquer consulta relacionada ao banco de dados
    """
    query = query.lower()
    
    # Detectar consultas sobre clientes/alunos
    if any(word in query for word in ['cliente', 'clientes', 'aluno', 'alunos', 'estudante', 'estudantes']):
        return get_all_clients()
        
    # Detectar consultas sobre cursos e seus alunos
    if any(word in query for word in ['curso', 'cursos', 'matricula', 'matriculas', 'matrículas']):
        return get_courses_with_students()
    
    # Para outras consultas, fornece dados gerais
    from .direct_query import format_financial_data
    return format_financial_data()
