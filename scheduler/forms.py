from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, HTML, Field, Row, Column

from core.models import User
from courses.models import Course
from .models import Event, EventLocation, EventParticipant

class EventForm(forms.ModelForm):
    """
    Formulário para criação e edição de eventos no calendário.
    """
    # Campos adicionais para facilitar a seleção de data e hora
    date = forms.DateField(
        label=_('Data'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    start_time_hour = forms.TimeField(
        label=_('Horário de início'),
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        required=True
    )
    end_time_hour = forms.TimeField(
        label=_('Horário de término'),
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_type', 'date', 'start_time_hour', 
            'end_time_hour', 'all_day', 'location', 'course', 'max_participants',
            'is_recurring', 'recurrence_rule', 'color', 'status'
        ]
        exclude = ['professor', 'start_time', 'end_time']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'recurrence_rule': forms.TextInput(attrs={
                'placeholder': 'Ex.: FREQ=WEEKLY;COUNT=4;BYDAY=MO',
                'class': 'form-control'
            }),
            'color': forms.Select(choices=[
                ('#3788d8', _('Azul')),
                ('#6aa84f', _('Verde')),
                ('#9900ff', _('Roxo')),
                ('#f1c232', _('Amarelo')),
                ('#cc0000', _('Vermelho')),
            ]),
        }
    
    def __init__(self, *args, **kwargs):
        self.professor = kwargs.pop('professor', None)
        super().__init__(*args, **kwargs)
        
        # Configuração do Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'row g-3'
        
        # Limita locais a estúdios ativos ou criados pelo professor
        if self.professor:
            from django.db.models import Q
            self.fields['location'].queryset = EventLocation.objects.filter(
                Q(created_by=self.professor) | Q(is_active=True)
            )
            self.fields['course'].queryset = Course.objects.filter(
                professor=self.professor
            )
        
        # Se estamos editando um evento existente, popule os campos de data/hora
        if self.instance.pk:
            self.fields['date'].initial = self.instance.start_time.date()
            self.fields['start_time_hour'].initial = self.instance.start_time.time()
            self.fields['end_time_hour'].initial = self.instance.end_time.time()
        
        # Só mostra o campo de recorrência se is_recurring estiver marcado
        self.fields['recurrence_rule'].widget.attrs['style'] = 'display: none;'
        
        # Adiciona tooltips e ajudas
        self.fields['all_day'].help_text = _('Evento que ocupa o dia inteiro.')
        self.fields['max_participants'].help_text = _('Deixe em branco para ilimitado.')
        self.fields['is_recurring'].help_text = _('Gera múltiplas ocorrências com base na regra definida.')
        
        # Layout do formulário com Bootstrap
        self.helper.layout = Layout(
            Fieldset(
                _('Informações Básicas'),
                Row(
                    Column('title', css_class='col-md-8'),
                    Column('event_type', css_class='col-md-4'),
                    css_class='row'
                ),
                'description',
            ),
            Fieldset(
                _('Agendamento'),
                Row(
                    Column('date', css_class='col-md-4'),
                    Column('start_time_hour', css_class='col-md-4'),
                    Column('end_time_hour', css_class='col-md-4'),
                    css_class='row'
                ),
                'all_day',
            ),
            Fieldset(
                _('Estúdio e Participantes'),
                Row(
                    Column('location', css_class='col-md-6'),
                    Column('max_participants', css_class='col-md-6'),
                    css_class='row'
                )
            ),
            Fieldset(
                _('Curso e Status'),
                Row(
                    Column('course', css_class='col-md-6'),
                    Column('status', css_class='col-md-6'),
                    css_class='row'
                )
            ),
            Fieldset(
                _('Configurações Avançadas'),
                Row(
                    Column('is_recurring', css_class='col-md-6'),
                    Column('color', css_class='col-md-6'),
                    css_class='row'
                ),
                'recurrence_rule',
            ),
            Div(
                Submit('submit', _('Salvar'), css_class='btn btn-primary'),
                HTML('<a href="{% url \'scheduler:event_list\' %}" class="btn btn-secondary">' + str(_('Cancelar')) + '</a>'),
                css_class='text-end'
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Verificar se os campos de data e hora estão preenchidos
        date = cleaned_data.get('date')
        start_hour = cleaned_data.get('start_time_hour')
        end_hour = cleaned_data.get('end_time_hour')
        
        if date and start_hour and end_hour:
            # Combinar data e hora em campos datetime
            from datetime import datetime, time
            import pytz
            
            # Usar timezone do Django para garantir que seja timezone-aware
            tz = timezone.get_current_timezone()
            
            # Criar objetos datetime combinando data e hora
            start_dt = timezone.make_aware(
                datetime.combine(date, start_hour),
                timezone=tz
            )
            
            end_dt = timezone.make_aware(
                datetime.combine(date, end_hour),
                timezone=tz
            )
            
            # Se o evento for de dia inteiro, ajustar horários
            if cleaned_data.get('all_day'):
                start_dt = timezone.make_aware(datetime.combine(date, time.min))
                end_dt = timezone.make_aware(datetime.combine(date, time.max))
            
            # Validar que o horário de término é depois do início
            if end_dt <= start_dt:
                raise ValidationError(_('O horário de término deve ser depois do horário de início.'))
            
            # Salvar nos campos do modelo
            cleaned_data['start_time'] = start_dt
            cleaned_data['end_time'] = end_dt
        
        # Validar regra de recorrência
        is_recurring = cleaned_data.get('is_recurring')
        recurrence_rule = cleaned_data.get('recurrence_rule')
        
        if is_recurring and not recurrence_rule:
            self.add_error('recurrence_rule', _('Uma regra de recorrência é necessária para eventos recorrentes.'))
        
        return cleaned_data
    
    def save(self, commit=True):
        event = super().save(commit=False)
        
        # Definir professor se não estiver definido
        if not event.professor and self.professor:
            event.professor = self.professor
        
        # Definir data e hora a partir dos campos auxiliares
        if 'start_time' in self.cleaned_data:
            event.start_time = self.cleaned_data['start_time']
            
        if 'end_time' in self.cleaned_data:
            event.end_time = self.cleaned_data['end_time']
        
        if commit:
            event.save()
        
        return event


class EventLocationForm(forms.ModelForm):
    """
    Formulário para criação e edição de estúdios.
    """
    class Meta:
        model = EventLocation
        fields = ['name', 'address', 'is_online', 'meeting_link', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configuração do Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        # Adiciona classes e atributos aos campos
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['address'].widget.attrs.update({'class': 'form-control', 'rows': '3'})
        self.fields['meeting_link'].widget.attrs.update({'class': 'form-control'})
        
        # Adiciona ajuda para campos
        self.fields['is_online'].help_text = _('Se marcado, este é um estúdio virtual (aulas online).')
        
        # Layout do formulário
        self.helper.layout = Layout(
            Fieldset(
                _('Informações do Estúdio'),
                'name',
                'is_active',
                'is_online',
                Div(
                    'address',
                    css_id='address_div',
                ),
                Div(
                    'meeting_link',
                    css_id='meeting_link_div',
                ),
            ),
            Div(
                Submit('submit', _('Salvar'), css_class='btn btn-primary'),
                HTML('<a href="{% url \'scheduler:location_list\' %}" class="btn btn-secondary">' + str(_('Cancelar')) + '</a>'),
                css_class='text-end mt-3'
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        is_online = cleaned_data.get('is_online')
        address = cleaned_data.get('address')
        meeting_link = cleaned_data.get('meeting_link')
        
        # Validações específicas para estúdios online vs físicos
        if is_online and not meeting_link:
            self.add_error('meeting_link', _('O link de reunião é obrigatório para estúdios online.'))
        
        if not is_online and not address:
            self.add_error('address', _('O endereço é obrigatório para estúdios físicos.'))
        
        return cleaned_data
    
    def save(self, commit=True):
        location = super().save(commit=False)
        
        if commit:
            location.save()
        
        return location


class ParticipantForm(forms.ModelForm):
    """
    Formulário para adicionar participantes a um evento.
    """
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='STUDENT'),
        label=_('Aluno'),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    class Meta:
        model = EventParticipant
        fields = ['student', 'attendance_status', 'notes']
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        # Configuração do Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        # Filtrar estudantes que já não são participantes deste evento
        if self.event:
            existing_participants = self.event.participants.values_list('student_id', flat=True)
            self.fields['student'].queryset = User.objects.filter(
                user_type='STUDENT'
            ).exclude(
                id__in=existing_participants
            )
        
        # Adicionar clases e melhoria aos widgets
        self.fields['notes'].widget.attrs.update({'rows': '3', 'class': 'form-control'})
        
        # Layout do formulário
        self.helper.layout = Layout(
            Fieldset(
                _('Adicionar Participante'),
                'student',
                'attendance_status',
                'notes',
            ),
            Div(
                Submit('submit', _('Adicionar'), css_class='btn btn-primary'),
                HTML('<a href="{% url \'scheduler:participant_list\' event_id=event.id %}" class="btn btn-secondary">' + str(_('Cancelar')) + '</a>'),
                css_class='text-end mt-3'
            )
        )
    
    def save(self, commit=True):
        participant = super().save(commit=False)
        
        # Definir evento se não estiver definido
        if not participant.event and self.event:
            participant.event = self.event
        
        # Se o status for "CONFIRMED", definir confirmed_at
        if participant.attendance_status == 'CONFIRMED' and not participant.confirmed_at:
            participant.confirmed_at = timezone.now()
        
        if commit:
            participant.save()
        
        return participant
