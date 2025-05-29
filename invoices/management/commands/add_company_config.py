from django.core.management.base import BaseCommand
from core.models import User
from invoices.models import CompanyConfig

class Command(BaseCommand):
    help = 'Adiciona configurações fiscais de exemplo para um usuário professor'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='professor@example.com', 
                            help='Email do professor para adicionar as configurações')

    def handle(self, *args, **options):
        email = options['email']
        
        try:
            # Encontrar o usuário professor
            professor = User.objects.get(email=email)
            
            # Criar ou atualizar as configurações fiscais
            company_config, created = CompanyConfig.objects.update_or_create(
                user=professor,
                defaults={
                    'enabled': True,
                    'cnpj': '12345678000190',  # CNPJ sem formatação
                    'razao_social': 'Instituto Educação Avançada Ltda',
                    'nome_fantasia': 'Academia Conhecimento Contínuo',
                    'inscricao_municipal': '123456789',
                    'regime_tributario': 'simples_nacional',
                    'endereco': 'Avenida Educadores',
                    'numero': '555',
                    'complemento': 'Sala 302',
                    'bairro': 'Centro',
                    'municipio': 'São Paulo',
                    'uf': 'SP',  # Utiliza o código do estado de SP
                    'cep': '01234567',  # CEP sem o hífen
                    'telefone': '11987654321',  # Telefone sem formatação
                    'email': 'contato@institutoea.com.br'
                }
            )
            
            status = "criadas" if created else "atualizadas"
            self.stdout.write(self.style.SUCCESS(
                f"Configurações fiscais {status} com sucesso para {professor.email}!"
            ))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Usuário {email} não encontrado!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao configurar dados fiscais: {str(e)}"))
