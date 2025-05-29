#!/usr/bin/env python
"""
Script para testar a funcionalidade de agendamento de estúdio
diretamente, sem passar pela API web.
"""
import os
import sys
import django

# Configurar o ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Importações do projeto
from assistant.db_query import create_studio_booking, extract_date_time, extract_studio

def test_booking():
    """Testar funções de extração e agendamento."""
    # Teste 1: Extração de data e hora
    query = "marcar uma aula de violão no estúdio barra amanhã às 14h"
    print("\n=== Teste de extração de data/hora ===")
    date_time_info = extract_date_time(query)
    if date_time_info:
        dt, tz = date_time_info
        print(f"Data/Hora: {dt.strftime('%d/%m/%Y %H:%M')}")
        print(f"Timezone: {tz}")
    else:
        print("Falha ao extrair data/hora")
    
    # Teste 2: Extração de estúdio
    print("\n=== Teste de extração de estúdio ===")
    from scheduler.models import EventLocation
    # Criar um estúdio de teste se não existir
    if not EventLocation.objects.filter(name__icontains="barra").exists():
        print("Criando estúdio de teste...")
        EventLocation.objects.create(
            name="Estúdio Barra",
            address="Av. das Américas, 500, Barra da Tijuca",
            is_active=True
        )
        print("Estúdio de teste criado.")
    
    studio_info = extract_studio(query)
    if studio_info:
        studio, studio_id = studio_info
        print(f"Estúdio: {studio.name} (ID: {studio_id})")
    else:
        print("Falha ao extrair estúdio")
    
    # Teste 3: Processamento de agendamento completo
    print("\n=== Teste de agendamento completo ===")
    from core.models import User
    # Criar um professor de teste se não existir
    if not User.objects.filter(user_type="PROFESSOR").exists():
        print("Criando professor de teste...")
        User.objects.create(
            email="professor@teste.com",
            username="professor_teste",
            first_name="Professor",
            last_name="Teste",
            user_type="PROFESSOR",
            is_active=True
        )
        print("Professor de teste criado.")
    
    result = create_studio_booking(query)
    print("Resultado:")
    print(type(result))
    if isinstance(result, dict):
        for key, value in result.items():
            print(f"{key}: {value}")
    else:
        print(result)

if __name__ == "__main__":
    test_booking() 