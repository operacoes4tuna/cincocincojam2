from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, TemplateView, View, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F, Prefetch
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid
from django.http import JsonResponse

from courses.views import ProfessorRequiredMixin, AdminRequiredMixin, StudentRequiredMixin
from courses.models import Course, Enrollment
from .models import PaymentTransaction, SingleSale
from .openpix_service import OpenPixService

User = get_user_model()

# Views para professores
class ProfessorFinancialDashboardView(LoginRequiredMixin, ProfessorRequiredMixin, TemplateView):
    """
    Dashboard financeiro do professor, mostrando uma visão geral das matrículas e pagamentos.
    Inclui também estatísticas sobre os alunos ativos.
    """
    template_name = 'payments/professor/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        professor = self.request.user
        
        # Cursos do professor
        courses = Course.objects.filter(professor=professor)
        context['courses'] = courses
        context['courses_count'] = courses.count()
        
        # Matrículas nos cursos do professor
        enrollments = Enrollment.objects.filter(course__professor=professor)
        context['enrollments_count'] = enrollments.count()
        
        # Estatísticas financeiras
        transactions = PaymentTransaction.objects.filter(enrollment__course__professor=professor)
        
        # Total recebido (status PAID)
        total_paid = transactions.filter(status=PaymentTransaction.Status.PAID).aggregate(
            total=Sum('amount')
        )['total'] or 0
        context['total_received'] = total_paid
        
        # Total pendente (status PENDING)
        total_pending = transactions.filter(status=PaymentTransaction.Status.PENDING).aggregate(
            total=Sum('amount')
        )['total'] or 0
        context['total_pending'] = total_pending
        
        # Estatísticas de alunos
        # Usar anotações para contar apenas os alunos com matrículas ativas
        from django.db.models import Count, Q
        
        # Alunos com matrículas ativas nos cursos do professor
        active_students = User.objects.filter(
            user_type=User.Types.STUDENT,
            enrollments__course__professor=professor,
            enrollments__status=Enrollment.Status.ACTIVE
        ).distinct()
        context['active_students_count'] = active_students.count()
        
        # Alunos recentes (matriculados nos últimos 30 dias)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_students = User.objects.filter(
            user_type=User.Types.STUDENT,
            enrollments__course__professor=professor,
            enrollments__enrolled_at__gte=thirty_days_ago
        ).distinct()
        context['recent_students_count'] = recent_students.count()
        
        # Total por curso
        course_stats = []
        for course in courses:
            course_enrollments = enrollments.filter(course=course).count()
            course_paid = transactions.filter(
                enrollment__course=course, 
                status=PaymentTransaction.Status.PAID
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            course_stats.append({
                'course': course,
                'enrollments': course_enrollments,
                'total_paid': course_paid
            })
        
        context['course_stats'] = course_stats
        
        # Transações recentes
        context['recent_transactions'] = transactions.order_by('-created_at')[:5]
        
        # Notas fiscais (nova seção)
        try:
            from invoices.models import Invoice
            # Contagem de notas fiscais por status
            invoices = Invoice.objects.filter(transaction__enrollment__course__professor=professor)
            context['invoices_count'] = invoices.count()
            
            # Notas por status
            context['invoices_approved'] = invoices.filter(status='approved').count()
            context['invoices_pending'] = invoices.filter(status='pending').count()
            context['invoices_processing'] = invoices.filter(status='processing').count()
            context['invoices_error'] = invoices.filter(status='error').count()
            
            # Notas fiscais recentes (últimas 5)
            context['recent_invoices'] = invoices.order_by('-created_at')[:5]
            
            # Verificar se o professor possui configuração fiscal
            from invoices.models import CompanyConfig
            try:
                try:
                    company_config = CompanyConfig.objects.get(user=professor)
                    context['has_company_config'] = True
                    context['company_config_complete'] = company_config.is_complete()
                    context['company_config_enabled'] = company_config.enabled
                except CompanyConfig.DoesNotExist:
                    context['has_company_config'] = False
                    context['company_config_complete'] = False
                    context['company_config_enabled'] = False
                except Exception as e:
                    # Tratar erro com coluna faltando ou outro problema de banco de dados
                    print(f"Erro ao acessar CompanyConfig: {e}")
                    context['has_company_config'] = False
                    context['company_config_complete'] = False
                    context['company_config_enabled'] = False
            except CompanyConfig.DoesNotExist:
                context['has_company_config'] = False
                context['company_config_complete'] = False
                context['company_config_enabled'] = False
        except ImportError:
            # Caso o aplicativo invoices não esteja disponível
            pass
        
        return context


class ProfessorTransactionListView(LoginRequiredMixin, ProfessorRequiredMixin, ListView):
    """
    Lista todas as transações relacionadas aos cursos do professor.
    Permite filtrar por curso e status.
    """
    model = PaymentTransaction
    template_name = 'payments/professor/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PaymentTransaction.objects.filter(
            enrollment__course__professor=self.request.user
        ).select_related('enrollment', 'enrollment__student', 'enrollment__course')
        
        # Adicionar prefetch_related para carregar as notas fiscais associadas
        try:
            from invoices.models import Invoice
            queryset = queryset.prefetch_related('invoices')
        except ImportError:
            pass  # O app de invoices pode não estar disponível
        
        # Filtro por curso
        course_id = self.request.GET.get('course')
        if course_id:
            queryset = queryset.filter(enrollment__course_id=course_id)
            
        # Filtro por status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Cursos do professor para o filtro
        context['courses'] = Course.objects.filter(professor=self.request.user)
        
        # Status possíveis para o filtro
        context['status_choices'] = PaymentTransaction.Status.choices
        
        # Filtros ativos
        context['selected_course'] = self.request.GET.get('course', '')
        context['selected_status'] = self.request.GET.get('status', '')
        
        # Totalizadores
        total_amount = self.get_queryset().aggregate(total=Sum('amount'))['total'] or 0
        context['total_amount'] = total_amount
        
        return context


class ProfessorCourseEnrollmentListView(LoginRequiredMixin, ProfessorRequiredMixin, ListView):
    """
    Lista os alunos matriculados em um curso específico do professor,
    junto com o status dos pagamentos.
    """
    model = Enrollment
    template_name = 'payments/professor/course_enrollment_list.html'
    context_object_name = 'enrollments'
    paginate_by = 20
    
    def get_queryset(self):
        # Verificar se o curso pertence ao professor
        self.course = get_object_or_404(
            Course,
            pk=self.kwargs.get('course_id'),
            professor=self.request.user
        )
        
        queryset = Enrollment.objects.filter(course=self.course)\
            .select_related('student', 'course')\
            .prefetch_related('payments')
            
        return queryset.order_by('-enrolled_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        
        # Adicionar status de pagamento a cada matrícula
        enrollments_with_status = []
        for enrollment in context['enrollments']:
            # Verificar se existe pagamento confirmado
            has_paid = enrollment.payments.filter(status=PaymentTransaction.Status.PAID).exists()
            
            enrollments_with_status.append({
                'enrollment': enrollment,
                'paid': has_paid,
                'transactions': enrollment.payments.order_by('-created_at')
            })
            
        context['enrollments_with_status'] = enrollments_with_status
        return context


class ProfessorStudentListView(LoginRequiredMixin, ProfessorRequiredMixin, ListView):
    """
    Lista todos os alunos matriculados nos cursos do professor.
    """
    model = User
    template_name = 'payments/professor/student_list.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        professor = self.request.user
        
        # Consulta básica: encontrar todos os alunos dos cursos do professor
        # usando prefetch_related para carregar as matrículas eficientemente
        base_query = User.objects.filter(
            user_type='STUDENT',
            enrollments__course__professor=professor
        ).distinct()
        
        # Aplicar filtros opcionais
        course_id = self.request.GET.get('course')
        enrollment_status = self.request.GET.get('status')
        
        # Construir filtro para prefetch_related
        enrollment_filter = models.Q(course__professor=professor)
        
        if course_id:
            try:
                course_id_int = int(course_id)
                enrollment_filter &= models.Q(course_id=course_id_int)
                base_query = base_query.filter(enrollments__course_id=course_id_int)
            except (ValueError, TypeError):
                pass
                
        if enrollment_status:
            enrollment_filter &= models.Q(status=enrollment_status)
            base_query = base_query.filter(enrollments__status=enrollment_status)
        
        # Aplicar prefetch_related para carregar matrículas relacionadas eficientemente
        prefetch_enrollments = models.Prefetch(
            'enrollments',
            queryset=Enrollment.objects.filter(enrollment_filter).select_related('course')
        )
        
        # Aplicar ordenação e prefetch
        students = base_query.prefetch_related(prefetch_enrollments)
        students = students.order_by('first_name', 'last_name')
        
        return students
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        professor = self.request.user
        
        # Cursos do professor para filtro
        context['courses'] = Course.objects.filter(professor=professor)
        
        # Dados para o filtro
        context['enrollment_status_choices'] = Enrollment.Status.choices
        context['selected_course'] = self.request.GET.get('course')
        context['selected_status'] = self.request.GET.get('status')
        
        # Estatísticas
        context['total_students'] = context['students'].count()
        
        return context


class ProfessorStudentDetailView(LoginRequiredMixin, ProfessorRequiredMixin, DetailView):
    """
    Mostra detalhes de um aluno específico para o professor, incluindo
    todas as matrículas e pagamentos deste aluno nos cursos do professor.
    """
    model = User
    template_name = 'payments/professor/student_detail.html'
    context_object_name = 'student'
    
    def get_queryset(self):
        professor = self.request.user
        
        # Garantir que o aluno está matriculado em pelo menos um curso do professor
        return User.objects.filter(
            enrollments__course__professor=professor
        ).distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        professor = self.request.user
        student = self.get_object()
        
        # Matrículas do aluno nos cursos do professor
        enrollments = Enrollment.objects.filter(
            student=student,
            course__professor=professor
        )
        context['enrollments'] = enrollments
        
        # Transações do aluno relacionadas aos cursos do professor
        transactions = PaymentTransaction.objects.filter(
            enrollment__student=student,
            enrollment__course__professor=professor
        )
        context['transactions'] = transactions
        
        # Total pago pelo aluno
        total_paid = transactions.filter(status=PaymentTransaction.Status.PAID).aggregate(
            total=Sum('amount')
        )['total'] or 0
        context['total_paid'] = total_paid
        
        # Total pendente do aluno
        total_pending = transactions.filter(status=PaymentTransaction.Status.PENDING).aggregate(
            total=Sum('amount')
        )['total'] or 0
        context['total_pending'] = total_pending
        
        return context


# Views para administradores
class AdminFinancialDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """
    Dashboard financeiro do administrador, mostrando uma visão geral de todas as transações financeiras
    da plataforma, incluindo resumos por professor e curso.
    """
    template_name = 'payments/admin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas gerais
        transactions = PaymentTransaction.objects.all()
        enrollments = Enrollment.objects.all()
        courses = Course.objects.all()
        professors = User.objects.filter(user_type='PROFESSOR')
        
        context['total_courses'] = courses.count()
        context['total_enrollments'] = enrollments.count()
        context['total_professors'] = professors.count()
        
        # Transações por status
        total_paid = transactions.filter(status=PaymentTransaction.Status.PAID).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_pending = transactions.filter(status=PaymentTransaction.Status.PENDING).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_refunded = transactions.filter(status=PaymentTransaction.Status.REFUNDED).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        context['total_received'] = total_paid
        context['total_pending'] = total_pending
        context['total_refunded'] = total_refunded
        context['total_transactions'] = transactions.count()
        
        # Notas fiscais
        try:
            from invoices.models import Invoice
            # Contagem de notas fiscais por status
            invoices = Invoice.objects.all()
            context['invoices_count'] = invoices.count()
            
            # Notas por status
            context['invoices_approved'] = invoices.filter(status='approved').count()
            context['invoices_pending'] = invoices.filter(status='pending').count()
            context['invoices_processing'] = invoices.filter(status='processing').count()
            context['invoices_error'] = invoices.filter(status='error').count()
            
            # Notas fiscais recentes (últimas 5)
            context['recent_invoices'] = invoices.order_by('-created_at')[:5]
        except ImportError:
            # App de notas fiscais não disponível
            context['invoices_count'] = 0
            context['invoices_approved'] = 0
            context['invoices_pending'] = 0
            context['invoices_processing'] = 0
            context['invoices_error'] = 0
            context['recent_invoices'] = []
        
        # Resumo por professor
        professor_stats = []
        for professor in professors:
            prof_courses = courses.filter(professor=professor).count()
            prof_enrollments = enrollments.filter(course__professor=professor).count()
            prof_revenue = transactions.filter(
                enrollment__course__professor=professor,
                status=PaymentTransaction.Status.PAID
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            professor_stats.append({
                'professor': professor,
                'courses': prof_courses,
                'enrollments': prof_enrollments,
                'revenue': prof_revenue
            })
        
        # Ordenar por receita (do maior para o menor)
        professor_stats.sort(key=lambda x: x['revenue'], reverse=True)
        context['professor_stats'] = professor_stats[:10]  # Top 10 professores
        
        # Top cursos por receita
        top_courses = Course.objects.annotate(
            revenue=Sum(
                'enrollments__payments__amount',
                filter=Q(enrollments__payments__status=PaymentTransaction.Status.PAID)
            )
        ).filter(revenue__isnull=False).order_by('-revenue')[:10]
        
        context['top_courses'] = top_courses
        
        # Transações recentes
        context['recent_transactions'] = transactions.select_related(
            'enrollment__student', 'enrollment__course', 'enrollment__course__professor'
        ).order_by('-created_at')[:10]
        
        return context


class AdminTransactionListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    Lista todas as transações financeiras para o administrador, com filtros avançados.
    """
    model = PaymentTransaction
    template_name = 'payments/admin/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = PaymentTransaction.objects.all()\
            .select_related('enrollment__student', 'enrollment__course', 'enrollment__course__professor')
        
        # Filtro por professor
        professor_id = self.request.GET.get('professor')
        if professor_id:
            queryset = queryset.filter(enrollment__course__professor_id=professor_id)
            
        # Filtro por curso
        course_id = self.request.GET.get('course')
        if course_id:
            queryset = queryset.filter(enrollment__course_id=course_id)
            
        # Filtro por status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filtro por data
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
            
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Opções para filtros
        context['professors'] = User.objects.filter(user_type='PROFESSOR')
        context['courses'] = Course.objects.all()
        context['status_choices'] = PaymentTransaction.Status.choices
        
        # Filtros ativos
        context['selected_professor'] = self.request.GET.get('professor', '')
        context['selected_course'] = self.request.GET.get('course', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_date_from'] = self.request.GET.get('date_from', '')
        context['selected_date_to'] = self.request.GET.get('date_to', '')
        
        # Totalizadores
        total_amount = self.get_queryset().aggregate(total=Sum('amount'))['total'] or 0
        context['total_amount'] = total_amount
        
        return context


class AdminProfessorDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """
    Mostra detalhes financeiros de um professor específico para o administrador.
    """
    model = User
    template_name = 'payments/admin/professor_detail.html'
    context_object_name = 'professor'
    
    def get_queryset(self):
        return User.objects.filter(user_type='PROFESSOR')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        professor = self.object
        
        # Cursos do professor
        courses = Course.objects.filter(professor=professor)
        context['courses'] = courses
        context['courses_count'] = courses.count()
        
        # Matrículas e transações
        enrollments = Enrollment.objects.filter(course__professor=professor)
        transactions = PaymentTransaction.objects.filter(enrollment__course__professor=professor)
        
        context['enrollments_count'] = enrollments.count()
        
        # Receita total do professor
        total_revenue = transactions.filter(
            status=PaymentTransaction.Status.PAID
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        context['total_revenue'] = total_revenue
        
        # Estatísticas por curso
        course_stats = []
        for course in courses:
            course_enrollments = enrollments.filter(course=course).count()
            course_revenue = transactions.filter(
                enrollment__course=course,
                status=PaymentTransaction.Status.PAID
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            course_stats.append({
                'course': course,
                'enrollments': course_enrollments,
                'revenue': course_revenue
            })
        
        context['course_stats'] = course_stats
        
        # Transações recentes do professor
        context['recent_transactions'] = transactions.select_related(
            'enrollment__student', 'enrollment__course'
        ).order_by('-created_at')[:10]
        
        return context


# Views para alunos
class StudentPaymentListView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    """
    Exibe a lista de pagamentos e matrículas do aluno.
    """
    template_name = 'payments/student/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        # Retornar todos os pagamentos do aluno
        return PaymentTransaction.objects.filter(
            enrollment__student=self.request.user
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obter todas as matrículas do aluno com seus respectivos pagamentos
        student_enrollments = Enrollment.objects.filter(
            student=self.request.user
        ).select_related(
            'course'
        ).prefetch_related(
            Prefetch(
                'payments',
                queryset=PaymentTransaction.objects.order_by('-created_at')
            )
        ).order_by('-enrolled_at')
        
        enrollments_with_payments = []
            
        for enrollment in student_enrollments:
            transactions = enrollment.payments.all().order_by('-created_at')
            latest_transaction = transactions.first()
            status = latest_transaction.status if latest_transaction else 'NONE'
            
            enrollments_with_payments.append({
                'enrollment': enrollment,
                'transactions': transactions,
                'latest_status': status,
                'is_paid': status == PaymentTransaction.Status.PAID
            })
            
        context['enrollments_with_payments'] = enrollments_with_payments
        
        return context


@login_required
def payment_options(request, course_id):
    """
    Exibe as opções de pagamento disponíveis para o curso.
    
    Args:
        request: Objeto HttpRequest
        course_id: ID do curso
        
    Returns:
        HttpResponse: Página com as opções de pagamento
    """
    # Verificar se o curso existe
    course = get_object_or_404(Course, id=course_id, status=Course.Status.PUBLISHED)
    
    # Verificar se o usuário é um aluno
    if not request.user.is_student:
        messages.error(request, _('Apenas alunos podem se matricular em cursos.'))
        return redirect('courses:course_detail', pk=course.id)
    
    # Verificar se já existe uma matrícula ativa
    existing_enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course,
        status=Enrollment.Status.ACTIVE
    ).first()
    
    if existing_enrollment:
        messages.info(request, _('Você já está matriculado neste curso.'))
        return redirect('courses:student:course_detail', pk=course.id)
    
    # Verificar se existe uma matrícula pendente
    pending_enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course,
        status=Enrollment.Status.PENDING
    ).first()
    
    # Se não existe matrícula pendente, criar uma
    if not pending_enrollment:
        pending_enrollment = Enrollment.objects.create(
            student=request.user,
            course=course,
            status=Enrollment.Status.PENDING
        )
    
    context = {
        'course': course,
        'enrollment': pending_enrollment,
    }
    
    return render(request, 'payments/payment_options.html', context)


class StudentEnrollmentDetailView(LoginRequiredMixin, StudentRequiredMixin, DetailView):
    """
    Mostra detalhes de uma matrícula específica do aluno, incluindo
    histórico completo de pagamentos.
    """
    model = Enrollment
    template_name = 'payments/student/enrollment_detail.html'
    context_object_name = 'enrollment'
    
    def get_queryset(self):
        # Apenas matrículas do aluno atual
        return Enrollment.objects.filter(
            student=self.request.user
        ).select_related('course', 'course__professor')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollment = self.object
        
        # Histórico de pagamentos
        transactions = PaymentTransaction.objects.filter(enrollment=enrollment).order_by('-created_at')
        context['transactions'] = transactions
        
        # Status atual
        latest_transaction = transactions.first()
        context['latest_transaction'] = latest_transaction
        context['is_paid'] = latest_transaction and latest_transaction.status == PaymentTransaction.Status.PAID
        
        return context


@login_required
def emit_payment_charge(request, transaction_id):
    """
    Emite uma cobrança para uma transação pendente, enviando um lembrete de pagamento
    e fornecendo um novo link de pagamento PIX.
    """
    # Obter a transação, garantindo que pertence a um curso do professor atual
    transaction = get_object_or_404(
        PaymentTransaction, 
        id=transaction_id, 
        status=PaymentTransaction.Status.PENDING,
        enrollment__course__professor=request.user
    )
    
    enrollment = transaction.enrollment
    
    try:
        # Criar uma nova cobrança PIX usando o OpenPix
        openpix = OpenPixService()
        charge_data = openpix.create_charge(enrollment)
        
        # Atualizar os dados da transação existente
        transaction.correlation_id = charge_data.get('correlationID')
        transaction.brcode = charge_data.get('brCode')
        transaction.qrcode_image = charge_data.get('qrCodeImage')
        transaction.updated_at = timezone.now()
        transaction.save()
        
        # Enviar um e-mail de cobrança para o aluno (implementação futura)
        
        messages.success(request, f'Cobrança emitida com sucesso para {enrollment.student.email}.')
        
        # Redirecionar para a página de detalhes da transação com um parâmetro para indicar o sucesso
        return redirect(reverse('payments:professor_transactions') + f'?emitted={transaction.id}')
        
    except Exception as e:
        messages.error(request, f'Erro ao emitir cobrança: {str(e)}')
        return redirect('payments:professor_transactions')


# Views para vendas avulsas
class SingleSaleListView(LoginRequiredMixin, ProfessorRequiredMixin, ListView):
    """
    Lista todas as vendas avulsas criadas pelo professor/vendedor.
    """
    model = SingleSale
    template_name = 'payments/professor/singlesale_list.html'
    context_object_name = 'sales'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = SingleSale.objects.filter(seller=self.request.user)
        
        # Filtro por status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filtro por período
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date and end_date:
            try:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                end = end.replace(hour=23, minute=59, second=59)  # Fim do dia
                queryset = queryset.filter(created_at__range=[start, end])
            except ValueError:
                pass
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Status possíveis para o filtro
        context['status_choices'] = SingleSale.Status.choices
        
        # Filtros ativos
        context['selected_status'] = self.request.GET.get('status', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        # Totalizadores
        total_amount = self.get_queryset().aggregate(Sum('amount'))['amount__sum'] or 0
        total_paid = self.get_queryset().filter(status=SingleSale.Status.PAID).aggregate(Sum('amount'))['amount__sum'] or 0
        total_pending = self.get_queryset().filter(status=SingleSale.Status.PENDING).aggregate(Sum('amount'))['amount__sum'] or 0
        
        context['total_amount'] = total_amount
        context['total_paid'] = total_paid
        context['total_pending'] = total_pending
        
        return context


class SingleSaleCreateView(LoginRequiredMixin, ProfessorRequiredMixin, CreateView):
    """
    Permite ao professor/vendedor criar uma nova venda avulsa.
    """
    model = SingleSale
    template_name = 'payments/professor/singlesale_form.html'
    fields = ['description', 'amount', 'customer_name', 'customer_email', 'customer_cpf']
    success_url = reverse_lazy('payments:singlesale_list')
    
    def form_valid(self, form):
        # Define o vendedor como o usuário atual
        form.instance.seller = self.request.user
        
        response = super().form_valid(form)
        
        # Adiciona mensagem de sucesso
        messages.success(self.request, _('Venda avulsa criada com sucesso!'))
        
        return response


class SingleSaleDetailView(LoginRequiredMixin, ProfessorRequiredMixin, DetailView):
    """
    Mostra detalhes de uma venda avulsa específica.
    """
    model = SingleSale
    template_name = 'payments/professor/singlesale_detail.html'
    context_object_name = 'sale'
    
    def get_queryset(self):
        # Garantir que só mostra vendas do professor atual
        return SingleSale.objects.filter(seller=self.request.user)


# View para gerar pagamento via Pix para uma venda avulsa
@login_required
def create_singlesale_pix(request, sale_id):
    """
    Cria um pagamento Pix para uma venda avulsa.
    """
    sale = get_object_or_404(SingleSale, id=sale_id, seller=request.user)
    
    if sale.status == SingleSale.Status.PAID:
        messages.warning(request, _('Esta venda já foi paga!'))
        return redirect('payments:singlesale_detail', pk=sale.id)
    
    if sale.brcode:
        messages.info(request, _('Esta venda já possui um Pix gerado.'))
        return redirect('payments:singlesale_pix_detail', sale_id=sale.id)
    
    # Inicia o serviço de Pix
    openpix_service = OpenPixService()
    
    # Define os dados para a cobrança
    charge_data = {
        'correlationID': str(uuid.uuid4()),
        'value': int(sale.amount * 100),  # Converte para centavos
        'comment': f"Venda: {sale.description}",
        'customer': {
            'name': sale.customer_name,
            'email': sale.customer_email,
            'phone': "",  # Opcional
            'taxID': sale.customer_cpf or ""  # CPF ou CNPJ se disponível
        }
    }
    
    # Cria a cobrança via API
    try:
        response = openpix_service.create_charge_dict(charge_data)
        
        if response and response.get('brCode'):
            # Atualiza a venda com os dados do Pix
            sale.correlation_id = charge_data['correlationID']
            sale.brcode = response.get('brCode')
            sale.qrcode_image = response.get('qrCodeImage')
            sale.save()
            
            messages.success(request, _('Pagamento Pix gerado com sucesso!'))
            return redirect('payments:singlesale_pix_detail', sale_id=sale.id)
        else:
            messages.error(request, _('Erro ao gerar o Pix. Tente novamente.'))
    except Exception as e:
        messages.error(request, _(f'Erro ao gerar o Pix: {str(e)}'))
    
    return redirect('payments:singlesale_detail', pk=sale.id)


@login_required
def singlesale_pix_detail(request, sale_id):
    """
    Exibe os detalhes do pagamento Pix para uma venda avulsa.
    """
    sale = get_object_or_404(SingleSale, id=sale_id)
    
    # Verificar permissão (apenas o vendedor ou o cliente por email)
    is_seller = request.user == sale.seller
    
    if not is_seller and not request.user.is_superuser:
        messages.error(request, _('Você não tem permissão para acessar esta página.'))
        return redirect('home')
    
    context = {
        'sale': sale,
        'is_seller': is_seller
    }
    
    return render(request, 'payments/singlesale_pix_detail.html', context)


@login_required
def check_singlesale_payment_status(request, sale_id):
    """
    Verifica o status do pagamento via API e atualiza o status da venda.
    """
    sale = get_object_or_404(SingleSale, id=sale_id)
    
    # Verificar permissão
    if request.user != sale.seller and not request.user.is_superuser:
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    # Se já está pago, apenas retorna o status
    if sale.status == SingleSale.Status.PAID:
        return JsonResponse({
            'status': sale.status,
            'status_display': sale.get_status_display(),
            'paid_at': sale.paid_at.isoformat() if sale.paid_at else None
        })
    
    # Consulta a API da OpenPix para verificar o status
    openpix_service = OpenPixService()
    
    try:
        payment_info = openpix_service.get_charge(sale.correlation_id)
        
        if payment_info and payment_info.get('status') == 'COMPLETED':
            # Atualiza o status para pago
            sale.mark_as_paid()
            
            # Tenta emitir nota fiscal, se disponível
            try:
                from invoices.models import Invoice
                invoice = Invoice.objects.create(
                    type='rps',
                    transaction=None,  # Não é uma transação de matrícula
                    singlesale=sale,  # Relaciona com a venda avulsa
                    amount=sale.amount,
                    customer_name=sale.customer_name,
                    customer_email=sale.customer_email,
                    customer_tax_id=sale.customer_cpf,
                    description=sale.description,
                    status='pending'
                )
                # O processamento posterior é feito por signals ou tarefas assíncronas
            except (ImportError, Exception) as e:
                print(f"Erro ao criar nota fiscal: {e}")
            
            return JsonResponse({
                'status': sale.status,
                'status_display': sale.get_status_display(),
                'paid_at': sale.paid_at.isoformat()
            })
        
        # Retorna o status atual
        return JsonResponse({
            'status': sale.status,
            'status_display': sale.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


class SingleSaleAdminListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    Lista todas as vendas avulsas para o administrador.
    """
    model = SingleSale
    template_name = 'payments/admin/singlesale_list.html'
    context_object_name = 'sales'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = SingleSale.objects.all()
        
        # Filtros diversos
        seller_id = self.request.GET.get('seller')
        if seller_id:
            queryset = queryset.filter(seller_id=seller_id)
            
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dados para filtros
        context['status_choices'] = SingleSale.Status.choices
        context['selected_status'] = self.request.GET.get('status', '')
        
        # Lista de vendedores para o filtro
        User = get_user_model()
        context['sellers'] = User.objects.filter(sales__isnull=False).distinct()
        context['selected_seller'] = self.request.GET.get('seller', '')
        
        # Totalizadores
        total_amount = self.get_queryset().aggregate(Sum('amount'))['amount__sum'] or 0
        context['total_amount'] = total_amount
        
        return context


class SingleSaleUpdateView(LoginRequiredMixin, ProfessorRequiredMixin, UpdateView):
    """
    Permite ao professor/vendedor atualizar uma venda avulsa existente.
    """
    model = SingleSale
    template_name = 'payments/professor/singlesale_form.html'
    fields = ['description', 'amount', 'customer_name', 'customer_email', 'customer_cpf', 'status']
    
    def get_queryset(self):
        # Garantir que só atualiza vendas do professor atual
        return SingleSale.objects.filter(seller=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy('payments:singlesale_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Venda avulsa atualizada com sucesso!'))
        return response


@login_required
def transaction_list(request):
    """
    Lista todas as transações do usuário.
    """
    # Verificar tipo de usuário
    if request.user.is_professor:
        # Redirecionar para a view específica de professor
        return redirect('payments:professor_transactions')
    
    # Para alunos, mostrar apenas suas próprias transações
    transactions = PaymentTransaction.objects.filter(
        enrollment__student=request.user
    ).select_related('enrollment', 'enrollment__course').order_by('-created_at')
    
    # Adicionar informações de notas fiscais, se disponíveis
    try:
        from invoices.models import Invoice
        transactions = transactions.prefetch_related('invoices')
        has_invoice_app = True
    except ImportError:
        has_invoice_app = False
    
    return render(request, 'payments/transaction_list.html', {
        'transactions': transactions,
        'has_invoice_app': has_invoice_app
    })


@login_required
def emit_invoice_from_transactions(request, transaction_id):
    """
    Emite uma nota fiscal a partir da página de transações.
    """
    # Verificar se o usuário é professor
    if not request.user.is_professor:
        messages.error(request, _('Apenas professores podem emitir notas fiscais.'))
        return redirect('payments:transactions')
    
    # Redirecionar para a função de emissão de nota fiscal no app invoices
    return redirect('invoices:emit', transaction_id=transaction_id)
