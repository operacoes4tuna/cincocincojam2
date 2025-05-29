"""
Sinais para o aplicativo de agenda do professor.
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import Event, EventParticipant

@receiver(post_save, sender=Event)
def event_created_or_updated(sender, instance, created, **kwargs):
    """
    Sinal disparado quando um evento é criado ou atualizado.
    Pode ser usado para enviar notificações ou atualizar dados relacionados.
    """
    # Exemplo: No futuro, poderia enviar email para o professor confirmando a criação/atualização
    
    # Se o status foi alterado para cancelado, notificar participantes
    if instance.status == 'CANCELLED' and not created:
        # Placeholder para futura integração de notificações
        # Poderia enviar emails ou alertas no sistema para os participantes
        pass

@receiver(post_save, sender=EventParticipant)
def participant_created_or_updated(sender, instance, created, **kwargs):
    """
    Sinal disparado quando um participante é adicionado a um evento ou seu status é atualizado.
    """
    # Se um participante for confirmado, podemos registrar a data de confirmação
    if instance.attendance_status == 'CONFIRMED' and not instance.confirmed_at:
        # Atualiza o timestamp de confirmação
        instance.confirmed_at = timezone.now()
        # Usa update para evitar recursão infinita
        EventParticipant.objects.filter(pk=instance.pk).update(confirmed_at=timezone.now())
