"""
Módulo para gerenciar consultas ao banco de dados para o assistente virtual
"""
import logging
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from courses.models import Course, Lesson, Enrollment, LessonProgress
from core.models import User
from payments.models import PaymentTransaction

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerencia consultas ao banco de dados para o assistente"""
    
    @staticmethod
    def get_course_info(course_id=None, course_slug=None, course_title=None):
        """
        Obtém informações sobre um curso específico
        
        Args:
            course_id: ID do curso
            course_slug: Slug do curso
            course_title: Título do curso (busca parcial)
            
        Returns:
            Dicionário com informações do curso ou None se não encontrado
        """
        try:
            query = Q()
            if course_id:
                query |= Q(id=course_id)
            if course_slug:
                query |= Q(slug=course_slug)
            if course_title:
                query |= Q(title__icontains=course_title)
                
            if not query:
                return None
                
            course = Course.objects.filter(query).first()
            
            if not course:
                return None
                
            return {
                'id': course.id,
                'title': course.title,
                'professor': course.professor.username,
                'description': course.description,
                'price': float(course.price),
                'status': course.status,
                'total_lessons': course.get_total_lessons(),
                'students_count': course.get_enrolled_students_count()
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações do curso: {str(e)}")
            return None
    
    @staticmethod
    def search_courses(query_text, limit=5):
        """
        Busca cursos que correspondam à consulta
        
        Args:
            query_text: Texto para buscar nos títulos e descrições
            limit: Número máximo de resultados
            
        Returns:
            Lista de cursos encontrados
        """
        try:
            courses = Course.objects.filter(
                Q(title__icontains=query_text) | 
                Q(description__icontains=query_text) |
                Q(short_description__icontains=query_text)
            ).filter(status='PUBLISHED')[:limit]
            
            return [
                {
                    'id': course.id,
                    'title': course.title,
                    'short_description': course.short_description,
                    'professor': course.professor.username,
                    'price': float(course.price),
                    'total_lessons': course.get_total_lessons()
                }
                for course in courses
            ]
        except Exception as e:
            logger.error(f"Erro ao buscar cursos: {str(e)}")
            return []
    
    @staticmethod
    def get_lessons_for_course(course_id=None, course_slug=None):
        """
        Obtém a lista de aulas para um curso específico
        
        Args:
            course_id: ID do curso
            course_slug: Slug do curso
            
        Returns:
            Lista de aulas do curso
        """
        try:
            query = Q()
            if course_id:
                query |= Q(id=course_id)
            if course_slug:
                query |= Q(slug=course_slug)
                
            if not query:
                return []
                
            course = Course.objects.filter(query).first()
            
            if not course:
                return []
                
            lessons = Lesson.objects.filter(course=course).order_by('order')
            
            return [
                {
                    'id': lesson.id,
                    'title': lesson.title,
                    'description': lesson.description,
                    'order': lesson.order,
                    'duration_minutes': lesson.duration_minutes,
                    'is_free': lesson.is_free
                }
                for lesson in lessons
            ]
        except Exception as e:
            logger.error(f"Erro ao obter aulas do curso: {str(e)}")
            return []
    
    @staticmethod
    def get_enrollment_info(student_email, course_id=None, course_slug=None):
        """
        Obtém informações sobre a matrícula de um aluno em um curso
        
        Args:
            student_email: Email do aluno
            course_id: ID do curso
            course_slug: Slug do curso
            
        Returns:
            Dicionário com informações da matrícula ou None se não encontrada
        """
        try:
            student = User.objects.filter(email=student_email).first()
            
            if not student:
                return None
                
            query = Q()
            if course_id:
                query |= Q(course__id=course_id)
            if course_slug:
                query |= Q(course__slug=course_slug)
                
            if not query:
                return None
                
            enrollment = Enrollment.objects.filter(query, student=student).first()
            
            if not enrollment:
                return None
                
            return {
                'id': enrollment.id,
                'course': enrollment.course.title,
                'status': enrollment.status,
                'progress': enrollment.progress,
                'enrolled_at': enrollment.enrolled_at.isoformat(),
                'completed_at': enrollment.completed_at.isoformat() if enrollment.completed_at else None
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações da matrícula: {str(e)}")
            return None
    
    @staticmethod
    def get_user_enrollments(student_email):
        """
        Obtém todas as matrículas de um aluno
        
        Args:
            student_email: Email do aluno
            
        Returns:
            Lista de matrículas do aluno
        """
        try:
            student = User.objects.filter(email=student_email).first()
            
            if not student:
                return []
                
            enrollments = Enrollment.objects.filter(student=student)
            
            return [
                {
                    'id': enrollment.id,
                    'course': enrollment.course.title,
                    'status': enrollment.status,
                    'progress': enrollment.progress,
                    'enrolled_at': enrollment.enrolled_at.isoformat()
                }
                for enrollment in enrollments
            ]
        except Exception as e:
            logger.error(f"Erro ao obter matrículas do aluno: {str(e)}")
            return []
    
    @staticmethod
    def get_platform_stats():
        """
        Obtém estatísticas gerais da plataforma
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            total_courses = Course.objects.filter(status='PUBLISHED').count()
            total_lessons = Lesson.objects.filter(course__status='PUBLISHED').count()
            total_students = User.objects.filter(user_type='STUDENT').count()
            total_professors = User.objects.filter(user_type='PROFESSOR').count()
            total_enrollments = Enrollment.objects.filter(status='ACTIVE').count()
            
            return {
                'total_courses': total_courses,
                'total_lessons': total_lessons,
                'total_students': total_students,
                'total_professors': total_professors,
                'total_enrollments': total_enrollments
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas da plataforma: {str(e)}")
            return {}
    
    @staticmethod
    def get_payment_info(enrollment_id=None, transaction_id=None):
        """
        Obtém informações sobre uma transação de pagamento específica
        
        Args:
            enrollment_id: ID da matrícula relacionada ao pagamento
            transaction_id: ID da transação de pagamento
            
        Returns:
            Dicionário com informações do pagamento ou None se não encontrado
        """
        try:
            query = Q()
            if enrollment_id:
                query |= Q(enrollment_id=enrollment_id)
            if transaction_id:
                query |= Q(id=transaction_id)
                
            if not query:
                return None
                
            payment = PaymentTransaction.objects.filter(query).first()
            
            if not payment:
                return None
                
            return {
                'id': payment.id,
                'enrollment_id': payment.enrollment_id,
                'student_email': payment.enrollment.student.email,
                'course_title': payment.enrollment.course.title,
                'amount': float(payment.amount),
                'status': payment.status,
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                'payment_method': payment.payment_method,
                'transaction_id': payment.transaction_id,
                'created_at': payment.created_at.isoformat(),
                'updated_at': payment.updated_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações de pagamento: {str(e)}")
            return None
    
    @staticmethod
    def get_user_payments(student_email):
        """
        Obtém todas as transações de pagamento de um aluno
        
        Args:
            student_email: Email do aluno
            
        Returns:
            Lista de transações do aluno
        """
        try:
            student = User.objects.filter(email=student_email).first()
            
            if not student:
                return []
                
            payments = PaymentTransaction.objects.filter(enrollment__student=student).order_by('-created_at')
            
            return [
                {
                    'id': payment.id,
                    'course_title': payment.enrollment.course.title,
                    'amount': float(payment.amount),
                    'status': payment.status,
                    'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                    'payment_method': payment.payment_method,
                    'created_at': payment.created_at.isoformat()
                }
                for payment in payments
            ]
        except Exception as e:
            logger.error(f"Erro ao obter pagamentos do aluno: {str(e)}")
            return []
    
    @staticmethod
    def get_pending_payments():
        """
        Obtém a lista de pagamentos pendentes na plataforma
        
        Returns:
            Lista de pagamentos pendentes com informações detalhadas
        """
        try:
            # Obter todas as transações pendentes
            pending_payments = PaymentTransaction.objects.filter(status='PENDING').order_by('-created_at')
            
            # Formatar os dados de cada pagamento
            payments_list = [
                {
                    'id': payment.id,
                    'course_name': payment.enrollment.course.title,
                    'student_email': payment.enrollment.student.email,
                    'student_name': f"{payment.enrollment.student.first_name} {payment.enrollment.student.last_name}",
                    'amount': float(payment.amount),
                    'status': payment.status,
                    'created_at': payment.created_at.isoformat(),
                    'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                    'enrollment_id': payment.enrollment.id
                }
                for payment in pending_payments
            ]
            
            # Adicionar estatísticas resumidas
            total_pending = sum(payment['amount'] for payment in payments_list)
            
            return {
                'payments': payments_list,
                'total_count': len(payments_list),
                'total_amount': float(total_pending)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter pagamentos pendentes: {str(e)}")
            return {
                'payments': [],
                'total_count': 0,
                'total_amount': 0.0
            }
    
    @staticmethod
    def get_revenue_stats(period=None):
        """
        Obtém estatísticas de faturamento da plataforma
        
        Args:
            period: Período para filtrar estatísticas (month, year, all)
            
        Returns:
            Dicionário com estatísticas de faturamento
        """
        try:
            # Inicializa a query base
            query = Q(status='PAID')
            
            # Aplica filtro de período se especificado
            now = timezone.now()
            if period == 'month':
                # Último mês
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                query &= Q(payment_date__gte=month_start)
            elif period == 'year':
                # Último ano
                year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                query &= Q(payment_date__gte=year_start)
            
            # Obtém as transações pagas
            paid_transactions = PaymentTransaction.objects.filter(query)
            
            # Calcula estatísticas
            total_revenue = paid_transactions.aggregate(total=Sum('amount'))['total'] or 0
            total_transactions = paid_transactions.count()
            average_ticket = total_revenue / total_transactions if total_transactions > 0 else 0
            
            # Estatísticas por status
            status_stats = {}
            for status, label in PaymentTransaction.Status.choices:
                count = PaymentTransaction.objects.filter(status=status).count()
                # Converte o proxy de tradução para string para evitar erro de serialização
                status_stats[str(label)] = count
            
            return {
                'total_revenue': float(total_revenue),
                'total_transactions': total_transactions,
                'average_ticket': float(average_ticket),
                'transactions_by_status': status_stats,
                'period': period or 'all_time'
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de faturamento: {str(e)}")
            return {}
