from django.db import models
from django.utils.translation import gettext_lazy as _
from courses.models import Course
from core.models import User

class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', _('Pendente')),
        ('COMPLETED', _('Completo')),
        ('EXPIRED', _('Expirado')),
        ('CANCELLED', _('Cancelado')),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(_('Valor'), max_digits=10, decimal_places=2)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='PENDING')
    correlation_id = models.CharField(_('ID de Correlação'), max_length=255, unique=True)
    brcode = models.TextField(_('BR Code'), blank=True, null=True)
    qrcode_image = models.URLField(_('QR Code URL'), blank=True, null=True)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)
    
    class Meta:
        verbose_name = _('Pagamento')
        verbose_name_plural = _('Pagamentos')
        
    def __str__(self):
        return f"Pagamento {self.id} - {self.user.email} - {self.course.title}"
