#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar os modelos do Django
from django.utils import timezone
import pytz

def test_timezone_adjustment():
    """
    Teste para verificar o ajuste automático de horários passados para o dia seguinte.
    """
    print("=== TESTE DE AJUSTE PARA DIA SEGUINTE ===")
    
    # Instanciar diretamente o timezone local
    timezone_name = 'America/Sao_Paulo'
    timezone_obj = pytz.timezone(timezone_name)
    
    # Pegar horário atual local
    now_utc = timezone.now()
    now_local = now_utc.astimezone(timezone_obj)
    print(f"Horário atual (local): {now_local}")
    
    # Criar data/hora passada (2 horas atrás)
    past_datetime = now_local - timedelta(hours=2)
    print(f"Horário passado (2h atrás): {past_datetime}")
    
    # Verificar se o sistema detecta que já passou
    is_past = past_datetime < now_local
    print(f"Sistema detecta que já passou? {is_past}")
    
    # Simular o ajuste que a função faria
    tomorrow = (now_local + timedelta(days=1)).date()
    tomorrow_time = past_datetime.time()
    tomorrow_naive = datetime.combine(tomorrow, tomorrow_time)
    adjusted_datetime = timezone.make_aware(tomorrow_naive, timezone=timezone_obj)
    
    print(f"Horário ajustado para amanhã: {adjusted_datetime}")
    print(f"Está no futuro? {adjusted_datetime > now_local}")
    
    # Verificar se o ajuste funciona com diferentes timezones
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    now_tokyo = now_utc.astimezone(tokyo_tz)
    print(f"\nHorário atual em Tokyo: {now_tokyo}")
    
    # Criar data/hora passada em Tokyo
    past_tokyo = now_tokyo - timedelta(hours=2)
    print(f"Horário passado em Tokyo (2h atrás): {past_tokyo}")
    
    # Converter ambos para America/Sao_Paulo para comparação
    past_sp = past_tokyo.astimezone(timezone_obj)
    print(f"Horário passado convertido para São Paulo: {past_sp}")
    
    # Verificar se o sistema detecta que já passou
    is_past_sp = past_sp < now_local
    print(f"Sistema detecta que já passou? {is_past_sp}")
    
    print("\n=== FIM DO TESTE ===")

if __name__ == "__main__":
    test_timezone_adjustment() 