from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from invoices.models import CompanyConfig, ServiceCode

class Command(BaseCommand):
    help = 'Migra códigos de serviço existentes do campo legado para o novo modelo ServiceCode'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa uma simulação sem fazer alterações no banco de dados',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO SIMULAÇÃO - Nenhuma alteração será feita no banco de dados')
            )
        
        # Buscar todas as configurações de empresa que têm código de serviço legado
        configs_with_legacy_code = CompanyConfig.objects.filter(
            city_service_code__isnull=False
        ).exclude(city_service_code='')
        
        migrated_count = 0
        skipped_count = 0
        
        for config in configs_with_legacy_code:
            # Verificar se já existe um código de serviço para esta configuração
            existing_codes = config.service_codes.all()
            
            if existing_codes.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'Pulando {config.user.email} - já possui códigos de serviço cadastrados'
                    )
                )
                skipped_count += 1
                continue
            
            # Criar o código de serviço baseado no campo legado
            if not dry_run:
                ServiceCode.objects.create(
                    company_config=config,
                    code=config.city_service_code,
                    description='Código migrado automaticamente',
                    is_default=True
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'{"[SIMULAÇÃO] " if dry_run else ""}Migrado código {config.city_service_code} '
                    f'para {config.user.email}'
                )
            )
            migrated_count += 1
        
        # Resumo
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Configurações processadas: {migrated_count + skipped_count}')
        self.stdout.write(f'Códigos migrados: {migrated_count}')
        self.stdout.write(f'Configurações puladas: {skipped_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\nEste foi um modo de simulação. Execute novamente sem --dry-run para aplicar as mudanças.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nMigração concluída com sucesso!'
                )
            ) 