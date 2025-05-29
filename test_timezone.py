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

def test_timezone_handling():
    """
    Teste para verificar a manipulação de timezone em diferentes cenários.
    """
    print("=== TESTE DE MANIPULAÇÃO DE TIMEZONE ===")
    
    # 1. Timezone padrão do Django
    print(f"\n1. Timezone padrão do Django:")
    default_tz = timezone.get_default_timezone()
    print(f"   Default timezone: {default_tz}")
    
    # 2. Timezone atual
    print(f"\n2. Data/hora atual:")
    now = timezone.now()
    print(f"   timezone.now(): {now}")
    print(f"   Timezone: {now.tzinfo}")
    
    # 3. Criando datetime com timezone (America/Sao_Paulo)
    print(f"\n3. Datetime com timezone (America/Sao_Paulo):")
    sp_tz = pytz.timezone('America/Sao_Paulo')
    naive_dt = datetime(2025, 4, 8, 15, 0, 0)  # 15:00
    
    # Método 1: usando localize
    aware_dt1 = sp_tz.localize(naive_dt)
    print(f"   Método 1 (localize): {aware_dt1}")
    print(f"   Timezone: {aware_dt1.tzinfo}")
    
    # Método 2: usando make_aware
    aware_dt2 = timezone.make_aware(naive_dt, timezone=sp_tz)
    print(f"   Método 2 (make_aware): {aware_dt2}")
    print(f"   Timezone: {aware_dt2.tzinfo}")
    
    # 4. Convertendo para UTC
    print(f"\n4. Convertendo para UTC:")
    utc_dt1 = aware_dt1.astimezone(pytz.UTC)
    print(f"   Método 1 (localize) em UTC: {utc_dt1}")
    
    utc_dt2 = aware_dt2.astimezone(pytz.UTC)
    print(f"   Método 2 (make_aware) em UTC: {utc_dt2}")
    
    # 5. Comparando datetimes
    print(f"\n5. Comparando datetimes:")
    now_utc = now.astimezone(pytz.UTC)
    print(f"   now em UTC: {now_utc}")
    print(f"   utc_dt1 < now_utc: {utc_dt1 < now_utc}")
    print(f"   utc_dt2 < now_utc: {utc_dt2 < now_utc}")
    
    # 6. Teste com horário no passado
    print(f"\n6. Teste com horário no passado:")
    past_hour = (now - timedelta(hours=1)).time()
    naive_past = datetime.combine(datetime.now().date(), past_hour)
    
    # Tornando aware
    past_aware1 = sp_tz.localize(naive_past)
    past_aware2 = timezone.make_aware(naive_past, timezone=sp_tz)
    
    # Convertendo para UTC
    past_utc1 = past_aware1.astimezone(pytz.UTC)
    past_utc2 = past_aware2.astimezone(pytz.UTC)
    
    print(f"   Horário passado: {past_hour}")
    print(f"   past_aware1: {past_aware1}")
    print(f"   past_aware2: {past_aware2}")
    print(f"   past_utc1: {past_utc1}")
    print(f"   past_utc2: {past_utc2}")
    print(f"   past_utc1 < now_utc: {past_utc1 < now_utc}")
    print(f"   past_utc2 < now_utc: {past_utc2 < now_utc}")
    
    # 7. Testar conversão de datetime-aware para mesmo timezone antes de comparar
    print(f"\n7. Conversão para mesmo timezone antes de comparar:")
    # Criar um datetime com timezone diferente
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    tokyo_dt = tokyo_tz.localize(datetime.now())
    
    # Converter para UTC antes de comparar
    tokyo_utc = tokyo_dt.astimezone(pytz.UTC)
    
    print(f"   Tokyo datetime: {tokyo_dt}")
    print(f"   Tokyo em UTC: {tokyo_utc}")
    print(f"   now em UTC: {now_utc}")
    print(f"   tokyo_dt < now: {tokyo_dt < now}")  # Comparação direta (pode ser inconsistente)
    print(f"   tokyo_utc < now_utc: {tokyo_utc < now_utc}")  # Comparação após converter para mesmo timezone
    
    print("\n=== FIM DOS TESTES ===")

if __name__ == "__main__":
    test_timezone_handling() 