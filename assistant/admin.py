from django.contrib import admin
from .models import ChatSession, Message, AssistantBehavior

# Register your models here.

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_id', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'session_id')
    date_hierarchy = 'created_at'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat_session', 'sender', 'content_preview', 'timestamp')
    list_filter = ('sender', 'timestamp')
    search_fields = ('content', 'chat_session__user__username')
    date_hierarchy = 'timestamp'
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    
    content_preview.short_description = 'Conteúdo'

@admin.register(AssistantBehavior)
class AssistantBehaviorAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_by', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'system_prompt')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'is_active', 'created_by')
        }),
        ('Comportamento do Assistente', {
            'fields': ('system_prompt',),
            'description': 'Define as instruções que orientam o comportamento do assistente virtual. Estas instruções serão usadas como prompt de sistema para o modelo de IA.'
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Registra o usuário que criou o comportamento"""
        if not change:  # Se é uma criação e não uma edição
            obj.created_by = request.user
        
        # Se este comportamento está sendo ativado, desativa todos os outros
        if obj.is_active:
            AssistantBehavior.objects.exclude(pk=obj.pk).update(is_active=False)
            
        super().save_model(request, obj, form, change)
