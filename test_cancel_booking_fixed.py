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

# Definir queries de teste focadas nos casos problemáticos
test_queries = [
    # Casos específicos que não funcionavam corretamente
    "desmarque a sessão do studio de 14h às 16h da barra do dia 09/04",
    "cancele todas as minhas sessões",
    "desmarque todas as sessões de estudio para mim",
    
    # Casos adicionais para teste
    "cancelar a aula do estúdio da barra na quarta às 17h",
    "remover todos os meus agendamentos do estúdio da barra",
    "cancele meus horários para amanhã"
]

def test_cancel_booking_fixed():
    """Testa a função cancel_studio_booking com os casos problemáticos específicos"""
    print("=== TESTE DE CANCELAMENTO DE SESSÕES (CORRIGIDO) ===\n")
    
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
    test_cancel_booking_fixed() 