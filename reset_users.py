#!/usr/bin/env python
"""
Script para redefinir as senhas dos usuários padrão do sistema.
Útil para corrigir problemas de acesso após o deploy.
"""
import os
import django

# Configurar ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

def reset_user_passwords():
    """
    Redefine as senhas dos usuários padrão do sistema para '123123'.
    """
    User = get_user_model()
    default_users = [
        'admin@55jam.com',
        'professor@55jam.com',
        'aluno@55jam.com'
    ]
    
    print("Redefinindo senhas dos usuários padrão...")
    
    for email in default_users:
        try:
            user = User.objects.get(email=email)
            user.set_password('123123')
            user.save()
            print(f"✅ Senha do usuário {email} redefinida com sucesso")
        except User.DoesNotExist:
            print(f"❌ Usuário {email} não encontrado")
    
    print("\nInformações de acesso:")
    print("-" * 40)
    print("| Email                | Senha  | Tipo       |")
    print("-" * 40)
    print("| admin@55jam.com     | 123123 | Admin      |")
    print("| professor@55jam.com | 123123 | Professor  |")
    print("| aluno@55jam.com     | 123123 | Aluno      |")
    print("-" * 40)
    
    # Verificar se os usuários existem e têm as senhas definidas
    for email in default_users:
        try:
            user = User.objects.get(email=email)
            print(f"Verificação do usuário {email}: {user.user_type} (ID: {user.id})")
        except User.DoesNotExist:
            print(f"Usuário {email} não existe no sistema")


if __name__ == "__main__":
    reset_user_passwords() 