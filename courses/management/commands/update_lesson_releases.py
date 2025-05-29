from django.core.management.base import BaseCommand
from django.utils import timezone
from courses.models import LessonRelease


class Command(BaseCommand):
    help = 'Atualiza o status de liberação das aulas baseado na data atual'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Buscar todas as liberações de aulas não liberadas com data passada
        pending_releases = LessonRelease.objects.filter(
            is_released=False,
            release_date__lte=now
        )
        
        # Contar quantas atualizações foram feitas
        count = pending_releases.count()
        
        if count > 0:
            # Atualizar status para liberado
            pending_releases.update(is_released=True)
            self.stdout.write(
                self.style.SUCCESS(f'✅ {count} aulas liberadas com sucesso!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '✅ Nenhuma aula pendente de liberação no momento.'
                )
            ) 