#!/usr/bin/env python
import os
import sys
import django

# Configurar ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Importar a função a ser testada
from assistant.db_query import cancel_studio_booking
from scheduler.models import Event, EventLocation

# Listar eventos correspondentes para depuração
def list_matching_events():
    """Lista eventos que deveriam corresponder aos critérios de busca"""
    print("=== EVENTOS QUE DEVERIAM CORRESPONDER AOS CRITÉRIOS ===")
    
    barra_studio = EventLocation.objects.filter(name__icontains='Barra').first()
    
    if not barra_studio:
        print("Erro: Estúdio da Barra não encontrado")
        return
    
    # Encontrar eventos das 14h às 16h na Barra
    matching_events = Event.objects.filter(
        location=barra_studio,
        start_time__hour=14,
        status__in=['SCHEDULED', 'CONFIRMED']
    )
    
    if not matching_events.exists():
        print("Nenhum evento encontrado com os critérios")
    else:
        for event in matching_events:
            print(f"ID {event.id} - {event.title} - {event.start_time.strftime('%d/%m/%Y %H:%M')} às {event.end_time.strftime('%H:%M')} - {event.location.name}")
    
    print("=" * 50)

# Testar a consulta específica
def test_specific_query():
    """Testa o cancelamento de sessões no estúdio da Barra das 14h às 16h"""
    query = "desmarque a sessão do studio de 14h às 16h da barra do dia 09/04"
    
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

if __name__ == "__main__":
    # Listar eventos para depuração
    list_matching_events()
    
    # Testar a consulta específica
    test_specific_query() 