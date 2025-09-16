from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.urls import path

from .models import Course, Lesson, Enrollment, ClassGroup, LessonRelease, Module, ModuleProgress


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo ClassGroup.
    """
    list_display = ['name', 'professor', 'get_students_count', 'get_courses_count', 'created_at']
    list_filter = ['created_at', 'professor']
    search_fields = ['name', 'description', 'professor__email', 'professor__first_name']
    filter_horizontal = ['students', 'courses']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('professor', 'name', 'description'),
        }),
        (_('Associações'), {
            'fields': ('students', 'courses'),
        }),
        (_('Metadados'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def get_students_count(self, obj):
        """Retorna o número de alunos na turma."""
        return obj.students.count()
    get_students_count.short_description = _('Alunos')
    
    def get_courses_count(self, obj):
        """Retorna o número de cursos na turma."""
        return obj.courses.count()
    get_courses_count.short_description = _('Cursos')


@admin.register(LessonRelease)
class LessonReleaseAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo LessonRelease.
    """
    list_display = ['lesson', 'class_group', 'release_date', 'is_released']
    list_filter = ['is_released', 'class_group', 'release_date']
    search_fields = ['lesson__title', 'class_group__name']
    readonly_fields = []
    autocomplete_fields = ['class_group', 'lesson']
    date_hierarchy = 'release_date'
    
    fieldsets = (
        (None, {
            'fields': ('class_group', 'lesson', 'release_date', 'is_released'),
        }),
    )
    
    actions = ['mark_as_released']
    
    def mark_as_released(self, request, queryset):
        """Marca as liberações selecionadas como liberadas."""
        updated = queryset.update(is_released=True)
        messages.success(request, _(f'{updated} liberações marcadas como liberadas com sucesso.'))
    mark_as_released.short_description = _('Marcar como liberadas')


class LessonInline(admin.TabularInline):
    """
    Inline para gerenciar aulas dentro da interface de administração de um módulo.
    """
    model = Lesson
    extra = 1
    fields = ('title', 'order', 'video_url', 'status')
    ordering = ['order']


class ModuleInline(admin.TabularInline):
    """
    Inline para gerenciar módulos dentro da interface de administração de um curso.
    """
    model = Module
    extra = 1
    fields = ('title', 'order', 'description', 'is_active')
    ordering = ['order']
    

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo Course.
    """
    list_display = ('title', 'professor', 'price', 'status', 'created_at', 'get_lessons_count')
    list_filter = ('status', 'created_at', 'professor')
    search_fields = ('title', 'description', 'professor__email', 'professor__first_name')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('professor', 'title', 'slug', 'description', 'short_description', 'price', 'image')
        }),
        (_('Configurações de Acesso'), {
            'fields': ('sequential_modules',)
        }),
        (_('Status e Controle'), {
            'fields': ('status', 'created_at', 'updated_at')
        }),
    )

    inlines = [ModuleInline]
    
    def get_lessons_count(self, obj):
        """Retorna o número de aulas do curso."""
        return obj.lessons.count()
    get_lessons_count.short_description = _('Aulas')


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo Module.
    """
    list_display = ('title', 'course', 'order', 'is_active', 'get_lessons_count', 'created_at')
    list_filter = ('is_active', 'course', 'created_at')
    search_fields = ('title', 'description', 'course__title')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['course']

    fieldsets = (
        (None, {
            'fields': ('course', 'title', 'description', 'order')
        }),
        (_('Configurações'), {
            'fields': ('is_active',)
        }),
        (_('Metadados'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    inlines = [LessonInline]

    def get_lessons_count(self, obj):
        """Retorna o número de aulas do módulo."""
        return obj.lessons.count()
    get_lessons_count.short_description = _('Aulas')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo Lesson.
    """
    list_display = ('title', 'module', 'course', 'order', 'status', 'created_at')
    list_filter = ('status', 'module', 'course', 'created_at')
    search_fields = ('title', 'description', 'module__title', 'course__title')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['course', 'module']

    fieldsets = (
        (None, {
            'fields': ('course', 'module', 'title', 'description', 'order')
        }),
        (_('Vídeo'), {
            'fields': ('video_url', 'private_video_url', 'youtube_id')
        }),
        (_('Status e Controle'), {
            'fields': ('status', 'created_at', 'updated_at')
        }),
    )


class EnrollmentStatusFilter(SimpleListFilter):
    """Filtro personalizado para status de matrícula"""
    title = _('Status da matrícula')
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        return Enrollment.Status.choices
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo Enrollment.
    Permite matricular alunos em cursos diretamente.
    """
    list_display = ('id', 'student_email', 'course_title', 'class_group', 'status', 'progress', 'enrolled_at')
    list_filter = (EnrollmentStatusFilter, 'class_group', 'enrolled_at', 'course')
    search_fields = ('student__email', 'student__first_name', 'course__title', 'class_group__name')
    readonly_fields = ('enrolled_at', 'completed_at', 'progress')
    raw_id_fields = ('student', 'course', 'class_group')
    actions = ['activate_enrollment', 'cancel_enrollment']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('criar-matricula/', 
                 self.admin_site.admin_view(self.create_enrollment_view), 
                 name='courses_enrollment_criar_matricula'),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        """Adiciona botão de matricular na listagem de matrículas"""
        extra_context = extra_context or {}
        extra_context['has_create_enrollment_button'] = True
        return super().changelist_view(request, extra_context=extra_context)
    
    def student_email(self, obj):
        """Retorna o email do aluno da matrícula"""
        return obj.student.email
    student_email.short_description = _('Aluno')
    
    def course_title(self, obj):
        """Retorna o título do curso da matrícula"""
        return obj.course.title
    course_title.short_description = _('Curso')
    
    def activate_enrollment(self, request, queryset):
        """Ativa as matrículas selecionadas"""
        count = 0
        for enrollment in queryset:
            if enrollment.status != Enrollment.Status.ACTIVE:
                enrollment.status = Enrollment.Status.ACTIVE
                enrollment.save()
                count += 1
        
        messages.success(request, _(f'{count} matrículas ativadas com sucesso.'))
    activate_enrollment.short_description = _('Ativar matrículas selecionadas')
    
    def cancel_enrollment(self, request, queryset):
        """Cancela as matrículas selecionadas"""
        count = 0
        for enrollment in queryset:
            if enrollment.status != Enrollment.Status.CANCELLED:
                enrollment.status = Enrollment.Status.CANCELLED
                enrollment.save()
                count += 1
        
        messages.success(request, _(f'{count} matrículas canceladas com sucesso.'))
    cancel_enrollment.short_description = _('Cancelar matrículas selecionadas')
    
    def create_enrollment_view(self, request):
        """View para criar uma matrícula diretamente"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Contexto inicial
        context = {
            'title': _('Matricular aluno em curso'),
            'app_label': 'courses',
            'opts': Enrollment._meta,
            'has_view_permission': True,
        }
        
        # Se for um POST, tenta criar a matrícula
        if request.method == 'POST':
            student_id = request.POST.get('student')
            course_id = request.POST.get('course')
            class_group_id = request.POST.get('class_group')
            status = request.POST.get('status', Enrollment.Status.ACTIVE)
            
            if student_id and course_id:
                try:
                    student = User.objects.get(id=student_id)
                    course = Course.objects.get(id=course_id)
                    class_group = None
                    
                    if class_group_id:
                        class_group = ClassGroup.objects.get(id=class_group_id)
                    
                    # Verifica se já existe matrícula
                    existing = Enrollment.objects.filter(
                        student=student, 
                        course=course,
                        class_group=class_group
                    ).first()
                    
                    if existing:
                        # Atualiza status se já existir
                        existing.status = status
                        existing.save()
                        messages.success(
                            request, 
                            _(f'Matrícula de {student.email} atualizada no curso "{course.title}"!')
                        )
                    else:
                        # Cria nova matrícula
                        enrollment = Enrollment.objects.create(
                            student=student,
                            course=course,
                            class_group=class_group,
                            status=status
                        )
                        
                        # Adiciona o aluno à turma, se especificada
                        if class_group:
                            class_group.students.add(student)
                            
                        messages.success(
                            request, 
                            _(f'Aluno {student.email} matriculado no curso "{course.title}" com sucesso!')
                        )
                        
                    return redirect('admin:courses_enrollment_changelist')
                except (User.DoesNotExist, Course.DoesNotExist, ClassGroup.DoesNotExist) as e:
                    messages.error(request, _(f'Erro ao criar matrícula: {str(e)}'))
            else:
                messages.error(request, _('Selecione um aluno e um curso para criar a matrícula.'))
        
        # Lista de estudantes, cursos e turmas
        students = User.objects.filter(user_type='STUDENT').order_by('email')
        courses = Course.objects.filter(status=Course.Status.PUBLISHED).order_by('title')
        class_groups = ClassGroup.objects.all().order_by('name')
        
        context.update({
            'students': students,
            'courses': courses,
            'class_groups': class_groups,
            'status_choices': Enrollment.Status.choices,
        })
        
        return TemplateResponse(
            request,
            'admin/courses/enrollment/create_enrollment.html',
            context
        )


@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo ModuleProgress.
    """
    list_display = ('get_student_email', 'get_module_title', 'progress_percentage', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'completed_at')
    search_fields = ('enrollment__student__email', 'module__title', 'module__course__title')
    readonly_fields = ('completed_at', 'last_accessed_at', 'progress_percentage')
    raw_id_fields = ('enrollment', 'module')

    def get_student_email(self, obj):
        """Retorna o email do aluno."""
        return obj.enrollment.student.email
    get_student_email.short_description = _('Aluno')

    def get_module_title(self, obj):
        """Retorna o título do módulo."""
        return f"{obj.module.course.title} - {obj.module.title}"
    get_module_title.short_description = _('Módulo')
