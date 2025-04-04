from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Q, Count, Case, When, IntegerField
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone

from .models import Course, Lesson, Enrollment, LessonProgress
from .forms import CourseEnrollForm, CourseSearchForm


class StudentRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários com tipo aluno.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_student


class EnrollmentRequiredMixin(UserPassesTestMixin):
    """
    Mixin para verificar se o aluno está matriculado no curso.
    """
    def test_func(self):
        if not self.request.user.is_authenticated or not self.request.user.is_student:
            return False
            
        # Obter o curso da URL
        course_id = self.kwargs.get('course_id') or self.kwargs.get('pk')
        if course_id:
            course = get_object_or_404(Course, pk=course_id)
            return Enrollment.objects.filter(
                student=self.request.user, 
                course=course,
                status=Enrollment.Status.ACTIVE
            ).exists()
            
        return False


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
        ).select_related('course').order_by('-enrolled_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas básicas
        enrollments = self.get_queryset()
        context['total_enrollments'] = enrollments.count()
        context['completed_courses'] = Enrollment.objects.filter(
            student=self.request.user,
            status=Enrollment.Status.COMPLETED
        ).count()
        
        # Cursos recentemente acessados
        context['recent_lessons'] = LessonProgress.objects.filter(
            enrollment__student=self.request.user
        ).select_related('lesson', 'enrollment', 'enrollment__course'
        ).order_by('-last_accessed_at')[:5]
        
        return context


class CourseListView(ListView):
    """
    Lista todos os cursos publicados disponíveis para matrícula.
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
            
        # Para usuários autenticados, marque os cursos em que já estão matriculados
        if self.request.user.is_authenticated:
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
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = CourseSearchForm(self.request.GET)
        return context


class CourseDetailView(DetailView):
    """
    Exibe os detalhes de um curso específico para alunos.
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
        
        # Verifica se o aluno está matriculado no curso
        is_enrolled = False
        enrollment = None
        
        if self.request.user.is_authenticated and self.request.user.is_student:
            try:
                enrollment = Enrollment.objects.get(
                    student=self.request.user,
                    course=course,
                    status=Enrollment.Status.ACTIVE
                )
                is_enrolled = True
                
                # Se o aluno está matriculado, adiciona informações sobre progresso
                context['enrollment'] = enrollment
                context['progress_width'] = f"{enrollment.progress}%"
                
                # Busca as aulas que o aluno já completou
                completed_lessons = LessonProgress.objects.filter(
                    enrollment=enrollment,
                    is_completed=True
                ).values_list('lesson_id', flat=True)
                
                context['completed_lessons'] = completed_lessons
                
            except Enrollment.DoesNotExist:
                pass
                
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


class CourseEnrollView(LoginRequiredMixin, StudentRequiredMixin, FormView):
    """
    Permite que um aluno se matricule em um curso.
    """
    form_class = CourseEnrollForm
    template_name = 'courses/student/course_enroll.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(
            Course,
            pk=self.kwargs['pk'],
            status=Course.Status.PUBLISHED
        )
        return context
    
    def form_valid(self, form):
        course = get_object_or_404(
            Course,
            pk=self.kwargs['pk'],
            status=Course.Status.PUBLISHED
        )
        
        # Verifica se o aluno já está matriculado
        enrollment, created = Enrollment.objects.get_or_create(
            student=self.request.user,
            course=course,
            defaults={'status': Enrollment.Status.ACTIVE}
        )
        
        if not created and enrollment.status == Enrollment.Status.CANCELLED:
            # Se a matrícula estava cancelada, reativa
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()
            messages.success(self.request, 'Você reativou sua matrícula no curso.')
        elif not created:
            messages.info(self.request, 'Você já está matriculado neste curso.')
        else:
            messages.success(self.request, 'Matrícula realizada com sucesso!')
            
            # Cria registros de progresso para todas as aulas
            lessons = Lesson.objects.filter(
                course=course,
                status=Lesson.Status.PUBLISHED
            )
            
            for lesson in lessons:
                LessonProgress.objects.get_or_create(
                    enrollment=enrollment,
                    lesson=lesson
                )
        
        return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('courses:student:course_learn', kwargs={'pk': self.kwargs['pk']})


class CourseLearnView(LoginRequiredMixin, EnrollmentRequiredMixin, DetailView):
    """
    Interface para o aluno assistir e acompanhar as aulas de um curso.
    """
    model = Course
    template_name = 'courses/student/course_learn.html'
    context_object_name = 'course'
    
    def get_queryset(self):
        return Course.objects.filter(status=Course.Status.PUBLISHED)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        
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
        completed_lessons = LessonProgress.objects.filter(
            enrollment=enrollment,
            is_completed=True
        ).values_list('lesson_id', flat=True)
        
        context['completed_lessons'] = completed_lessons
        
        if current_lesson:
            # Atualiza ou cria um registro de progresso para esta aula
            lesson_progress, created = LessonProgress.objects.get_or_create(
                enrollment=enrollment,
                lesson=current_lesson
            )
            
            # Extrai o ID do vídeo do YouTube, se for um vídeo do YouTube
            youtube_video_id = None
            if current_lesson.video_url:
                import re
                from urllib.parse import urlparse, parse_qs
                
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
