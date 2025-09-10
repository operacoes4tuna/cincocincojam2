from django.core.management.base import BaseCommand
from core.models import User, ModulePermission


class Command(BaseCommand):
    help = 'Cria permissões de módulo padrão para usuários existentes'

    def handle(self, *args, **options):
        # Obtém todos os professores
        professors = User.objects.filter(user_type=User.Types.PROFESSOR)
        
        # Contador de permissões criadas
        created_count = 0
        
        # Para cada professor
        for professor in professors:
            self.stdout.write(f"Processando professor: {professor.email}")
            
            # Lista de módulos disponíveis
            modules = [
                ModulePermission.ModuleChoices.DASHBOARD,
                ModulePermission.ModuleChoices.AGENDA,
                ModulePermission.ModuleChoices.CURSOS,
                ModulePermission.ModuleChoices.FINANCAS,
                ModulePermission.ModuleChoices.CLIENTES,
            ]
            
            # Cria permissões para cada módulo
            for module in modules:
                # Verifica se a permissão já existe
                permission, created = ModulePermission.objects.get_or_create(
                    user=professor,
                    module=module,
                    # Por padrão, concede acesso a todos os módulos
                    defaults={'has_access': True}
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        f"  - Criada permissão para módulo {module}"
                    )
                else:
                    self.stdout.write(
                        f"  - Permissão para módulo {module} já existe"
                    )
        
        success_msg = f"Processo concluído! {created_count} permissões criadas."
        self.stdout.write(self.style.SUCCESS(success_msg))