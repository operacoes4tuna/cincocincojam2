from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ClientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clients'
    verbose_name = _('Clientes')
