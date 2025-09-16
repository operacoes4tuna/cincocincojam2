from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Max

from .models import Course, Lesson, Enrollment, LessonProgress, Module


class CourseForm(forms.ModelForm):
    """
    Formulário para criação e edição de cursos.
    """
    class Meta:
        model = Course
        fields = ['title', 'description', 'short_description', 'price', 'image', 'status', 'sequential_modules']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'short_description': forms.TextInput(attrs={'placeholder': 'Breve descrição do curso (máx. 200 caracteres)'}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'sequential_modules': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'sequential_modules': _('Módulos sequenciais (aluno só acessa próximo módulo após completar o anterior)'),
        }
        
    def __init__(self, *args, **kwargs):
        # Remove o campo professor do formulário, pois será preenchido automaticamente
        # com o usuário atual no momento de salvar o formulário
        self.professor = kwargs.pop('professor', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.professor and not instance.pk:  # Somente em criação, não em edição
            instance.professor = self.professor
            
        if commit:
            instance.save()
        return instance


class ModuleForm(forms.ModelForm):
    """
    Formulário para criação e edição de módulos.
    """
    class Meta:
        model = Module
        fields = ['title', 'description', 'order', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'min': '1', 'step': '1', 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': _('Título do Módulo'),
            'description': _('Descrição'),
            'order': _('Ordem'),
            'is_active': _('Módulo ativo'),
        }

    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.course and not instance.pk:
            instance.course = self.course

            # Se a ordem não foi especificada, define como o último módulo + 1
            if not instance.order:
                last_order = Module.objects.filter(course=self.course).aggregate(Max('order'))['order__max'] or 0
                instance.order = last_order + 1

        if commit:
            instance.save()
        return instance


class LessonForm(forms.ModelForm):
    """
    Formulário para criação e edição de aulas.
    """
    class Meta:
        model = Lesson
        fields = ['module', 'title', 'description', 'video_url', 'private_video_url', 'order', 'status']
        widgets = {
            'module': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'min': '0', 'step': '1', 'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'placeholder': 'https://www.youtube.com/watch?v=ID_DO_VIDEO', 'class': 'form-control'}),
            'private_video_url': forms.URLInput(attrs={'placeholder': 'https://play.giancorrea.55jam.com.br/embed/14/HASH', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # Remove o campo course do formulário, pois será preenchido automaticamente
        # com o curso atual no momento de salvar o formulário
        self.course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)

        # Se temos um curso, filtra os módulos apenas deste curso
        if self.course:
            modules = Module.objects.filter(course=self.course, is_active=True).order_by('order')
            self.fields['module'].queryset = modules
            self.fields['module'].required = False  # Torna o módulo opcional
            self.fields['module'].empty_label = "-- Sem módulo (aula avulsa) --"

            # Se não há módulos criados, deixa mais claro que é opcional
            if not modules.exists():
                self.fields['module'].help_text = "Nenhum módulo criado ainda. A aula será criada como avulsa."
            else:
                self.fields['module'].help_text = f"Escolha um dos {modules.count()} módulos disponíveis ou deixe em branco para aula avulsa."

            # Se estamos editando e a aula já tem módulo, pré-seleciona
            if self.instance.pk and self.instance.module:
                self.fields['module'].initial = self.instance.module.pk

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.course:
            # Na criação, define o curso
            if not instance.pk:
                instance.course = self.course

            # Se a ordem não foi especificada, define como a última aula + 1 no módulo
            if not instance.order and instance.module:
                last_order = instance.module.lessons.aggregate(Max('order'))['order__max'] or 0
                instance.order = last_order + 1

        if commit:
            instance.save()
        return instance


class CoursePublishForm(forms.Form):
    """
    Formulário simples para confirmar a publicação de um curso.
    """
    confirm = forms.BooleanField(
        required=True,
        label=_('Confirmo que este curso está pronto para ser publicado'),
        help_text=_('Ao publicar, o curso ficará visível para todos os alunos.')
    )


class CourseEnrollForm(forms.Form):
    """
    Formulário simples para confirmar a matrícula em um curso.
    """
    confirm = forms.BooleanField(
        required=True,
        label=_('Confirmo que desejo me matricular neste curso'),
        help_text=_('Ao se matricular, você terá acesso a todas as aulas deste curso.')
    )


class CourseSearchForm(forms.Form):
    """
    Formulário para pesquisa de cursos no catálogo.
    """
    query = forms.CharField(
        label=_('Buscar cursos'),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Digite um termo de busca...',
            'class': 'form-control'
        })
    )
    
    order_by = forms.ChoiceField(
        label=_('Ordenar por'),
        required=False,
        choices=[
            ('title', _('Título (A-Z)')),
            ('-title', _('Título (Z-A)')),
            ('-created_at', _('Mais recentes')),
            ('price', _('Menor preço')),
            ('-price', _('Maior preço')),
        ],
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
