#!/usr/bin/env python
import os
import sys
import django

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar os modelos necessários
from scheduler.models import Event

def check_last_booking():
    """
    Verifica os detalhes do último agendamento criado.
    """
    print("=== VERIFICANDO ÚLTIMO AGENDAMENTO ===")
    
    # Obter o último evento criado ordenado por ID
    last_event = Event.objects.order_by('-id').first()
    
    if last_event:
        print(f"ID: {last_event.id}")
        print(f"Título: '{last_event.title}'")
        print(f"Data/Hora Início: {last_event.start_time}")
        print(f"Data/Hora Fim: {last_event.end_time}")
        print(f"Estúdio: {last_event.location.name if last_event.location else 'Não especificado'}")
        print(f"Professor: {last_event.professor.first_name} {last_event.professor.last_name if last_event.professor else 'Não especificado'}")
        print(f"Status: {last_event.status}")
        print(f"Descrição: {last_event.description}")
    else:
        print("Nenhum evento encontrado no banco de dados.")
    
    print("\n=== FIM DA VERIFICAÇÃO ===")

if __name__ == "__main__":
    check_last_booking() 