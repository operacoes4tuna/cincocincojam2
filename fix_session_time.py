#!/usr/bin/env python
import os
import sys
import django
import pytz
from datetime import datetime, timedelta

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar os modelos necessários
from scheduler.models import Event
from django.utils import timezone

def fix_specific_event():
    """
    Corrige o horário do evento "Barra de 21h" para começar às 21:00 em vez de 00:00.
    """
    print("=== CORRIGINDO EVENTO ESPECÍFICO ===")
    
    try:
        # Buscar o evento pelo ID
        event = Event.objects.get(id=9)
        
        # Mostrar o horário atual
        start_date = event.start_time.strftime('%d/%m/%Y')
        start_time = event.start_time.strftime('%H:%M')
        end_date = event.end_time.strftime('%d/%m/%Y')
        end_time = event.end_time.strftime('%H:%M')
        
        print(f"Evento encontrado: ID {event.id} - {event.title}")
        print(f"Horário atual: {start_date} {start_time} até {end_date} {end_time}")
        
        # Calcular a duração original
        duration = event.end_time - event.start_time
        
        # Verificar se o título contém "21h" e o evento não começa às 21h
        if "21h" in event.title and event.start_time.hour != 21:
            # Obter a data do evento atual
            current_date = event.start_time.date()
            
            # Criar nova data/hora de início às 21:00
            tz = pytz.timezone('America/Sao_Paulo')
            new_start = datetime(
                year=current_date.year,
                month=current_date.month,
                day=current_date.day,
                hour=21,
                minute=0,
                second=0
            )
            new_start = timezone.make_aware(new_start, timezone=tz)
            
            # Definir novo término mantendo a mesma duração
            new_end = new_start + duration
            
            # Salvar o horário antigo para referência
            old_start = event.start_time
            old_end = event.end_time
            
            # Atualizar o evento
            event.start_time = new_start
            event.end_time = new_end
            event.save()
            
            # Mostrar o resultado
            new_start_date = new_start.strftime('%d/%m/%Y')
            new_start_time = new_start.strftime('%H:%M')
            new_end_date = new_end.strftime('%d/%m/%Y')
            new_end_time = new_end.strftime('%H:%M')
            
            print(f"✅ Evento corrigido: {new_start_date} {new_start_time} até {new_end_date} {new_end_time}")
            print("Evento atualizado com sucesso!")
        else:
            print(f"O evento não precisa de correção ou não contém '21h' no título.")
        
    except Event.DoesNotExist:
        print(f"Evento com ID 9 não encontrado.")
    except Exception as e:
        print(f"Erro ao corrigir o evento: {str(e)}")
    
    print("\n=== CORREÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    fix_specific_event() 