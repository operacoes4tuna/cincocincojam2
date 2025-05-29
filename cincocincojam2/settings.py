# ... existing code ...

# Configurações do NFE.io
NFEIO_API_KEY = os.environ.get('NFEIO_API_KEY', '')
NFEIO_COMPANY_ID = os.environ.get('NFEIO_COMPANY_ID', '')
NFEIO_ENVIRONMENT = os.environ.get('NFEIO_ENVIRONMENT', 'sandbox')
NFEIO_OFFLINE_MODE = os.environ.get('NFEIO_OFFLINE_MODE', 'False') == 'True'

# Configuração das tarefas Cron
CRON_CLASSES = [
    'core.cron.UpdateLessonReleasesCronJob',
    # ... outras tarefas cron existentes ...
]

# ... existing code ...