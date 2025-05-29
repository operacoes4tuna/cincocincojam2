from django.core.management import call_command
from django_cron import CronJobBase, Schedule


class UpdateLessonReleasesCronJob(CronJobBase):
    RUN_EVERY_MINS = 30  # executa a cada 30 minutos
    
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'core.cron.update_lesson_releases'
    
    def do(self):
        call_command('update_lesson_releases') 