from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.base import ContentFile
import os
import base64

User = get_user_model()

class Command(BaseCommand):
    help = 'Cria usuários padrão do sistema com perfis completos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Atualiza os usuários mesmo se eles já existirem',
        )

    def handle(self, *args, **kwargs):
        force_update = kwargs.get('force_update', False)
        
        # Lista de usuários padrão com perfis mais completos
        default_users = [
            # Administrador
            {
                'email': 'admin@55jam.com',
                'password': '123123',
                'first_name': 'Admin',
                'last_name': 'Sistema',
                'user_type': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'bio': 'Administrador principal do sistema CincoCincoJAM 2.0.',
            },
            
            # Professor
            {
                'email': 'professor@55jam.com',
                'password': '123123',
                'first_name': 'Professor',
                'last_name': 'Exemplo',
                'user_type': 'PROFESSOR',
                'bio': 'Professor com experiência em programação web e desenvolvimento de sistemas.',
            },
            
            # Aluno
            {
                'email': 'aluno@55jam.com',
                'password': '123123',
                'first_name': 'Aluno',
                'last_name': 'Teste',
                'user_type': 'STUDENT',
                'bio': 'Estudante de tecnologia interessado em desenvolvimento web e inteligência artificial.',
            },
        ]

        # Contar usuários criados/atualizados
        created_count = 0
        updated_count = 0
        skipped_count = 0

        # Criar ou atualizar cada usuário
        for user_data in default_users:
            email = user_data.pop('email')
            password = user_data.pop('password')
            
            user_exists = User.objects.filter(email=email).exists()
            
            if not user_exists:
                # Criar novo usuário
                user = User.objects.create_user(email=email, password=password, **user_data)
                self.stdout.write(self.style.SUCCESS(f'Usuário criado: {email} ({user_data.get("user_type")})'))
                created_count += 1
            elif force_update:
                # Atualizar usuário existente
                user = User.objects.get(email=email)
                for key, value in user_data.items():
                    setattr(user, key, value)
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.WARNING(f'Usuário atualizado: {email} ({user_data.get("user_type")})'))
                updated_count += 1
            else:
                self.stdout.write(self.style.WARNING(f'Usuário ignorado (já existe): {email}'))
                skipped_count += 1

        # Resumo final
        self.stdout.write("\n=== Resumo da Operação ===")
        self.stdout.write(f"Usuários criados: {created_count}")
        self.stdout.write(f"Usuários atualizados: {updated_count}")
        self.stdout.write(f"Usuários ignorados: {skipped_count}")
        self.stdout.write(f"Total de usuários processados: {len(default_users)}")
        self.stdout.write("\nUse --force-update para atualizar usuários existentes")
        
        # Informações de acesso
        self.stdout.write("\n=== Informações de Acesso ===")
        self.stdout.write(f"{'Email':<30} {'Senha':<10} {'Tipo':<15}")
        self.stdout.write("-" * 55)
        self.stdout.write(f"{'admin@55jam.com':<30} {'123123':<10} {'Admin':<15}")
        self.stdout.write(f"{'professor@55jam.com':<30} {'123123':<10} {'Professor':<15}")
        self.stdout.write(f"{'aluno@55jam.com':<30} {'123123':<10} {'Aluno':<15}")
