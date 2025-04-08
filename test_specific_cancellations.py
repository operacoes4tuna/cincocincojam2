#!/usr/bin/env python
import os
import sys
import django

# Configurar ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Importar a função a ser testada
from assistant.db_query import cancel_studio_booking

def test_specific_case(query):
    """Testa um caso específico e exibe o resultado detalhado"""
    print(f"TESTANDO: '{query}'")
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
    
    print("\n" + "=" * 50 + "\n")

# Testar casos específicos um por um
if __name__ == "__main__":
    # Teste de cancelamento por horário específico
    test_specific_case("cancelar a sessão das 14h às 16h no estúdio da barra")
    
    # Teste de cancelamento por estúdio específico
    test_specific_case("desmarque todas as sessões do estúdio da barra")
    
    # Teste de cancelamento por dia da semana
    test_specific_case("cancele as sessões de quarta-feira")
    
    # Teste de solicitação mais específica
    test_specific_case("cancelar a aula do estúdio da barra na quarta às 17h") 