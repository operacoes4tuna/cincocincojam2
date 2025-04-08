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

def fix_event_times():
    """
    Verifica e corrige eventos com horários problemáticos.
    Ajusta eventos que:
    1. Terminam no dia seguinte ao início
    2. Têm duração muito longa (mais de 8 horas)
    """
    print("=== VERIFICANDO HORÁRIOS DOS EVENTOS ===")
    
    # Obter todos os eventos
    events = Event.objects.all().order_by('start_time')
    count = 0
    
    for event in events:
        # Mostrar horário atual do evento
        start_date = event.start_time.strftime('%d/%m/%Y')
        start_time = event.start_time.strftime('%H:%M')
        end_date = event.end_time.strftime('%d/%m/%Y')
        end_time = event.end_time.strftime('%H:%M')
        
        print(f"ID {event.id}: {event.title}")
        print(f"  Data/Hora atual: {start_date} {start_time} até {end_date} {end_time}")
        
        # Calcular a duração em horas
        duration_minutes = (event.end_time - event.start_time).total_seconds() / 60
        duration_hours = duration_minutes / 60
        
        issues = []
        
        # Verificar se o evento termina em um dia diferente
        if start_date != end_date:
            issues.append(f"termina em dia diferente ({round(duration_hours, 1)} horas)")
        
        # Verificar se a duração é muito longa
        if duration_hours > 8 and not event.all_day:
            issues.append(f"duração muito longa ({round(duration_hours, 1)} horas)")
        
        # Verificar se a duração é negativa (termina antes de começar)
        if duration_minutes < 0:
            issues.append(f"duração negativa ({round(duration_hours, 1)} horas)")
        
        if issues:
            old_start = event.start_time
            old_end = event.end_time
            
            print(f"  ⚠️ Problemas detectados: {', '.join(issues)}")
            print(f"  Corrigindo...")
            
            # Ajustar eventos com duração negativa
            if duration_minutes < 0:
                # Inverter início e fim
                event.start_time, event.end_time = event.end_time, event.start_time
            # Ajustar eventos muito longos ou que terminam no dia seguinte
            elif duration_hours > 8 or start_date != end_date:
                # Limitar a duração a 2 horas se for muito longa
                new_end = event.start_time + timedelta(hours=2)
                event.end_time = new_end
            
            # Salvar as alterações
            event.save()
            
            # Mostrar o resultado da correção
            new_start_date = event.start_time.strftime('%d/%m/%Y')
            new_start_time = event.start_time.strftime('%H:%M')
            new_end_date = event.end_time.strftime('%d/%m/%Y')
            new_end_time = event.end_time.strftime('%H:%M')
            
            print(f"  ✅ Corrigido para: {new_start_date} {new_start_time} até {new_end_date} {new_end_time}")
            count += 1
        else:
            print(f"  ✓ Horário OK")
        
        print("")
    
    print(f"\nTotal de eventos corrigidos: {count} de {events.count()}")
    print("\n=== CORREÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    fix_event_times() 