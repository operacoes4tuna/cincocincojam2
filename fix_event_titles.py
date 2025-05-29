#!/usr/bin/env python
import os
import sys
import django
import re

# Configura o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Agora podemos importar os modelos necessários
from scheduler.models import Event

def fix_event_titles():
    """
    Corrige os títulos dos eventos existentes, removendo expressões inadequadas.
    """
    print("=== CORRIGINDO TÍTULOS DOS EVENTOS ===")
    
    # Lista de palavras e frases para filtrar do título
    filter_words = [
        'mim', 'me', 'eu', 'nos', 'nós', 'a gente', 'para mim', 'para nós', 
        'para essa', 'para esta', 'nessa', 'nesta', 'dessa', 'desta',
        'hoje', 'amanhã', 'depois', 'próxima', 'proxima', 'seguinte',
        'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo',
        'de manhã', 'à tarde', 'à noite', 'às', 'as', 'no dia', 'na data',
        'para', 'do', 'da', 'dos', 'das', 'no', 'na', 'nos', 'nas',
        'unidade', 'essa', 'este', 'esta', 'desse', 'deste', 'dessa', 'desta'
    ]
    
    # Tipos comuns de sessões como fallback
    session_types = {
        'gravação': 'Sessão de Gravação',
        'gravacao': 'Sessão de Gravação',
        'mixagem': 'Sessão de Mixagem',
        'masterização': 'Sessão de Masterização',
        'masterizacao': 'Sessão de Masterização',
        'violão': 'Aula de Violão',
        'guitarra': 'Aula de Guitarra',
        'bateria': 'Aula de Bateria',
        'piano': 'Aula de Piano',
        'canto': 'Aula de Canto',
        'ensaio': 'Ensaio',
        'produção': 'Sessão de Produção',
        'producao': 'Sessão de Produção',
        'reunião': 'Reunião',
        'aula': 'Aula'
    }
    
    # Obter todos os eventos
    events = Event.objects.all()
    count = 0
    
    for event in events:
        original_title = event.title
        
        # Verificar se o título atual contém palavras inadequadas
        needs_fix = any(word in original_title.lower() for word in filter_words)
        
        if needs_fix:
            # Título original para log
            print(f"ID {event.id}: '{original_title}' → ", end="")
            
            # Tentar limpar o título
            clean_title = original_title.lower()
            for word in filter_words:
                clean_title = re.sub(r'\b' + re.escape(word) + r'\b', '', clean_title)
            
            # Limpar múltiplos espaços e espaços no início/fim
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()
            clean_title = clean_title.capitalize()
            
            # Se ficou muito curto, buscar um tipo de sessão no título original
            if len(clean_title) < 3:
                # Tentar identificar o tipo de sessão no título ou descrição
                for keyword, session_type in session_types.items():
                    if keyword in original_title.lower() or (event.description and keyword in event.description.lower()):
                        clean_title = session_type
                        break
                
                # Se ainda não encontrou um tipo, usar padrão
                if len(clean_title) < 3:
                    clean_title = "Sessão de Estúdio"
            
            # Atualizar o título
            event.title = clean_title
            event.save()
            count += 1
            
            print(f"'{clean_title}'")
    
    print(f"\nTotal de eventos corrigidos: {count} de {events.count()}")
    print("\n=== CORREÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    fix_event_titles() 