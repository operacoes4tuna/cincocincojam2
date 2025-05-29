from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SchedulerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduler'
    verbose_name = _('Agenda do Professor')
    
    def ready(self):
        # Importar sinais quando o aplicativo estiver pronto
        try:
            import scheduler.signals
        except ImportError:
            pass
