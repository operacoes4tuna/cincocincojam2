#!/usr/bin/env python
import os
import sys
import django
import pytz
from datetime import datetime, timedelta

# Configurar ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Importar os modelos necessários
from scheduler.models import Event, EventLocation
from core.models import User
from django.utils import timezone

def add_test_events():
    """
    Adiciona eventos de teste para validar as funcionalidades de cancelamento.
    """
    print("=== ADICIONANDO EVENTOS DE TESTE ===")
    
    # Restaurar eventos existentes para status SCHEDULED
    restored = Event.objects.filter(status='CANCELLED').update(status='SCHEDULED')
    print(f"✅ Restaurados {restored} eventos cancelados para status SCHEDULED")
    
    # Obter estúdios
    barra_studio = EventLocation.objects.filter(name__icontains='Barra').first()
    ipanema_studio = EventLocation.objects.filter(name__icontains='Ipanema').first()
    botafogo_studio = EventLocation.objects.filter(name__icontains='Botafogo').first()
    
    # Obter professor para associar aos eventos
    professor = User.objects.filter(user_type='PROFESSOR').first()
    
    if not professor:
        print("Erro: Nenhum professor encontrado no sistema")
        return
        
    if not barra_studio or not ipanema_studio:
        print("Erro: Estúdios necessários não encontrados")
        return
    
    # Adicionar novos eventos com horários específicos para testes
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)
    
    # Função auxiliar para criar evento
    def create_event(title, start_day, start_hour, duration_minutes, studio, status='SCHEDULED'):
        # Criar data/hora de início
        start_datetime = datetime.combine(
            start_day, 
            datetime.min.time().replace(hour=start_hour)
        )
        start_datetime = timezone.make_aware(start_datetime, timezone=pytz.timezone('America/Sao_Paulo'))
        
        # Calcular hora de término
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        
        # Criar o evento
        event = Event(
            title=title,
            start_time=start_datetime,
            end_time=end_datetime,
            location=studio,
            event_type='CLASS',
            status=status,
            professor=professor
        )
        event.save()
        
        print(f"Criado: {title} - {start_datetime.strftime('%d/%m/%Y %H:%M')} às {end_datetime.strftime('%H:%M')} - {studio.name}")
        return event
    
    # Criar eventos para testar diferentes cenários
    create_event("Aula de Violão", tomorrow, 14, 120, barra_studio)
    create_event("Workshop de Piano", tomorrow, 17, 120, ipanema_studio)
    create_event("Sessão de Mixagem", tomorrow, 14, 120, ipanema_studio)
    
    # Criar eventos para casos específicos mencionados pelo usuário
    next_wednesday = today + timedelta(days=(9 - today.weekday()) % 7)  # Próxima quarta
    next_friday = today + timedelta(days=(11 - today.weekday()) % 7)    # Próxima sexta
    
    create_event("Ensaio de Banda", next_wednesday, 17, 120, barra_studio)
    create_event("Gravação de Podcast", next_friday, 14, 120, barra_studio)
    
    print("\n=== ADIÇÃO DE EVENTOS CONCLUÍDA ===")

if __name__ == "__main__":
    add_test_events() 