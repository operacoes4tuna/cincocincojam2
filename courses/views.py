from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.base import ContentFile
import boto3
import os
from datetime import datetime

from .models import Course, Lesson, Enrollment, ClassGroup, LessonRelease, Module, ModuleProgress, LessonAttachment
from .forms import CourseForm, LessonForm, CoursePublishForm, ModuleForm

User = get_user_model()


def upload_attachment_to_s3(uploaded_file):
    """
    Faz upload de um arquivo para o S3 e retorna o caminho.
    """
    if not settings.USE_S3:
        return None

    # Gerar nome único para o arquivo
    ext = uploaded_file.name.split('.')[-1]
    filename_base = uploaded_file.name.rsplit('.', 1)[0]
    # Limitar o nome do arquivo e remover caracteres especiais
    filename_base = ''.join(c for c in filename_base if c.isalnum() or c in '-_')[:50]
    filename = f"{filename_base}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    file_path = f"lesson_attachments/{datetime.now().strftime('%Y/%m')}/{filename}"

    # Upload para S3
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    s3_key = f"media-courses/{file_path}"

    # Fazer upload
    uploaded_file.seek(0)  # Garantir que estamos no início do arquivo
    s3_client.upload_fileobj(
        uploaded_file,
        settings.AWS_STORAGE_BUCKET_NAME,
        s3_key,
        ExtraArgs={'ContentType': uploaded_file.content_type or 'application/octet-stream'}
    )

    return file_path


class ProfessorRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários com tipo professor.
    """
    def test_func(self):
        is_professor = self.request.user.is_authenticated and self.request.user.is_professor
        print(f"ProfessorRequiredMixin test_func: usuário {self.request.user}, is_professor={is_professor}, resultado={is_professor}")
        return is_professor


class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários com tipo administrador.
    """
    def test_func(self):
        is_admin = self.request.user.is_authenticated and self.request.user.is_admin
        print(f"AdminRequiredMixin test_func: usuário {self.request.user}, is_admin={is_admin}, resultado={is_admin}")
        return is_admin


class ProfessorOrAdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso a usuários com tipo professor ou administrador.
    """
    def test_func(self):
        is_professor = self.request.user.is_authenticated and self.request.user.is_professor
        is_admin = self.request.user.is_authenticated and self.request.user.is_admin
        return is_professor or is_admin


class StudentRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários com tipo aluno.
    """
    def test_func(self):
        is_student = self.request.user.is_authenticated and self.request.user.is_student
        print(f"StudentRequiredMixin test_func: usuário {self.request.user}, is_student={is_student}, resultado={is_student}")
        return is_student


class ProfessorCourseMixin(UserPassesTestMixin):
    """
    Mixin para verificar se o curso pertence ao professor logado ou se o usuário é administrador.
    """
    def test_func(self):
        print(f"[DEBUG ProfessorCourseMixin] User: {self.request.user.email if self.request.user.is_authenticated else 'Anonymous'}")
        print(f"[DEBUG ProfessorCourseMixin] Model: {getattr(self, 'model', None)}")
        print(f"[DEBUG ProfessorCourseMixin] kwargs: {self.kwargs}")

        # Se é administrador, tem acesso a tudo
        if self.request.user.is_authenticated and self.request.user.is_admin:
            print(f"[DEBUG ProfessorCourseMixin] User is admin - allowing access")
            return True

        # Se não é professor autenticado, não tem acesso
        if not self.request.user.is_authenticated or not self.request.user.is_professor:
            print(f"[DEBUG ProfessorCourseMixin] User is not professor - denying access")
            return False

        # Para ModuleViews (update/delete) onde temos pk do módulo
        if hasattr(self, 'get_object') and self.model == Module:
            try:
                module = self.get_object()
                result = module.course.professor == self.request.user
                print(f"[DEBUG ProfessorCourseMixin] Module check - Course Professor: {module.course.professor.email}, User: {self.request.user.email}, Result: {result}")
                return result
            except Exception as e:
                print(f"[DEBUG ProfessorCourseMixin] Error getting module: {e}")
                pass

        # Para LessonViews (update/delete) onde temos pk da lição
        if hasattr(self, 'get_object') and self.model == Lesson:
            try:
                lesson = self.get_object()
                result = lesson.course.professor == self.request.user
                print(f"[DEBUG ProfessorCourseMixin] Lesson check - Course Professor: {lesson.course.professor.email}, User: {self.request.user.email}, Result: {result}")
                return result
            except Exception as e:
                print(f"[DEBUG ProfessorCourseMixin] Error getting lesson: {e}")
                pass

        # Verificar contexto - para CourseViews usando course_id ou pk
        course_id = self.kwargs.get('course_id')
        if course_id:
            course = get_object_or_404(Course, pk=course_id)
            result = course.professor == self.request.user
            print(f"[DEBUG ProfessorCourseMixin] Course check - Professor: {course.professor.email}, User: {self.request.user.email}, Result: {result}")
            return result

        # Para CourseViews que usam pk diretamente
        if 'pk' in self.kwargs and self.model == Course:
            course = get_object_or_404(Course, pk=self.kwargs['pk'])
            result = course.professor == self.request.user
            print(f"[DEBUG ProfessorCourseMixin] Course pk check - Professor: {course.professor.email}, User: {self.request.user.email}, Result: {result}")
            return result

        print(f"[DEBUG ProfessorCourseMixin] Default return True for CreateView")
        return True  # Para CreateView, que não tem curso ainda


class ProfessorClassGroupMixin(UserPassesTestMixin):
    """
    Mixin para verificar se a turma pertence ao professor logado ou se o usuário é administrador.
    """
    def test_func(self):
        # Se é administrador, tem acesso a tudo
        if self.request.user.is_authenticated and self.request.user.is_admin:
            return True
            
        # Se não é professor autenticado, não tem acesso
        if not self.request.user.is_authenticated or not self.request.user.is_professor:
            return False
        
        # Caso especial para LessonReleaseCreateView (usa class_group_id)
        if hasattr(self, 'kwargs') and 'class_group_id' in self.kwargs:
            class_group_id = self.kwargs['class_group_id']
            try:
                class_group = ClassGroup.objects.get(pk=class_group_id)
                print(f"[DEBUG] ProfessorClassGroupMixin verificando acesso à turma {class_group_id} para professor {self.request.user}")
                return class_group.professor == self.request.user
            except ClassGroup.DoesNotExist:
                return False
            
        # Caso especial para LessonReleaseUpdateView e LessonReleaseDeleteView
        if self.model == LessonRelease and hasattr(self, 'get_object'):
            try:
                lesson_release = self.get_object()
                return lesson_release.class_group.professor == self.request.user
            except:
                return False
            
        # Verificar contexto - para ClassGroupViews
        class_group_id = self.kwargs.get('pk')
        if class_group_id:
            try:
                class_group = ClassGroup.objects.get(pk=class_group_id)
                return class_group.professor == self.request.user
            except ClassGroup.DoesNotExist:
                return False
            
        return True  # Para CreateView, que não tem turma ainda


class DashboardView(LoginRequiredMixin, ProfessorOrAdminRequiredMixin, ListView):
    """
    Dashboard do professor mostrando seus cursos e estatísticas gerais.
    """
    template_name = 'courses/dashboard.html'
    context_object_name = 'courses'
    
    def get_queryset(self):
        # Retorna os cursos do professor logado com contagem de aulas
        return Course.objects.filter(professor=self.request.user).annotate(
            total_lessons=Count('lessons')
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        professor = self.request.user
        
        # Estatísticas básicas de cursos
        courses = self.get_queryset()
        context['total_courses'] = courses.count()
        context['published_courses'] = courses.filter(status=Course.Status.PUBLISHED).count()
        context['draft_courses'] = courses.filter(status=Course.Status.DRAFT).count()
        
        # Cursos recentemente editados
        context['recent_courses'] = courses.order_by('-updated_at')[:5]
        
        # Estatísticas de alunos
        # Alunos ativos nos cursos do professor
        active_students = User.objects.filter(
            user_type='STUDENT',
            enrollments__course__professor=professor,
            enrollments__status=Enrollment.Status.ACTIVE
        ).distinct()
        context['total_students'] = active_students.count()
        
        # Alunos recentes (matriculados nos últimos 30 dias)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_students = User.objects.filter(
            user_type='STUDENT',
            enrollments__course__professor=professor,
            enrollments__enrolled_at__gte=thirty_days_ago
        ).distinct()
        context['recent_students'] = recent_students.count()
        
        # Totalizar ganhos financeiros
        try:
            from payments.models import PaymentTransaction
            # Total recebido (status PAID)
            transactions = PaymentTransaction.objects.filter(enrollment__course__professor=professor)
            total_paid = transactions.filter(status=PaymentTransaction.Status.PAID).aggregate(
                total=Sum('amount')
            )['total'] or 0
            context['total_revenue'] = total_paid
        except:
            # Se o app payments não estiver disponível
            context['total_revenue'] = 0
        
        return context


class CourseListView(LoginRequiredMixin, ProfessorOrAdminRequiredMixin, ListView):
    """
    Lista todos os cursos. Para professores, filtra apenas seus cursos.
    Para administradores, mostra todos os cursos.
    """
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    
    def get_queryset(self):
        # Se o usuário é um administrador, mostra todos os cursos
        if self.request.user.is_admin:
            return Course.objects.all().order_by('-created_at')
            
        # Se é um professor, filtra apenas os cursos dele
        return Course.objects.filter(professor=self.request.user).order_by('-created_at')


class CourseDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Exibe os detalhes de um curso específico, incluindo suas aulas.
    Administradores podem ver qualquer curso, professores apenas seus próprios cursos.
    """
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    
    def test_func(self):
        # Se for administrador, tem acesso a qualquer curso
        if self.request.user.is_admin:
            return True
            
        # Se for professor, só tem acesso aos seus cursos
        if self.request.user.is_professor:
            course = self.get_object()
            return course.professor == self.request.user
        
        # Se for aluno, também tem acesso aos cursos publicados
        if self.request.user.is_student:
            course = self.get_object()
            return course.status == 'PUBLISHED'
            
        return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona os módulos e aulas do curso ao contexto
        context['modules'] = Module.objects.filter(course=self.object).order_by('order').prefetch_related('lessons')
        # Para compatibilidade, também adiciona todas as aulas
        context['lessons'] = Lesson.objects.filter(course=self.object).order_by('module__order', 'order')
        return context


class CourseCreateView(LoginRequiredMixin, ProfessorOrAdminRequiredMixin, CreateView):
    """
    Cria um novo curso.
    """
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:course_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passa o professor atual para o formulário
        kwargs['professor'] = self.request.user
        # Adiciona os arquivos do request para processar uploads
        if self.request.method == 'POST':
            kwargs['files'] = self.request.FILES
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Curso criado com sucesso!')
        return super().form_valid(form)


class CourseUpdateView(LoginRequiredMixin, ProfessorCourseMixin, UpdateView):
    """
    Atualiza um curso existente.
    """
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Adiciona os arquivos do request para processar uploads
        if self.request.method == 'POST':
            kwargs['files'] = self.request.FILES
        return kwargs
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Curso atualizado com sucesso!')
        return super().form_valid(form)


class CourseDeleteView(LoginRequiredMixin, ProfessorCourseMixin, DeleteView):
    """
    Exclui um curso.
    """
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('courses:course_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Curso excluído com sucesso!')
        return super().delete(request, *args, **kwargs)


class CoursePublishView(LoginRequiredMixin, ProfessorCourseMixin, FormView):
    """
    Publica um curso, alterando seu status para publicado.
    """
    form_class = CoursePublishForm
    template_name = 'courses/course_publish.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['pk'])
        return context
    
    def form_valid(self, form):
        course = get_object_or_404(Course, pk=self.kwargs['pk'])
        course.status = Course.Status.PUBLISHED
        course.save()
        messages.success(self.request, f'O curso "{course.title}" foi publicado com sucesso!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.kwargs['pk']})


# Views para aulas
# Views para gerenciamento de Módulos

class ModuleListView(LoginRequiredMixin, ProfessorCourseMixin, ListView):
    """
    Lista todos os módulos de um curso específico.
    """
    model = Module
    template_name = 'courses/module_list.html'
    context_object_name = 'modules'

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return Module.objects.filter(course_id=course_id).order_by('order').prefetch_related('lessons')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return context


class ModuleCreateView(LoginRequiredMixin, ProfessorCourseMixin, CreateView):
    """
    Cria um novo módulo para um curso específico.
    """
    model = Module
    form_class = ModuleForm
    template_name = 'courses/module_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return context

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.kwargs['course_id']})

    def form_valid(self, form):
        messages.success(self.request, 'Módulo criado com sucesso!')
        return super().form_valid(form)


class ModuleUpdateView(LoginRequiredMixin, ProfessorCourseMixin, UpdateView):
    """
    Atualiza um módulo existente.
    """
    model = Module
    form_class = ModuleForm
    template_name = 'courses/module_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['course'] = self.get_object().course
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.course.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Módulo atualizado com sucesso!')
        return super().form_valid(form)


class ModuleDeleteView(LoginRequiredMixin, ProfessorCourseMixin, DeleteView):
    """
    Exclui um módulo.
    """
    model = Module
    template_name = 'courses/module_confirm_delete.html'

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.course.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Módulo excluído com sucesso!')
        return super().delete(request, *args, **kwargs)


# Views para gerenciamento de Aulas

class LessonCreateView(LoginRequiredMixin, ProfessorCourseMixin, CreateView):
    """
    Cria uma nova aula para um curso específico.
    """
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passa o curso atual para o formulário
        kwargs['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return context
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.kwargs['course_id']})
    
    def form_valid(self, form):
        # Salvar a aula primeiro
        response = super().form_valid(form)

        # Processar anexos após criar a aula
        total_attachments = int(self.request.POST.get('total_new_attachments', 0))

        for i in range(1, total_attachments + 1):
            # Verificar se existe anexo com este índice
            title = self.request.POST.get(f'attachment_title_{i}')
            if not title:
                continue

            # Criar o anexo
            attachment = LessonAttachment(
                lesson=self.object,
                title=title,
                description=self.request.POST.get(f'attachment_description_{i}', ''),
                order=i
            )

            # Determinar tipo de anexo
            attachment_type = self.request.POST.get(f'attachment_type_{i}', 'auto')
            if attachment_type != 'auto':
                attachment.attachment_type = attachment_type

            # Verificar se é arquivo ou link
            choice = self.request.POST.get(f'attachment_choice_{i}', 'file')

            if choice == 'file' and f'attachment_file_{i}' in self.request.FILES:
                uploaded_file = self.request.FILES[f'attachment_file_{i}']

                # Se USE_S3 está ativo, fazer upload direto para S3
                if settings.USE_S3:
                    file_path = upload_attachment_to_s3(uploaded_file)
                    if file_path:
                        # Salvar apenas a referência do arquivo no S3
                        attachment.file.name = file_path
                    else:
                        # Fallback para upload local
                        attachment.file = uploaded_file
                else:
                    # Upload local normal
                    attachment.file = uploaded_file

            elif choice == 'link':
                link = self.request.POST.get(f'attachment_link_{i}')
                if link:
                    attachment.link = link

            # Salvar o anexo se tiver arquivo ou link
            if attachment.file or attachment.link:
                attachment.save()

        messages.success(self.request, 'Aula adicionada com sucesso!')
        return response


class LessonUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Atualiza uma aula existente.
    Administradores podem editar qualquer aula, professores apenas suas próprias aulas.
    """
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'
    
    def test_func(self):
        # Se é administrador, pode editar qualquer aula
        if self.request.user.is_admin:
            return True
            
        # Se é professor, só pode editar suas próprias aulas
        if self.request.user.is_professor:
            lesson = self.get_object()
            return lesson.course.professor == self.request.user
            
        return False
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passar o curso associado à aula para o formulário
        kwargs['course'] = self.object.course
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.course.pk})
    
    def form_valid(self, form):
        # Salvar a aula primeiro
        response = super().form_valid(form)

        # Processar remoção de anexos existentes
        remove_ids = self.request.POST.getlist('remove_attachments')
        if remove_ids:
            LessonAttachment.objects.filter(id__in=remove_ids, lesson=self.object).delete()

        # Processar novos anexos
        total_attachments = int(self.request.POST.get('total_new_attachments', 0))

        for i in range(1, total_attachments + 1):
            # Verificar se existe anexo com este índice
            title = self.request.POST.get(f'attachment_title_{i}')
            if not title:
                continue

            # Criar o anexo
            attachment = LessonAttachment(
                lesson=self.object,
                title=title,
                description=self.request.POST.get(f'attachment_description_{i}', ''),
                order=self.object.attachments.count() + i
            )

            # Determinar tipo de anexo
            attachment_type = self.request.POST.get(f'attachment_type_{i}', 'auto')
            if attachment_type != 'auto':
                attachment.attachment_type = attachment_type

            # Verificar se é arquivo ou link
            choice = self.request.POST.get(f'attachment_choice_{i}', 'file')

            if choice == 'file' and f'attachment_file_{i}' in self.request.FILES:
                uploaded_file = self.request.FILES[f'attachment_file_{i}']

                # Se USE_S3 está ativo, fazer upload direto para S3
                if settings.USE_S3:
                    file_path = upload_attachment_to_s3(uploaded_file)
                    if file_path:
                        # Salvar apenas a referência do arquivo no S3
                        attachment.file.name = file_path
                    else:
                        # Fallback para upload local
                        attachment.file = uploaded_file
                else:
                    # Upload local normal
                    attachment.file = uploaded_file

            elif choice == 'link':
                link = self.request.POST.get(f'attachment_link_{i}')
                if link:
                    attachment.link = link

            # Salvar o anexo se tiver arquivo ou link
            if attachment.file or attachment.link:
                attachment.save()

        messages.success(self.request, 'Aula atualizada com sucesso!')
        return response


class LessonDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Exclui uma aula.
    Administradores podem excluir qualquer aula, professores apenas suas próprias aulas.
    """
    model = Lesson
    template_name = 'courses/lesson_confirm_delete.html'
    
    def test_func(self):
        # Se é administrador, pode excluir qualquer aula
        if self.request.user.is_admin:
            return True
            
        # Se é professor, só pode excluir suas próprias aulas
        if self.request.user.is_professor:
            lesson = self.get_object()
            return lesson.course.professor == self.request.user
            
        return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.course.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Aula excluída com sucesso!')
        return super().delete(request, *args, **kwargs)


# API para buscar cursos do professor
@login_required
def api_professor_courses(request):
    """API para buscar cursos do professor logado, para uso em dropdowns e seleções."""
    try:
        if not request.user.is_professor:
            return JsonResponse({'error': 'Acesso negado. Somente professores podem acessar esta API.'}, status=403)
        
        # Buscar cursos do professor logado
        courses = Course.objects.filter(professor=request.user).order_by('title')
        
        # Adicionar contagem de alunos para cada curso
        courses_data = []
        for course in courses:
            student_count = Enrollment.objects.filter(
                course=course, 
                status=Enrollment.Status.ACTIVE
            ).count()
            
            courses_data.append({
                'id': course.id,
                'title': course.title,
                'student_count': student_count
            })
        
        return JsonResponse({'courses': courses_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# VIEWS PARA TURMAS (CLASS GROUPS)

class ClassGroupListView(LoginRequiredMixin, ProfessorOrAdminRequiredMixin, ListView):
    """
    Lista todas as turmas. Para professores, filtra apenas suas turmas.
    Para administradores, mostra todas as turmas.
    """
    model = ClassGroup
    template_name = 'courses/class_group_list.html'
    context_object_name = 'class_groups'
    
    def get_queryset(self):
        # Se o usuário é um administrador, mostra todas as turmas
        if self.request.user.is_admin:
            return ClassGroup.objects.all().order_by('-created_at')
            
        # Se é um professor, filtra apenas as turmas dele
        return ClassGroup.objects.filter(professor=self.request.user).order_by('-created_at')


class ClassGroupDetailView(LoginRequiredMixin, ProfessorClassGroupMixin, DetailView):
    """
    Exibe os detalhes de uma turma específica, incluindo alunos, cursos e liberações de aulas.
    """
    model = ClassGroup
    template_name = 'courses/class_group_detail.html'
    context_object_name = 'class_group'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adiciona dados sobre os alunos da turma
        context['students'] = self.object.students.all()
        context['students_count'] = self.object.students.count()
        
        # Adiciona dados sobre os cursos da turma
        context['courses'] = self.object.courses.all()
        context['courses_count'] = self.object.courses.count()
        
        # Adiciona dados sobre as liberações de aulas da turma
        context['lesson_releases'] = LessonRelease.objects.filter(
            class_group=self.object
        ).select_related('lesson').order_by('release_date')
        
        # Adiciona dados sobre matrículas ativas nesta turma
        context['active_enrollments'] = Enrollment.objects.filter(
            class_group=self.object,
            status=Enrollment.Status.ACTIVE
        ).select_related('student', 'course')
        
        return context


class ClassGroupCreateView(LoginRequiredMixin, ProfessorOrAdminRequiredMixin, CreateView):
    """
    Cria uma nova turma.
    """
    model = ClassGroup
    template_name = 'courses/class_group_form.html'
    fields = ['name', 'description', 'students', 'courses']
    success_url = reverse_lazy('courses:class_group_list')
    
    def form_valid(self, form):
        # Define o professor como o usuário atual
        form.instance.professor = self.request.user
        messages.success(self.request, 'Turma criada com sucesso!')
        return super().form_valid(form)


class ClassGroupUpdateView(LoginRequiredMixin, ProfessorClassGroupMixin, UpdateView):
    """
    Atualiza uma turma existente.
    """
    model = ClassGroup
    template_name = 'courses/class_group_form.html'
    fields = ['name', 'description', 'students', 'courses']
    
    def get_success_url(self):
        return reverse('courses:class_group_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Turma atualizada com sucesso!')
        return super().form_valid(form)


class ClassGroupDeleteView(LoginRequiredMixin, ProfessorClassGroupMixin, DeleteView):
    """
    Exclui uma turma.
    """
    model = ClassGroup
    template_name = 'courses/class_group_confirm_delete.html'
    success_url = reverse_lazy('courses:class_group_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Turma excluída com sucesso!')
        return super().delete(request, *args, **kwargs)


# VIEWS PARA LIBERAÇÃO DE AULAS (LESSON RELEASES)

class LessonReleaseCreateView(LoginRequiredMixin, ProfessorClassGroupMixin, CreateView):
    """
    Cria uma nova liberação de aula para uma turma específica.
    """
    model = LessonRelease
    template_name = 'courses/lesson_release_form.html'
    fields = ['lesson', 'release_date', 'is_released']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        class_group = get_object_or_404(ClassGroup, pk=self.kwargs['class_group_id'])
        
        # Filtrar apenas aulas dos cursos da turma
        form.fields['lesson'].queryset = Lesson.objects.filter(
            course__class_groups=class_group
        ).select_related('course')
        
        return form
    
    def form_valid(self, form):
        try:
            # Define a turma para a liberação de aula
            class_group = get_object_or_404(ClassGroup, pk=self.kwargs['class_group_id'])
            form.instance.class_group = class_group
            
            # Verificar se já existe uma liberação para esta combinação de aula e turma
            lesson = form.cleaned_data['lesson']
            existing_release = LessonRelease.objects.filter(
                class_group=class_group,
                lesson=lesson
            ).exists()
            
            if existing_release:
                messages.error(
                    self.request, 
                    f'Já existe uma liberação para a aula "{lesson.title}" nesta turma. '
                    'Escolha outra aula ou edite a liberação existente.'
                )
                return self.form_invalid(form)
            
            messages.success(self.request, 'Liberação de aula criada com sucesso!')
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f'Erro ao criar liberação: {str(e)}')
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('courses:class_group_detail', kwargs={'pk': self.kwargs['class_group_id']})


class LessonReleaseUpdateView(LoginRequiredMixin, ProfessorClassGroupMixin, UpdateView):
    """
    Atualiza uma liberação de aula existente.
    """
    model = LessonRelease
    template_name = 'courses/lesson_release_form.html'
    fields = ['lesson', 'release_date', 'is_released']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        lesson_release = self.get_object()
        
        # Filtrar apenas aulas dos cursos da turma
        form.fields['lesson'].queryset = Lesson.objects.filter(
            course__class_groups=lesson_release.class_group
        ).select_related('course')
        
        return form
    
    def form_valid(self, form):
        try:
            # Verificar se já existe uma liberação para esta combinação de aula e turma
            lesson = form.cleaned_data['lesson']
            class_group = self.get_object().class_group
            existing_release = LessonRelease.objects.filter(
                class_group=class_group,
                lesson=lesson
            ).exclude(pk=self.get_object().pk).exists()
            
            if existing_release:
                messages.error(
                    self.request, 
                    f'Já existe uma liberação para a aula "{lesson.title}" nesta turma. '
                    'Escolha outra aula ou edite a liberação existente.'
                )
                return self.form_invalid(form)
            
            messages.success(self.request, 'Liberação de aula atualizada com sucesso!')
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f'Erro ao atualizar liberação: {str(e)}')
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('courses:class_group_detail', kwargs={'pk': self.object.class_group.pk})


class LessonReleaseDeleteView(LoginRequiredMixin, ProfessorClassGroupMixin, DeleteView):
    """
    Exclui uma liberação de aula.
    """
    model = LessonRelease
    template_name = 'courses/lesson_release_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('courses:class_group_detail', kwargs={'pk': self.object.class_group.pk})
    
    def delete(self, request, *args, **kwargs):
        lesson_release = self.get_object()
        class_group_id = lesson_release.class_group.pk
        messages.success(request, 'Liberação de aula excluída com sucesso!')
        return super().delete(request, *args, **kwargs)
