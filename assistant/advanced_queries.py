"""
Módulo de consultas avançadas ao banco de dados usando Django ORM
Implementado conforme as diretrizes de otimização e uso eficiente de relacionamentos
"""
from django.db.models import Sum, Count, F, Q, Avg, Max, Min, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

from core.models import User
from courses.models import Course, Lesson, Enrollment
from payments.models import PaymentTransaction

class AdvancedQueries:
    """
    Classe para consultas avançadas ao banco de dados
    Utiliza técnicas eficientes do Django ORM para agregar e relacionar dados
    """
    
    @staticmethod
    def get_top_students_by_revenue(limit=5):
        """
        Obtém os alunos que geraram maior faturamento
        
        Args:
            limit: Número de alunos a retornar
            
        Returns:
            Dicionário com informações dos alunos e valores
        """
        try:
            # Utiliza select_related para otimizar a consulta
            top_students = User.objects.filter(
                user_type='STUDENT',
                enrollment__paymenttransaction__status='PAID'
            ).annotate(
                total_pago=Sum('enrollment__paymenttransaction__amount')
            ).order_by('-total_pago')[:limit]
            
            # Formatar resultados
            result = []
            for student in top_students:
                # Contagem de matrículas em cursos distintos
                course_count = Enrollment.objects.filter(
                    student=student
                ).values('course').distinct().count()
                
                result.append({
                    'id': student.id,
                    'nome': f"{student.first_name} {student.last_name}",
                    'email': student.email,
                    'total_pago': float(student.total_pago or 0),
                    'num_cursos': course_count
                })
                
            return {
                'success': True,
                'students': result,
                'count': len(result)
            }
        except Exception as e:
            # Implementação alternativa em caso de erro no relacionamento
            try:
                # Abordagem alternativa usando PaymentTransaction diretamente
                students_data = {}
                
                # Obter todos os pagamentos processados
                payments = PaymentTransaction.objects.filter(
                    status='PAID'
                ).select_related('enrollment', 'enrollment__student')
                
                # Agregar pagamentos por aluno
                for payment in payments:
                    if payment.enrollment and payment.enrollment.student:
                        student = payment.enrollment.student
                        student_id = student.id
                        
                        if student_id not in students_data:
                            students_data[student_id] = {
                                'id': student_id,
                                'nome': f"{student.first_name} {student.last_name}",
                                'email': student.email,
                                'total_pago': 0,
                                'payments': set(),
                                'courses': set()
                            }
                        
                        # Adicionar o pagamento ao total do aluno
                        students_data[student_id]['total_pago'] += float(payment.amount or 0)
                        students_data[student_id]['payments'].add(payment.id)
                        
                        if payment.enrollment.course:
                            students_data[student_id]['courses'].add(payment.enrollment.course.id)
                
                # Converter para lista ordenada
                result = []
                for student_id, data in students_data.items():
                    result.append({
                        'id': data['id'],
                        'nome': data['nome'],
                        'email': data['email'],
                        'total_pago': data['total_pago'],
                        'num_cursos': len(data['courses'])
                    })
                
                # Ordenar por total pago em ordem decrescente
                result.sort(key=lambda x: x['total_pago'], reverse=True)
                
                # Limitar ao número solicitado
                return {
                    'success': True,
                    'students': result[:limit],
                    'count': len(result[:limit])
                }
            except Exception as e2:
                return {
                    'success': False,
                    'error': f"Erro nas consultas: {str(e)} / Alternativa: {str(e2)}"
                }
    
    @staticmethod
    def get_top_courses_by_enrollment(limit=5, status='ACTIVE'):
        """
        Obtém os cursos com maior número de matrículas
        
        Args:
            limit: Número de cursos a retornar
            status: Status das matrículas a considerar
            
        Returns:
            Dicionário com informações dos cursos e contagens
        """
        try:
            # Consulta otimizada com prefetch_related
            top_courses = Course.objects.filter(
                enrollments__status=status
            ).annotate(
                num_matriculas=Count('enrollments')
            ).order_by('-num_matriculas')[:limit]
            
            # Formatar resultados
            result = []
            for course in top_courses:
                # Calcular faturamento total do curso
                total_revenue = PaymentTransaction.objects.filter(
                    enrollment__course=course,
                    status='PAID'
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                result.append({
                    'id': course.id,
                    'titulo': course.title,
                    'professor': f"{course.professor.first_name} {course.professor.last_name}",
                    'preco': float(course.price),
                    'matriculas': course.num_matriculas,
                    'faturamento': float(total_revenue)
                })
            
            return {
                'success': True,
                'courses': result,
                'count': len(result)
            }
        except Exception as e:
            # Abordagem alternativa em caso de erro
            try:
                # Obter todos os cursos
                courses = Course.objects.all().select_related('professor')
                courses_data = {}
                
                # Para cada curso, contar matrículas manualmente
                for course in courses:
                    enrollment_count = Enrollment.objects.filter(
                        course=course,
                        status=status
                    ).count()
                    
                    # Calcular faturamento
                    revenue = 0
                    course_enrollments = Enrollment.objects.filter(course=course)
                    for enrollment in course_enrollments:
                        paid = PaymentTransaction.objects.filter(
                            enrollment=enrollment,
                            status='PAID'
                        ).aggregate(Sum('amount'))['amount__sum'] or 0
                        revenue += float(paid)
                    
                    courses_data[course.id] = {
                        'id': course.id,
                        'titulo': course.title,
                        'professor': f"{course.professor.first_name} {course.professor.last_name}",
                        'preco': float(course.price),
                        'matriculas': enrollment_count,
                        'faturamento': revenue
                    }
                
                # Converter para lista e ordenar por número de matrículas
                result = list(courses_data.values())
                result.sort(key=lambda x: x['matriculas'], reverse=True)
                
                return {
                    'success': True,
                    'courses': result[:limit],
                    'count': len(result[:limit])
                }
            except Exception as e2:
                return {
                    'success': False,
                    'error': f"Erro nas consultas: {str(e)} / Alternativa: {str(e2)}"
                }
    
    @staticmethod
    def get_courses_with_pending_payments(limit=5):
        """
        Obtém os cursos com maior número de pagamentos pendentes
        
        Args:
            limit: Número de cursos a retornar
            
        Returns:
            Dicionário com informações dos cursos e contagens
        """
        try:
            # Consulta utilizando relacionamentos múltiplos
            courses_with_pending = Course.objects.filter(
                enrollments__paymenttransaction__status='PENDING'
            ).annotate(
                num_pendentes=Count('enrollments__paymenttransaction')
            ).order_by('-num_pendentes')[:limit]
            
            # Formatar resultados
            result = []
            for course in courses_with_pending:
                # Calcular valor total pendente
                pending_amount = PaymentTransaction.objects.filter(
                    enrollment__course=course,
                    status='PENDING'
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                result.append({
                    'id': course.id,
                    'titulo': course.title,
                    'professor': f"{course.professor.first_name} {course.professor.last_name}",
                    'pagamentos_pendentes': course.num_pendentes,
                    'valor_pendente': float(pending_amount)
                })
            
            return {
                'success': True,
                'courses': result,
                'count': len(result)
            }
        except Exception as e:
            # Implementação alternativa
            try:
                # Obter todos os cursos
                courses = Course.objects.all().select_related('professor')
                courses_data = {}
                
                # Obter pagamentos pendentes
                pending_payments = PaymentTransaction.objects.filter(
                    status='PENDING'
                ).select_related('enrollment', 'enrollment__course')
                
                # Contar pagamentos pendentes por curso
                for payment in pending_payments:
                    if payment.enrollment and payment.enrollment.course:
                        course = payment.enrollment.course
                        course_id = course.id
                        
                        if course_id not in courses_data:
                            courses_data[course_id] = {
                                'id': course_id,
                                'titulo': course.title,
                                'professor': f"{course.professor.first_name} {course.professor.last_name}",
                                'pagamentos_pendentes': 0,
                                'valor_pendente': 0
                            }
                        
                        courses_data[course_id]['pagamentos_pendentes'] += 1
                        courses_data[course_id]['valor_pendente'] += float(payment.amount or 0)
                
                # Converter para lista e ordenar
                result = list(courses_data.values())
                result.sort(key=lambda x: x['pagamentos_pendentes'], reverse=True)
                
                return {
                    'success': True,
                    'courses': result[:limit],
                    'count': len(result[:limit])
                }
            except Exception as e2:
                return {
                    'success': False,
                    'error': f"Erro nas consultas: {str(e)} / Alternativa: {str(e2)}"
                }
