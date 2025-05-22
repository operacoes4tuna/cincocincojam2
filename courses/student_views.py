from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Q, Count, Case, When, IntegerField
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone

from .models import Course, Lesson, Enrollment, LessonProgress, ClassGroup, LessonRelease
from .forms import CourseEnrollForm, CourseSearchForm
from core.models import User
from scheduler.models import EventParticipant


class StudentRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários com tipo aluno.
    """
    def test_func(self):
        result = self.request.user.is_authenticated and self.request.user.is_student
        # Log para depuração
        print(f"StudentRequiredMixin test_func: usuário {self.request.user.email}, is_student={self.request.user.is_student}, resultado={result}")
        return result


class EnrollmentRequiredMixin(UserPassesTestMixin):
    """
    Mixin para verificar se o aluno está matriculado no curso e se tem acesso à aula
    de acordo com as liberações de sua turma.
    """
    def test_func(self):
        if not self.request.user.is_authenticated or not self.request.user.is_student:
            print(f"[DEBUG] EnrollmentRequiredMixin: Usuário não autenticado ou não é aluno")
            return False
            
        # Obter o curso da URL
        course_id = self.kwargs.get('course_id') or self.kwargs.get('pk')
        if not course_id:
            print(f"[DEBUG] EnrollmentRequiredMixin: Curso não encontrado na URL")
            return False
            
        course = get_object_or_404(Course, pk=course_id)
        
        # Verificar se existe uma matrícula ativa
        enrollment = Enrollment.objects.filter(
            student=self.request.user, 
            course=course,
            status=Enrollment.Status.ACTIVE
        ).first()
        
        if not enrollment:
            print(f"[DEBUG] EnrollmentRequiredMixin: Nenhuma matrícula ativa encontrada para o curso {course_id}")
            return False
            
        # Se estiver acessando uma aula específica, verificar liberação por turma
        lesson_id = self.kwargs.get('lesson_id')
        if lesson_id and enrollment.class_group:
            lesson = get_object_or_404(Lesson, pk=lesson_id)
            
            # Verificar se a aula está liberada para a turma do aluno
            lesson_released = LessonRelease.objects.filter(
                class_group=enrollment.class_group,
                lesson=lesson,
                is_released=True
            ).exists()
            
            if not lesson_released:
                print(f"[DEBUG] EnrollmentRequiredMixin: Aula {lesson_id} não liberada para a turma {enrollment.class_group.id}")
                return False
                
        # Se não houver turma ou se a verificação de liberação passou, permitir acesso
        print(f"[DEBUG] EnrollmentRequiredMixin: Acesso permitido ao curso {course_id}")
        return True
    
    def handle_no_permission(self):
        # Obter o curso da URL
        course_id = self.kwargs.get('course_id') or self.kwargs.get('pk')
        
        if course_id and self.request.user.is_authenticated and self.request.user.is_student:
            course = get_object_or_404(Course, pk=course_id)
            
            # Verificar se o aluno está matriculado mas com status diferente de ACTIVE
            try:
                enrollment = Enrollment.objects.get(
                    student=self.request.user,
                    course=course
                )
                
                print(f"[DEBUG] EnrollmentRequiredMixin.handle_no_permission: Matrícula encontrada com status {enrollment.status}")
                
                # Se matrícula existe mas está pendente, redirecionar para pagamento
                if enrollment.status == Enrollment.Status.PENDING:
                    messages.warning(self.request, 'Sua matrícula está pendente de pagamento. Por favor, conclua o pagamento para acessar o curso.')
                    print(f"[DEBUG] EnrollmentRequiredMixin: Redirecionando para pagamento PIX do curso {course_id}")
                    return redirect('payments:payment_options', course_id=course_id)
                elif enrollment.status == Enrollment.Status.CANCELLED:
                    messages.warning(self.request, 'Sua matrícula neste curso foi cancelada. Por favor, matricule-se novamente.')
                    print(f"[DEBUG] EnrollmentRequiredMixin: Matrícula cancelada para o curso {course_id}")
                # Verificar se o acesso foi negado por causa de aula não liberada
                elif enrollment.class_group:
                    lesson_id = self.kwargs.get('lesson_id')
                    if lesson_id:
                        messages.warning(
                            self.request, 
                            'Esta aula ainda não foi liberada para sua turma. Entre em contato com seu professor.'
                        )
                        # Redirecionar para a página do curso
                        return redirect('courses:student_course_learn', pk=course_id)
            
            except Enrollment.DoesNotExist:
                print(f"[DEBUG] EnrollmentRequiredMixin: Matrícula não encontrada para o curso {course_id}")
                pass
                
        # Comportamento padrão
        return super().handle_no_permission()


class StudentDashboardView(LoginRequiredMixin, StudentRequiredMixin, ListView):
    """
    Dashboard do aluno mostrando seus cursos matriculados e progresso.
    """
    template_name = 'courses/student/dashboard.html'
    context_object_name = 'enrollments'
    
    def get_queryset(self):
        # Retorna as matrículas ativas do aluno com informações adicionais
        return Enrollment.objects.filter(
            student=self.request.user,
            status=Enrollment.Status.ACTIVE
        ).select_related('course', 'class_group').order_by('-enrolled_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas básicas
        enrollments = self.get_queryset()
        context['total_enrollments'] = enrollments.count()
        context['completed_courses'] = Enrollment.objects.filter(
            student=self.request.user,
            status=Enrollment.Status.COMPLETED
        ).count()
        
        # Calcular o progresso médio
        total_progress = 0
        enrollments_count = enrollments.count()
        
        if enrollments_count > 0:
            for enrollment in enrollments:
                total_progress += enrollment.progress
            avg_progress = int(total_progress / enrollments_count)
        else:
            avg_progress = 0
            
        context['avg_progress'] = avg_progress
        
        # Cursos recentemente acessados
        context['recent_lessons'] = LessonProgress.objects.filter(
            enrollment__student=self.request.user
        ).select_related('lesson', 'enrollment', 'enrollment__course', 'enrollment__class_group'
        ).order_by('-last_accessed_at')[:5]
        
        # Verificar se há cobranças pendentes
        try:
            from payments.models import PaymentTransaction
            
            # Buscar transações pendentes
            pending_transactions = PaymentTransaction.objects.filter(
                enrollment__student=self.request.user,
                status=PaymentTransaction.Status.PENDING
            ).select_related('enrollment', 'enrollment__course', 'enrollment__class_group').order_by('-created_at')
            
            context['pending_transactions'] = pending_transactions
            context['has_pending_payment'] = pending_transactions.exists()
            
            # Se tiver apenas uma transação pendente, facilitar o acesso direto
            if pending_transactions.count() == 1:
                context['single_pending_transaction'] = pending_transactions.first()
        except (ImportError, Exception) as e:
            # Se o módulo payments não estiver disponível ou ocorrer outro erro
            print(f"Erro ao buscar transações pendentes: {e}")
            context['has_pending_payment'] = False
        
        # Verificar convites pendentes para eventos (aulas)
        try:
            from scheduler.models import EventParticipant
            
            # Buscar convites pendentes
            pending_invitations = EventParticipant.objects.filter(
                student=self.request.user,
                attendance_status='PENDING',
                event__start_time__gte=timezone.now()
            ).count()
            
            context['pending_invitations_count'] = pending_invitations
        except (ImportError, Exception) as e:
            # Se o módulo scheduler não estiver disponível ou ocorrer outro erro
            print(f"Erro ao buscar convites pendentes: {e}")
            context['pending_invitations_count'] = 0

        # Buscar turmas do aluno
        context['class_groups'] = ClassGroup.objects.filter(
            students=self.request.user
        ).select_related('professor').prefetch_related('courses')
            
        return context


class CourseListView(LoginRequiredMixin, ListView):
    """
    Lista todos os cursos publicados disponíveis para visualização por alunos e professores.
    """
    model = Course
    template_name = 'courses/student/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Course.objects.filter(
            status=Course.Status.PUBLISHED
        ).select_related('professor').annotate(
            lessons_count=Count('lessons')
        )
        
        # Aplica o filtro de busca, se fornecido
        form = CourseSearchForm(self.request.GET)
        if form.is_valid():
            query = form.cleaned_data.get('query')
            order_by = form.cleaned_data.get('order_by')
            
            if query:
                queryset = queryset.filter(
                    Q(title__icontains=query) | 
                    Q(description__icontains=query) |
                    Q(short_description__icontains=query)
                )
                
            if order_by:
                queryset = queryset.order_by(order_by)
            else:
                queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')
            
        # Para usuários autenticados, tratamento específico por tipo de usuário
        if self.request.user.is_authenticated:
            # Para alunos, marque os cursos em que já estão matriculados
            if self.request.user.is_student:
                enrolled_courses = Enrollment.objects.filter(
                    student=self.request.user,
                    status=Enrollment.Status.ACTIVE
                ).values_list('course_id', flat=True)
                
                queryset = queryset.annotate(
                    is_enrolled=Case(
                        When(id__in=enrolled_courses, then=1),
                        default=0,
                        output_field=IntegerField()
                    )
                )
            # Para professores, marque os cursos que são de sua autoria
            elif self.request.user.is_professor:
                own_courses = Course.objects.filter(
                    professor=self.request.user
                ).values_list('id', flat=True)
                
                queryset = queryset.annotate(
                    is_own_course=Case(
                        When(id__in=own_courses, then=1),
                        default=0,
                        output_field=IntegerField()
                    )
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = CourseSearchForm(self.request.GET)
        context['is_professor'] = self.request.user.is_professor
        context['is_student'] = self.request.user.is_student
        return context


class CourseDetailView(LoginRequiredMixin, DetailView):
    """
    Exibe os detalhes de um curso específico para alunos e professores.
    """
    model = Course
    template_name = 'courses/student/course_detail.html'
    context_object_name = 'course'
    
    def get_queryset(self):
        # Somente cursos publicados podem ser visualizados
        return Course.objects.filter(status=Course.Status.PUBLISHED)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        
        # Verifica o tipo de usuário e suas permissões
        is_enrolled = False
        enrollment = None
        is_course_author = False
        is_admin = False
        
        # Adiciona informações sobre o tipo de usuário ao contexto
        context['is_student'] = self.request.user.is_student
        context['is_professor'] = self.request.user.is_professor
        context['is_admin'] = self.request.user.is_admin

        # Para alunos, verifica matrícula ATIVA
        if self.request.user.is_authenticated and self.request.user.is_student:
            # Verificar se existe alguma matrícula (independente do status) para mostrar status correto
            try:
                any_enrollment = Enrollment.objects.get(
                    student=self.request.user,
                    course=course
                )
                
                context['enrollment_exists'] = True
                context['enrollment_status'] = any_enrollment.status
                
                # Verificar especificamente matrículas ATIVAS
                if any_enrollment.status == Enrollment.Status.ACTIVE:
                    is_enrolled = True
                    enrollment = any_enrollment
                    
                    # Se o aluno está matriculado ativamente, adiciona informações sobre progresso
                    context['enrollment'] = enrollment
                    context['progress_width'] = f"{enrollment.progress}%"
                    
                    # Busca as aulas que o aluno já completou
                    completed_lessons = LessonProgress.objects.filter(
                        enrollment=enrollment,
                        is_completed=True
                    ).values_list('lesson_id', flat=True)
                    
                    context['completed_lessons'] = completed_lessons
            except Enrollment.DoesNotExist:
                context['enrollment_exists'] = False
                
        # Para professores, verifica se é autor do curso
        elif self.request.user.is_authenticated and self.request.user.is_professor:
            is_course_author = (course.professor == self.request.user)
            context['is_course_author'] = is_course_author
            # Professores sempre podem ver todas as aulas
            is_enrolled = True  # Consideramos como "enrolled" para mostrar todas as aulas
            
        # Para administradores, têm acesso completo
        elif self.request.user.is_authenticated and self.request.user.is_admin:
            is_admin = True
            context['is_admin'] = True
            # Admins sempre podem ver todas as aulas
            is_enrolled = True  # Consideramos como "enrolled" para mostrar todas as aulas
                
        context['is_enrolled'] = is_enrolled
        context['enrollment_form'] = CourseEnrollForm()
        
        # Lista de aulas (só mostra todas se estiver matriculado, caso contrário mostra apenas algumas)
        lessons = Lesson.objects.filter(
            course=course,
            status=Lesson.Status.PUBLISHED
        ).order_by('order')
        
        if not is_enrolled:
            # Se não estiver matriculado, mostra apenas algumas aulas como demonstração
            context['lessons'] = lessons[:2]  # Mostra apenas as 2 primeiras aulas
            context['total_lessons'] = lessons.count()
        else:
            context['lessons'] = lessons
            
        return context


class CourseEnrollView(LoginRequiredMixin, View):
    """
    Permite que um aluno se matricule em um curso.
    Permite matrícula direta através de requisição GET ou POST.
    """
    # Removemos o StudentRequiredMixin para facilitar o debug
    
    def get(self, request, *args, **kwargs):
        # Processa a matrícula diretamente sem exigir formulário
        return self.process_enrollment(request, *args, **kwargs)
        
    def post(self, request, *args, **kwargs):
        # Também aceita requisições POST (para compatibilidade com o formulário existente)
        return self.process_enrollment(request, *args, **kwargs)
    
    def process_enrollment(self, request, *args, **kwargs):
        # Log para depuração
        print(f"\n[DEBUG] process_enrollment iniciado para: {request.user.email}")
        print(f"[DEBUG] Tipo de usuário: {request.user.user_type}, is_student: {request.user.is_student}")
        print(f"[DEBUG] Curso ID: {kwargs.get('pk')}")
        
        # Usamos kwargs que foram passados para o método, não self.kwargs
        course = get_object_or_404(
            Course,
            pk=kwargs.get('pk'),
            status=Course.Status.PUBLISHED
        )
        
        # Salva o ID do curso para uso no get_success_url
        self.course_id = course.id
        
        # Verifica se o usuário é um aluno
        if not request.user.is_student:
            messages.error(request, 'Apenas alunos podem se matricular em cursos.')
            print(f"[DEBUG] ERRO: Usuário não é um aluno")
            return redirect('courses:student:course_detail', pk=course.id)
        
        # Verifica se o curso é pago (tem preço maior que zero)
        is_paid_course = course.price and course.price > 0
        print(f"[DEBUG] Curso é pago: {is_paid_course}, Preço: {course.price}")
        
        # Verifica se o aluno já está matriculado
        try:
            print(f"[DEBUG] Tentando matricular {self.request.user.email} no curso {course.id} - {course.title}")
            enrollment, created = Enrollment.objects.get_or_create(
                student=self.request.user,
                course=course,
                defaults={'status': Enrollment.Status.PENDING if is_paid_course else Enrollment.Status.ACTIVE}
            )
            
            print(f"[DEBUG] Matrícula criada: {created}, Status: {enrollment.status}")
            
            # Se o curso é pago e a matrícula estava cancelada ou é nova, redireciona para pagamento
            if is_paid_course and (created or enrollment.status == Enrollment.Status.CANCELLED):
                print(f"[DEBUG] Curso pago - Redirecionando para opções de pagamento")
                # Atualiza o status para 'PENDING' para permitir o pagamento
                enrollment.status = Enrollment.Status.PENDING
                enrollment.save()
                
                # Redireciona para a página de opções de pagamento
                return redirect('payments:payment_options', course_id=course.id)
            
            elif not created and enrollment.status == Enrollment.Status.CANCELLED:
                # Se a matrícula estava cancelada e o curso é gratuito, reativa
                print(f"[DEBUG] Reativando matrícula cancelada para curso gratuito")
                enrollment.status = Enrollment.Status.ACTIVE
                enrollment.save()
                messages.success(self.request, 'Você reativou sua matrícula no curso.')
            elif not created:
                print(f"[DEBUG] Usuário já está matriculado")
                if enrollment.status == Enrollment.Status.ACTIVE:
                    messages.info(self.request, 'Você já está matriculado neste curso.')
                elif enrollment.status == Enrollment.Status.PENDING:
                    print(f"[DEBUG] Redirecionando para opções de pagamento")
                    return redirect('payments:payment_options', course_id=course.id)
            else:
                # Nova matrícula em curso gratuito
                print(f"[DEBUG] Nova matrícula realizada com sucesso em curso gratuito")
                messages.success(self.request, 'Matrícula realizada com sucesso!')
                
                # Cria registros de progresso para todas as aulas
                lessons = Lesson.objects.filter(
                    course=course,
                    status=Lesson.Status.PUBLISHED
                )
                print(f"[DEBUG] Criando registros de progresso para {lessons.count()} aulas")
                
                for lesson in lessons:
                    LessonProgress.objects.get_or_create(
                        enrollment=enrollment,
                        lesson=lesson
                    )
        except Exception as e:
            print(f"[DEBUG] ERRO na matrícula: {str(e)}")
            messages.error(self.request, f'Erro ao processar a matrícula: {str(e)}')
        
        # Não redirecionar para a página de aprendizado se o pagamento está pendente
        # ou se já foi redirecionado para o pagamento
        if is_paid_course and (created or enrollment.status == Enrollment.Status.PENDING):
            # Um redirecionamento para pagamento já deve ter ocorrido em outra parte do código
            # Esta linha provavelmente nunca será alcançada, mas é uma proteção adicional
            print(f"[DEBUG] Tentando redirecionar novamente para pagamento PIX")
            return redirect('payments:payment_options', course_id=course.id)
        else:
            print(f"[DEBUG] Redirecionando para página de aprendizado do curso {self.course_id}")
            return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        # Importante: usar o ID do curso que acabou de ser processado
        url = reverse('courses:student:course_learn', kwargs={'pk': self.course_id})
        print(f"[DEBUG] URL de redirecionamento: {url}")
        return url


class CourseLearnView(LoginRequiredMixin, DetailView):
    """
    Interface para o aluno assistir e acompanhar as aulas de um curso.
    Professores também podem acessar o modo de aprendizado de seus próprios cursos.
    """
    model = Course
    template_name = 'courses/student/course_learn.html'
    context_object_name = 'course'
    
    def get_queryset(self):
        return Course.objects.filter(status=Course.Status.PUBLISHED)
        
    def dispatch(self, request, *args, **kwargs):
        course = get_object_or_404(Course, pk=kwargs['pk'], status=Course.Status.PUBLISHED)
        
        # Adicionar logs para depuração
        user_email = request.user.email
        user_type = request.user.user_type
        print(f"[DEBUG] CourseLearnView.dispatch - usuário: {user_email}, tipo: {user_type}, curso: {kwargs['pk']}")
        
        # Verifica se o usuário é professor e autor do curso
        is_professor = request.user.user_type == User.Types.PROFESSOR
        is_course_author = is_professor and course.professor == request.user
        
        print(f"[DEBUG] is_professor: {is_professor}, is_course_author: {is_course_author}")
        
        # Se não for professor/autor, verifica se está matriculado e com status ACTIVE
        if not (is_professor and is_course_author):
            try:
                enrollment = Enrollment.objects.get(
                    student=request.user,
                    course=course
                )
                
                print(f"[DEBUG] Status da matrícula: {enrollment.status}")
                
                # Verificar se a matrícula está ativa
                if enrollment.status != Enrollment.Status.ACTIVE:
                    if enrollment.status == Enrollment.Status.PENDING:
                        messages.warning(request, 'Sua matrícula está pendente de pagamento. Por favor, conclua o pagamento para acessar o curso.')
                        print(f"[DEBUG] Matrícula pendente, redirecionando para o detalhe do curso")
                        return redirect('payments:payment_options', course_id=course.id)
                    elif enrollment.status == Enrollment.Status.CANCELLED:
                        messages.error(request, 'Sua matrícula neste curso foi cancelada.')
                        print(f"[DEBUG] Matrícula cancelada, redirecionando para o detalhe do curso")
                        return redirect('courses:student:course_detail', pk=course.id)
                    else:
                        messages.error(request, 'Sua matrícula neste curso não está ativa.')
                        print(f"[DEBUG] Matrícula não está ativa, redirecionando para o detalhe do curso")
                        return redirect('courses:student:course_detail', pk=course.id)
                
            except Enrollment.DoesNotExist:
                messages.error(request, 'Você não está matriculado neste curso.')
                print(f"[DEBUG] Usuário não está matriculado, redirecionando para o detalhe do curso")
                return redirect('courses:student:course_detail', pk=course.id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        
        # Verifica se o usuário é um professor e autor do curso
        is_professor = self.request.user.user_type == User.Types.PROFESSOR
        is_course_author = is_professor and course.professor == self.request.user
        
        context['is_professor'] = is_professor
        context['is_course_author'] = is_course_author
        
        # Se é professor e autor do curso, permite acesso sem matrícula
        if is_professor and is_course_author:
            enrollment = None
            context['enrollment'] = None
            context['progress_width'] = "100%"
            context['viewing_as_professor'] = True
        else:
            # Obtém a matrícula do aluno
            enrollment = get_object_or_404(
                Enrollment,
                student=self.request.user,
                course=course,
                status=Enrollment.Status.ACTIVE
            )
            
            context['enrollment'] = enrollment
            context['progress_width'] = f"{enrollment.progress}%"
        
        # Obtém todas as aulas do curso em ordem
        lessons = Lesson.objects.filter(
            course=course,
            status=Lesson.Status.PUBLISHED
        ).order_by('order')
        
        context['lessons'] = lessons
        
        # Verifica qual aula o aluno deve assistir agora (parâmetro ou próxima não concluída)
        lesson_id = self.request.GET.get('lesson_id')
        current_lesson = None
        
        if lesson_id:
            # Se um ID de aula foi fornecido, usa essa aula
            try:
                current_lesson = lessons.get(pk=lesson_id)
            except Lesson.DoesNotExist:
                pass
                
        if not current_lesson and lessons.exists():
            # Encontra a primeira aula não concluída ou a primeira aula
            lesson_progress = LessonProgress.objects.filter(
                enrollment=enrollment,
                is_completed=False
            ).order_by('lesson__order').first()
            
            if lesson_progress:
                current_lesson = lesson_progress.lesson
            else:
                current_lesson = lessons.first()
                
        context['current_lesson'] = current_lesson
        
        # Busca as aulas que o aluno já completou para marcar visualmente
        if enrollment:
            completed_lessons = LessonProgress.objects.filter(
                enrollment=enrollment,
                is_completed=True
            ).values_list('lesson_id', flat=True)
            context['completed_lessons'] = completed_lessons
        else:
            # Para professores, todas as aulas são consideradas completas
            context['completed_lessons'] = [lesson.id for lesson in context['lessons']]
        
        if current_lesson:
            # Atualiza ou cria um registro de progresso para esta aula (apenas para alunos)
            if enrollment:
                lesson_progress, created = LessonProgress.objects.get_or_create(
                    enrollment=enrollment,
                    lesson=current_lesson
                )
            
            # Extrai o ID do vídeo do YouTube, se for um vídeo do YouTube
            youtube_video_id = None
            if current_lesson.video_url:
                import re
                from urllib.parse import urlparse, parse_qs
                
                # Verifica se temos uma URL de vídeo privado configurada
                if current_lesson.private_video_url:
                    # O vídeo privado tem prioridade sobre o YouTube
                    context['private_video_url'] = current_lesson.private_video_url
                else:
                    # Pattern para URLs completas do YouTube
                    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
                    
                    youtube_match = re.match(youtube_regex, current_lesson.video_url)
                    if youtube_match:
                        youtube_video_id = youtube_match.group(6)
                    else:
                        # Se não der match, tenta com urlparse para URLs do tipo youtu.be
                        parsed_url = urlparse(current_lesson.video_url)
                        if 'youtu.be' in parsed_url.netloc:
                            youtube_video_id = parsed_url.path.lstrip('/')
                        
                        # Para URLs do formato youtube.com/watch?v=ID
                        elif 'youtube.com' in parsed_url.netloc:
                            query = parse_qs(parsed_url.query)
                            if 'v' in query:
                                youtube_video_id = query['v'][0]
            
            context['youtube_video_id'] = youtube_video_id
            
            # Determina a aula anterior e a próxima
            lesson_list = list(lessons)
            current_index = lesson_list.index(current_lesson)
            
            if current_index > 0:
                context['prev_lesson'] = lesson_list[current_index - 1]
                
            if current_index < len(lesson_list) - 1:
                context['next_lesson'] = lesson_list[current_index + 1]
            
        return context


class LessonCompleteView(LoginRequiredMixin, EnrollmentRequiredMixin, View):
    """
    View para marcar uma aula como concluída.
    """
    http_method_names = ['post']
    
    def post(self, request, *args, **kwargs):
        course = get_object_or_404(Course, pk=kwargs['course_id'])
        lesson = get_object_or_404(Lesson, pk=kwargs['lesson_id'], course=course)
        
        # Obtém a matrícula do aluno
        enrollment = get_object_or_404(
            Enrollment,
            student=request.user,
            course=course,
            status=Enrollment.Status.ACTIVE
        )
        
        # Marca a aula como concluída
        lesson_progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson
        )
        
        lesson_progress.complete()
        
        messages.success(request, 'Aula marcada como concluída!')
        
        # Retorna para a próxima aula ou para a página do curso
        next_lesson = Lesson.objects.filter(
            course=course,
            order__gt=lesson.order,
            status=Lesson.Status.PUBLISHED
        ).order_by('order').first()
        
        if next_lesson:
            return HttpResponseRedirect(
                reverse('courses:student:course_learn', kwargs={'pk': course.id}) +
                f'?lesson_id={next_lesson.id}'
            )
        else:
            return HttpResponseRedirect(
                reverse('courses:student:course_learn', kwargs={'pk': course.id})
            )


class EnrollmentCancelView(LoginRequiredMixin, EnrollmentRequiredMixin, View):
    """
    View para cancelar a matrícula em um curso.
    """
    http_method_names = ['post']
    
    def post(self, request, *args, **kwargs):
        course = get_object_or_404(Course, pk=kwargs['pk'])
        
        # Obtém a matrícula do aluno
        enrollment = get_object_or_404(
            Enrollment,
            student=request.user,
            course=course,
            status=Enrollment.Status.ACTIVE
        )
        
        # Cancela a matrícula
        enrollment.cancel()
        
        messages.success(request, 'Sua matrícula foi cancelada.')
        
        return HttpResponseRedirect(reverse('courses:student:dashboard'))
