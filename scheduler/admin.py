from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import EventLocation, Event, EventParticipant

@admin.register(EventLocation)
class EventLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_online', 'created_by', 'is_active', 'created_at')
    list_filter = ('is_online', 'is_active', 'created_at')
    search_fields = ('name', 'address')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        (_('Detalhes do Estúdio'), {
            'fields': ('address', 'is_online', 'meeting_link')
        }),
        (_('Informações do Sistema'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class EventParticipantInline(admin.TabularInline):
    model = EventParticipant
    extra = 0
    autocomplete_fields = ['student']
    readonly_fields = ('created_at', 'confirmed_at')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'professor', 'start_time', 'end_time', 'status', 'participant_count')
    list_filter = ('event_type', 'status', 'professor', 'start_time')
    search_fields = ('title', 'description', 'professor__first_name', 'professor__last_name')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['professor', 'course', 'location']
    date_hierarchy = 'start_time'
    inlines = [EventParticipantInline]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'event_type', 'status')
        }),
        (_('Agendamento'), {
            'fields': ('start_time', 'end_time', 'all_day')
        }),
        (_('Local e Participantes'), {
            'fields': ('location', 'max_participants')
        }),
        (_('Curso e Professor'), {
            'fields': ('professor', 'course')
        }),
        (_('Configurações Avançadas'), {
            'fields': ('is_recurring', 'recurrence_rule', 'color'),
            'classes': ('collapse',)
        }),
        (_('Informações do Sistema'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """
        Otimização de consulta com eager loading para evitar N+1 queries
        """
        return super().get_queryset(request).select_related(
            'professor', 'course', 'location'
        ).prefetch_related('participants')

@admin.register(EventParticipant)
class EventParticipantAdmin(admin.ModelAdmin):
    list_display = ('student', 'event', 'attendance_status', 'confirmed_at')
    list_filter = ('attendance_status', 'event__status', 'event__start_time')
    search_fields = ('student__first_name', 'student__last_name', 'event__title')
    readonly_fields = ('created_at', 'updated_at', 'confirmed_at')
    autocomplete_fields = ['student', 'event']
    
    fieldsets = (
        (None, {
            'fields': ('event', 'student')
        }),
        (_('Status'), {
            'fields': ('attendance_status', 'notes')
        }),
        (_('Informações do Sistema'), {
            'fields': ('confirmed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """
        Otimização de consulta com eager loading
        """
        return super().get_queryset(request).select_related('student', 'event')
    
    actions = ['mark_as_confirmed', 'mark_as_attended', 'mark_as_missed']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(attendance_status='CONFIRMED', confirmed_at=timezone.now())
        self.message_user(request, _(f'{updated} participantes foram confirmados com sucesso.'))
    mark_as_confirmed.short_description = _('Marcar selecionados como confirmados')
    
    def mark_as_attended(self, request, queryset):
        updated = queryset.update(attendance_status='ATTENDED')
        self.message_user(request, _(f'{updated} participantes foram marcados como presentes.'))
    mark_as_attended.short_description = _('Marcar selecionados como presentes')
    
    def mark_as_missed(self, request, queryset):
        updated = queryset.update(attendance_status='MISSED')
        self.message_user(request, _(f'{updated} participantes foram marcados como ausentes.'))
    mark_as_missed.short_description = _('Marcar selecionados como ausentes')
