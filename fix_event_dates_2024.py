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

def fix_event_dates_to_2024():
    """
    Ajusta todos os eventos com ano 2025 para o ano atual (2024).
    """
    print("=== AJUSTANDO DATAS DOS EVENTOS PARA 2024 ===")
    
    # Obter todos os eventos
    events = Event.objects.all().order_by('start_time')
    count = 0
    
    # Data de hoje para comparação
    today = timezone.now().date()
    current_year = 2024  # Fixando em 2024
    
    for event in events:
        # Mostrar data atual do evento
        start_date = event.start_time.strftime('%d/%m/%Y')
        start_time = event.start_time.strftime('%H:%M')
        end_time = event.end_time.strftime('%H:%M')
        
        print(f"ID {event.id}: {event.title}")
        print(f"  Data atual: {start_date}, {start_time} às {end_time}")
        
        # Verificar se o evento está em 2025
        if event.start_time.year == 2025:
            # Ajustar para 2024
            old_start = event.start_time
            old_end = event.end_time
            
            # Criar nova data mantendo mês, dia e hora, mas ajustando o ano para 2024
            new_start = old_start.replace(year=current_year)
            
            # Calcular a nova data de término mantendo a mesma duração
            duration = old_end - old_start
            new_end = new_start + duration
            
            # Atualizar o evento
            event.start_time = new_start
            event.end_time = new_end
            event.save()
            
            # Mostrar a correção
            new_start_date = new_start.strftime('%d/%m/%Y')
            new_start_time = new_start.strftime('%H:%M')
            new_end_time = new_end.strftime('%H:%M')
            
            print(f"  ✅ Corrigido para: {new_start_date}, {new_start_time} às {new_end_time}")
            count += 1
        else:
            print(f"  ✓ Data já está em {current_year}")
        
        print("")
    
    print(f"\nTotal de eventos corrigidos: {count} de {events.count()}")
    print("\n=== AJUSTE CONCLUÍDO ===")

if __name__ == "__main__":
    fix_event_dates_to_2024() 