from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from core.models import User
from courses.models import Course

class EventLocation(models.Model):
    """
    Modelo para armazenar estúdios onde os eventos/aulas podem acontecer.
    Pode ser um estúdio físico ou virtual (online).
    """
    name = models.CharField(_('Nome do estúdio'), max_length=200)
    address = models.TextField(_('Endereço'), blank=True, null=True, 
                               help_text=_('Endereço físico do estúdio (caso não seja online)'))
    is_online = models.BooleanField(_('Online?'), default=False,
                                   help_text=_('Marque esta opção se for um estúdio virtual/online'))
    meeting_link = models.URLField(_('Link da reunião'), blank=True, null=True,
                                  help_text=_('Link da sala virtual (Zoom, Meet, etc.)'))
    phone = models.CharField(_('Telefone'), max_length=20, blank=True, null=True,
                            help_text=_('Telefone de contato da unidade'))
    email = models.EmailField(_('Email'), blank=True, null=True,
                             help_text=_('Email de contato da unidade'))
    image = models.ImageField(_('Foto'), upload_to='studios/', blank=True, null=True,
                             help_text=_('Imagem da unidade'))
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_locations',
        verbose_name=_('Criado por')
    )
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    is_active = models.BooleanField(_('Ativo?'), default=True,
                                   help_text=_('Desmarque para ocultar este estúdio sem excluí-lo'))
    
    class Meta:
        verbose_name = _('Estúdio')
        verbose_name_plural = _('Estúdios')
        ordering = ['name']
    
    def __str__(self):
        if self.is_online:
            return f"{self.name} (Online)"
        return self.name

class Event(models.Model):
    """
    Modelo para eventos/aulas agendados pelo professor.
    Pode estar vinculado a um curso e ter alunos participantes.
    """
    # Tipos de evento
    EVENT_TYPE_CHOICES = [
        ('CLASS', _('Aula regular')),
        ('WORKSHOP', _('Workshop')),
        ('EXAM', _('Avaliação')),
        ('MEETING', _('Reunião')),
        ('OTHER', _('Outro'))
    ]
    
    # Status do evento
    STATUS_CHOICES = [
        ('SCHEDULED', _('Agendado')),
        ('CONFIRMED', _('Confirmado')),
        ('CANCELLED', _('Cancelado')),
        ('COMPLETED', _('Concluído'))
    ]
    
    title = models.CharField(_('Título'), max_length=200)
    description = models.TextField(_('Descrição'), blank=True)
    event_type = models.CharField(
        _('Tipo de evento'), 
        max_length=20, 
        choices=EVENT_TYPE_CHOICES,
        default='CLASS'
    )
    start_time = models.DateTimeField(_('Horário de início'))
    end_time = models.DateTimeField(_('Horário de término'))
    all_day = models.BooleanField(_('Dia inteiro?'), default=False)
    location = models.ForeignKey(
        EventLocation, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='events',
        verbose_name=_('Local')
    )
    professor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='professor_events',
        limit_choices_to={'user_type': 'PROFESSOR'},
        verbose_name=_('Professor')
    )
    course = models.ForeignKey(
        Course, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='course_events',
        verbose_name=_('Curso')
    )
    is_recurring = models.BooleanField(_('Recorrente?'), default=False)
    recurrence_rule = models.CharField(_('Regra de recorrência'), max_length=200, blank=True, null=True)
    color = models.CharField(_('Cor'), max_length=20, default='#3788d8')
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED'
    )
    max_participants = models.PositiveIntegerField(_('Máximo de participantes'), null=True, blank=True)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    
    class Meta:
        verbose_name = _('Evento')
        verbose_name_plural = _('Eventos')
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['professor', 'start_time']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def duration_minutes(self):
        """Retorna a duração do evento em minutos"""
        if self.all_day:
            return 24 * 60  # 24 horas em minutos
        
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 60
    
    @property
    def is_past(self):
        """Verifica se o evento já passou"""
        return self.end_time < timezone.now()
    
    @property
    def participant_count(self):
        """Retorna o número de participantes confirmados"""
        return self.participants.filter(attendance_status='CONFIRMED').count()

class EventParticipant(models.Model):
    """
    Modelo para participantes de um evento/aula.
    Relaciona alunos a eventos e armazena status de presença.
    """
    ATTENDANCE_STATUS_CHOICES = [
        ('CONFIRMED', _('Confirmado')),
        ('PENDING', _('Pendente')),
        ('CANCELLED', _('Cancelado')),
        ('ATTENDED', _('Compareceu')),
        ('MISSED', _('Faltou'))
    ]
    
    event = models.ForeignKey(
        Event, 
        on_delete=models.CASCADE, 
        related_name='participants',
        verbose_name=_('Evento')
    )
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='student_events',
        limit_choices_to={'user_type': 'STUDENT'},
        verbose_name=_('Aluno')
    )
    attendance_status = models.CharField(
        _('Status de presença'),
        max_length=20,
        choices=ATTENDANCE_STATUS_CHOICES,
        default='PENDING'
    )
    notes = models.TextField(_('Anotações'), blank=True)
    confirmed_at = models.DateTimeField(_('Confirmado em'), null=True, blank=True)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    
    class Meta:
        verbose_name = _('Participante do evento')
        verbose_name_plural = _('Participantes do evento')
        ordering = ['event__start_time', 'student__first_name']
        unique_together = ['event', 'student']  # Evita duplicidades
        indexes = [
            models.Index(fields=['event', 'attendance_status']),
        ]
    
    def __str__(self):
        return f"{self.student.first_name} - {self.event.title}"
    
    def confirm_attendance(self):
        """Marca o participante como confirmado"""
        self.attendance_status = 'CONFIRMED'
        self.confirmed_at = timezone.now()
        self.save()
    
    def mark_as_attended(self):
        """Marca o participante como presente no evento"""
        self.attendance_status = 'ATTENDED'
        self.save()
    
    def mark_as_missed(self):
        """Marca o participante como ausente no evento"""
        self.attendance_status = 'MISSED'
        self.save()
