#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta

# Configurar ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Importar a função a ser testada
from assistant.db_query import cancel_studio_booking

# Definir queries de teste
test_queries = [
    "Cancele todas as minhas sessões",
    "Desmarque minha sessão de 13h no estúdio de ipanema",
    "Cancele meus agendamentos de sexta",
    "Remover minha aula de violão amanhã",
    "Anule a sessão de gravação de amanhã às 10h",
    "Exclua o ensaio da banda na barra",
    "Desmarque a sessão das 18h"
]

def test_cancel_booking():
    """Testa a função cancel_studio_booking com diferentes tipos de consultas"""
    print("=== TESTE DE CANCELAMENTO DE SESSÕES ===\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"Teste #{i}: '{query}'")
        print("-" * 50)
        
        try:
            # Chamar a função e obter o resultado
            result = cancel_studio_booking(query)
            
            # Exibir o resultado
            if isinstance(result, dict):
                print(f"Tipo de resposta: {result.get('response_type', 'unknown')}")
                print(f"Conteúdo: {result.get('content', 'Nenhum conteúdo')}")
            else:
                print(f"Resultado: {result}")
        except Exception as e:
            print(f"ERRO: {str(e)}")
        
        print("\n")
    
    print("=== TESTES CONCLUÍDOS ===")

if __name__ == "__main__":
    test_cancel_booking() 