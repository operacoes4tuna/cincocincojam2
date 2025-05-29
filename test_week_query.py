#!/usr/bin/env python
import os
import sys
import django

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar as funções necessárias
from assistant.db_query import process_db_query, get_schedule_info

def test_week_query():
    """
    Teste específico para consulta de sessões da semana.
    """
    print("=== TESTE DE CONSULTA DE SESSÕES DA SEMANA ===")
    
    # Consulta problemática
    query = "quais sessões tenho marcadas para esta semana?"
    print(f"Consulta: '{query}'")
    
    # Testar processamento direto pela função process_db_query
    print("\n--- Resultado via process_db_query ---")
    result = process_db_query(query)
    content = result['content'] if isinstance(result, dict) and 'content' in result else result
    print(content)
    
    # Testar chamando a função get_schedule_info diretamente
    print("\n--- Resultado via get_schedule_info ---")
    result = get_schedule_info(query + " esta semana")  # Adicionando explicitamente o contexto
    print(result)
    
    print("\n=== FIM DO TESTE ===")

if __name__ == "__main__":
    test_week_query() 