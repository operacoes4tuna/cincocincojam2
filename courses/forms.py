from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Max

from .models import Course, Lesson, Enrollment, LessonProgress


class CourseForm(forms.ModelForm):
    """
    Formulário para criação e edição de cursos.
    """
    class Meta:
        model = Course
        fields = ['title', 'description', 'short_description', 'price', 'image', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'short_description': forms.TextInput(attrs={'placeholder': 'Breve descrição do curso (máx. 200 caracteres)'}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
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


class LessonForm(forms.ModelForm):
    """
    Formulário para criação e edição de aulas.
    """
    class Meta:
        model = Lesson
        fields = ['title', 'description', 'video_url', 'private_video_url', 'order', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'order': forms.NumberInput(attrs={'min': '0', 'step': '1'}),
            'video_url': forms.URLInput(attrs={'placeholder': 'https://www.youtube.com/watch?v=ID_DO_VIDEO'}),
            'private_video_url': forms.URLInput(attrs={'placeholder': 'https://play.giancorrea.55jam.com.br/embed/14/HASH'}),
        }
        
    def __init__(self, *args, **kwargs):
        # Remove o campo course do formulário, pois será preenchido automaticamente
        # com o curso atual no momento de salvar o formulário
        self.course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.course and not instance.pk:  # Somente em criação, não em edição
            instance.course = self.course
            
            # Se a ordem não foi especificada, define como a última aula + 1
            if not instance.order and hasattr(self.course, 'lessons'):
                last_order = self.course.lessons.aggregate(Max('order'))['order__max'] or 0
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
