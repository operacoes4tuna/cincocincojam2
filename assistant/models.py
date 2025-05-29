from django.db import models
from django.conf import settings

# Create your models here.

class ChatSession(models.Model):
    """Modelo para armazenar uma sessão de chat"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.user:
            return f"Chat de {self.user.username} ({self.session_id})"
        return f"Chat anônimo ({self.session_id})"

class Message(models.Model):
    """Modelo para armazenar mensagens de chat"""
    SENDER_CHOICES = (
        ('user', 'Usuário'),
        ('bot', 'Assistente'),
    )
    
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.get_sender_display()}: {self.content[:50]}..."

class AssistantBehavior(models.Model):
    """
    Modelo para armazenar orientações de comportamento do assistente virtual.
    Permite que administradores definam como o assistente deve se comportar e responder.
    """
    name = models.CharField(max_length=100, verbose_name="Nome do perfil")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    system_prompt = models.TextField(
        verbose_name="Orientações de comportamento", 
        help_text="Instruções que definem o comportamento do assistente. Este texto funcionará como um 'prompt de sistema' para o modelo de IA."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="created_behaviors",
        verbose_name="Criado por"
    )
    
    class Meta:
        verbose_name = "Comportamento do Assistente"
        verbose_name_plural = "Comportamentos do Assistente"
        ordering = ['-is_active', 'name']
    
    def __str__(self):
        status = "Ativo" if self.is_active else "Inativo"
        return f"{self.name} ({status})"
    
    @classmethod
    def get_active_behavior(cls):
        """Retorna o comportamento ativo atual, ou None se não existir"""
        return cls.objects.filter(is_active=True).first()
