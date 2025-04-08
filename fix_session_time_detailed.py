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
from django.db import connection

def fix_specific_event_detailed():
    """
    Corrige o horário do evento "Barra de 21h" com informações detalhadas.
    """
    print("=== CORREÇÃO DETALHADA DE EVENTO ===")
    
    try:
        # Buscar o evento pelo ID
        event = Event.objects.get(id=9)
        
        # Mostrar informações detalhadas
        print(f"Evento encontrado: ID {event.id} - {event.title}")
        print(f"Timezone do sistema: {timezone.get_current_timezone_name()}")
        print(f"Start time (raw): {event.start_time}")
        print(f"End time (raw): {event.end_time}")
        print(f"Start time timezone: {event.start_time.tzinfo}")
        print(f"Formato de data/hora: {event.start_time.strftime('%d/%m/%Y %H:%M:%S %Z%z')}")
        
        # Atualizar para 21:00 no dia anterior
        # (já que ele parece mostrar como meia-noite do dia seguinte mesmo após atualização)
        current_date = event.start_time.date()
        previous_day = current_date - timedelta(days=1)
        
        # Criar nova data/hora de início às 21:00 no dia anterior
        tz = timezone.get_current_timezone()
        new_start = datetime(
            year=previous_day.year,
            month=previous_day.month,
            day=previous_day.day,
            hour=21,
            minute=0,
            second=0
        )
        new_start = timezone.make_aware(new_start, timezone=tz)
        
        # Calcular duração atual
        duration = event.end_time - event.start_time
        duration_hours = duration.total_seconds() / 3600
        print(f"Duração atual: {duration_hours:.2f} horas")
        
        # Definir nova data de término
        new_end = new_start + duration
        
        print("\nAtualizando evento...")
        print(f"Novo início: {new_start.strftime('%d/%m/%Y %H:%M:%S %Z%z')}")
        print(f"Novo término: {new_end.strftime('%d/%m/%Y %H:%M:%S %Z%z')}")
        
        # Atualizar o evento diretamente com SQL para garantir
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE scheduler_event SET start_time = %s, end_time = %s WHERE id = %s",
                [new_start, new_end, event.id]
            )
            print(f"Registros atualizados: {cursor.rowcount}")
        
        # Recarregar o objeto do banco
        event.refresh_from_db()
        
        # Verificar se a atualização foi bem-sucedida
        print("\nVerificando atualização...")
        print(f"Start time atualizado: {event.start_time}")
        print(f"Formatado: {event.start_time.strftime('%d/%m/%Y %H:%M:%S %Z%z')}")
        print(f"End time atualizado: {event.end_time}")
        print(f"Formatado: {event.end_time.strftime('%d/%m/%Y %H:%M:%S %Z%z')}")
        
        print("\n✅ Evento atualizado com sucesso!")
        
    except Event.DoesNotExist:
        print(f"Evento com ID 9 não encontrado.")
    except Exception as e:
        print(f"Erro ao corrigir o evento: {str(e)}")
    
    print("\n=== CORREÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    fix_specific_event_detailed() 