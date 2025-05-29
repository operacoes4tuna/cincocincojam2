from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Invoice

@receiver(post_save, sender=Invoice)
def handle_invoice_update(sender, instance, created, **kwargs):
    """
    Manipula eventos após o salvamento de uma Invoice.
    Atualiza a data de emissão quando o status muda para 'approved'.
    """
    if not created and instance.status == 'approved' and not instance.emitted_at:
        # Se a nota foi aprovada pela primeira vez, atualiza a data de emissão
        instance.emitted_at = timezone.now()
        # Evita recursão chamando save com update_fields
        Invoice.objects.filter(pk=instance.pk).update(emitted_at=instance.emitted_at)
