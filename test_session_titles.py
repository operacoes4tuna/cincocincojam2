#!/usr/bin/env python
import os
import sys
import django

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar as funções necessárias
from assistant.db_query import extract_session_title

def test_session_titles():
    """
    Testa a extração de títulos de sessão de várias consultas,
    verificando se os títulos problemáticos são corrigidos.
    """
    print("=== TESTE DE EXTRAÇÃO DE TÍTULOS DE SESSÃO ===")
    
    test_queries = [
        # Caso problemático similar ao reportado
        "marque para mim uma sessão no estudio ipanema sexta de 13h às 14h",
        # Outros casos que poderiam ser problemáticos
        "quero agendar para mim uma aula de violão na unidade botafogo amanhã de manhã",
        "preciso reservar o estúdio barra para ensaio com a minha banda na sexta às 19h",
        "marcar para essa sexta uma sessão de gravação no estúdio centro",
        "agendar estúdio para mixagem do meu projeto na próxima terça",
        "reservar aula de canto para mim no dia 15/05",
        # Casos mais bem formatados para comparação
        "aula de violão com professor João",
        "sessão de gravação para o álbum novo",
        "ensaio da banda Os Incríveis",
        "masterização do single 'Canção de Verão'"
    ]
    
    for i, query in enumerate(test_queries, 1):
        title = extract_session_title(query)
        print(f"\nConsulta {i}: '{query}'")
        print(f"Título extraído: '{title}'")
    
    print("\n=== FIM DO TESTE ===")

if __name__ == "__main__":
    test_session_titles() 