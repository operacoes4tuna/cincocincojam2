#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar os modelos de Django
from assistant.db_query import create_studio_booking
from django.utils import timezone

def test_booking():
    """
    Testa o agendamento de estúdio com diferentes cenários
    para verificar a manipulação de timezone e comparações de datetime
    """
    print("=== TESTE DE AGENDAMENTO DE ESTÚDIO ===")
    
    # Cenário 1: Agendamento para hoje
    query1 = "Quero agendar uma sessão de gravação no estúdio Barra hoje às 15h"
    result1 = create_studio_booking(query1)
    print("\n--- Cenário 1: Agendamento para hoje ---")
    print(f"Query: {query1}")
    print(f"Resultado: {result1['content'] if isinstance(result1, dict) and 'content' in result1 else result1}")
    
    # Cenário 2: Agendamento para amanhã
    tomorrow = (timezone.now() + timedelta(days=1)).strftime('%d/%m/%Y')
    query2 = f"Agendar aula de violão no estúdio Centro para {tomorrow} às 10h"
    result2 = create_studio_booking(query2)
    print("\n--- Cenário 2: Agendamento para amanhã ---")
    print(f"Query: {query2}")
    print(f"Resultado: {result2['content'] if isinstance(result2, dict) and 'content' in result2 else result2}")
    
    # Cenário 3: Agendamento para um horário que já passou hoje
    now = timezone.now()
    # Usar um horário fixo que sabemos que já passou (2:00 da manhã)
    query3 = f"Agendar ensaio no estúdio Ipanema hoje às 02:00"
    result3 = create_studio_booking(query3)
    print("\n--- Cenário 3: Agendamento para horário que já passou hoje (2:00) ---")
    print(f"Query: {query3}")
    print(f"Resultado: {result3['content'] if isinstance(result3, dict) and 'content' in result3 else result3}")
    
    print("\n=== FIM DOS TESTES ===")

if __name__ == "__main__":
    test_booking() 