#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar as funções necessárias
from assistant.db_query import create_studio_booking
from django.utils import timezone
import pytz

def test_booking_query():
    """
    Teste da função create_studio_booking com a consulta específica do usuário.
    """
    print("=== TESTE DE AGENDAMENTO COM CONSULTA ESPECÍFICA ===")
    
    # Consulta original do usuário
    query = "marque para mim uma sessão no estudio ipanema sexta de 13h às 14h"
    print(f"Consulta: '{query}'")
    
    # Executar a função de agendamento
    result = create_studio_booking(query)
    
    print("\nResultado do agendamento:")
    content = result['content'] if isinstance(result, dict) and 'content' in result else result
    print(content)
    
    print("\n=== FIM DO TESTE ===")

if __name__ == "__main__":
    test_booking_query() 