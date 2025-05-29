import os
import django

# Configurar ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User
from invoices.models import CompanyConfig

def add_company_config():
    """
    Adiciona configurações fiscais de exemplo para o usuário professor@example.com
    """
    try:
        # Encontrar o usuário professor
        professor = User.objects.get(email='professor@example.com')
        
        # Criar ou atualizar as configurações fiscais
        company_config, created = CompanyConfig.objects.update_or_create(
            user=professor,
            defaults={
                'enabled': True,
                'cnpj': '12.345.678/0001-90',
                'razao_social': 'Instituto Educação Avançada Ltda',
                'nome_fantasia': 'Academia Conhecimento Contínuo',
                'inscricao_municipal': '123456789',
                'regime_tributario': 'simples_nacional',
                'endereco': 'Avenida Educadores',
                'numero': '555',
                'complemento': 'Sala 302',
                'bairro': 'Centro',
                'municipio': 'São Paulo',
                'uf': 'SP',
                'cep': '01234-567',
                'telefone': '(11) 98765-4321',
                'email': 'contato@institutoea.com.br'
            }
        )
        
        status = "criadas" if created else "atualizadas"
        print(f"✅ Configurações fiscais {status} com sucesso para {professor.email}!")
        
    except User.DoesNotExist:
        print("❌ Usuário professor@example.com não encontrado!")
    except Exception as e:
        print(f"❌ Erro ao configurar dados fiscais: {str(e)}")

if __name__ == "__main__":
    add_company_config()
