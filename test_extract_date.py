#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar as funções necessárias
from assistant.db_query import extract_date_time, extract_studio, extract_duration
from django.utils import timezone
import pytz

def test_extract_functions():
    """
    Teste das funções de extração para verificar o processamento da consulta.
    """
    print("=== TESTE DE EXTRAÇÃO DE INFORMAÇÕES DA CONSULTA ===")
    
    # Consulta original do usuário
    query = "marque para mim uma sessão no estudio ipanema sexta de 13h às 14h"
    print(f"Consulta: '{query}'")
    
    # Testar extração de data/hora
    date_time_info = extract_date_time(query)
    if date_time_info:
        date_time, timezone_name = date_time_info
        print(f"\nData/hora extraída: {date_time}")
        print(f"Timezone: {timezone_name}")
        
        # Verificar dia da semana
        weekday = date_time.weekday()
        weekday_names = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        print(f"Dia da semana: {weekday_names[weekday]} (índice {weekday})")
        
        # Verificar se é realmente sexta-feira
        is_friday = weekday == 4  # 4 = sexta-feira
        print(f"É sexta-feira? {is_friday}")
    else:
        print("\nNão foi possível extrair data/hora da consulta")
    
    # Testar extração de estúdio
    studio_info = extract_studio(query)
    if studio_info:
        studio, studio_id = studio_info
        print(f"\nEstúdio extraído: {studio.name} (ID: {studio_id})")
    else:
        print("\nNão foi possível extrair o estúdio da consulta")
    
    # Testar extração de duração
    duration = extract_duration(query)
    print(f"\nDuração extraída: {duration} minutos")
    
    # Testar a consulta modificada (especificando 'próxima sexta')
    print("\n=== TESTE COM 'PRÓXIMA SEXTA' ===")
    modified_query = "marque para mim uma sessão no estudio ipanema próxima sexta de 13h às 14h"
    print(f"Consulta modificada: '{modified_query}'")
    
    # Testar extração de data/hora com a consulta modificada
    date_time_info = extract_date_time(modified_query)
    if date_time_info:
        date_time, timezone_name = date_time_info
        print(f"\nData/hora extraída: {date_time}")
        print(f"Timezone: {timezone_name}")
        
        # Verificar dia da semana
        weekday = date_time.weekday()
        weekday_names = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        print(f"Dia da semana: {weekday_names[weekday]} (índice {weekday})")
        
        # Verificar se é realmente sexta-feira
        is_friday = weekday == 4  # 4 = sexta-feira
        print(f"É sexta-feira? {is_friday}")
    else:
        print("\nNão foi possível extrair data/hora da consulta modificada")
    
    print("\n=== FIM DO TESTE ===")

if __name__ == "__main__":
    test_extract_functions() 