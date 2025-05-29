from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class InvoicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'invoices'
    verbose_name = _('Notas Fiscais')
    
    def ready(self):
        # Importa os sinais quando o aplicativo for inicializado
        import invoices.signals
