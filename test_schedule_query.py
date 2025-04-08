#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar as funções necessárias
from assistant.db_query import process_db_query
from django.utils import timezone
import pytz

def test_schedule_query():
    """
    Teste da função de consulta de agendamentos existentes.
    """
    print("=== TESTE DE CONSULTA DE AGENDAMENTOS ===")
    
    # Consulta original do usuário
    query = "olá! eu possuo alguma sessão marcada no estudio de ipanema na sexta feira?"
    print(f"Consulta: '{query}'")
    
    # Executar o processamento da consulta
    result = process_db_query(query)
    
    print("\nResultado da consulta:")
    content = result['content'] if isinstance(result, dict) and 'content' in result else result
    print(content)
    
    # Testar mais algumas variações da consulta
    variations = [
        "tenho alguma sessão agendada para sexta-feira?",
        "mostre minha agenda para o estúdio ipanema",
        "quais sessões tenho marcadas para esta semana?",
        "há alguma sessão no estúdio de Botafogo amanhã?"
    ]
    
    for i, variation in enumerate(variations, 1):
        print(f"\n--- Variação {i}: '{variation}' ---")
        result = process_db_query(variation)
        content = result['content'] if isinstance(result, dict) and 'content' in result else result
        # Imprimir apenas as primeiras linhas da resposta para não ficar muito extenso
        print('\n'.join(content.split('\n')[:10]) + '\n...')
    
    print("\n=== FIM DO TESTE ===")

if __name__ == "__main__":
    test_schedule_query() 