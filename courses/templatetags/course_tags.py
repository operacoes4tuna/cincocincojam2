from django import template
import re
from urllib.parse import urlparse, parse_qs
from django.utils.safestring import mark_safe
from django.utils.text import slugify

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Permite acessar um item de um dicionário utilizando uma variável como chave.
    Usado em course_learn.html para acessar o progresso de cada aula.
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def get_youtube_id(url):
    """
    Extrai o ID de um vídeo do YouTube a partir da URL.
    Suporta formatos de URL completos e encurtados.
    """
    if not url:
        return None
        
    # Pattern para URLs completas do YouTube
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    
    youtube_match = re.match(youtube_regex, url)
    if youtube_match:
        return youtube_match.group(6)
    
    # Se não der match, tenta com urlparse para URLs do tipo youtu.be
    parsed_url = urlparse(url)
    if 'youtu.be' in parsed_url.netloc:
        return parsed_url.path.lstrip('/')
    
    # Para URLs do formato youtube.com/watch?v=ID
    if 'youtube.com' in parsed_url.netloc:
        query = parse_qs(parsed_url.query)
        if 'v' in query:
            return query['v'][0]
            
    return None

@register.filter
def get_next(items, current_item):
    """
    Retorna o próximo item de uma lista após o item atual.
    Usado para navegar entre aulas no course_learn.html.
    """
    try:
        current_index = list(items).index(current_item)
        if current_index < len(items) - 1:
            return items[current_index + 1]
    except (ValueError, IndexError):
        pass
    return None

@register.filter
def get_previous(items, current_item):
    """
    Retorna o item anterior de uma lista antes do item atual.
    Usado para navegar entre aulas no course_learn.html.
    """
    try:
        current_index = list(items).index(current_item)
        if current_index > 0:
            return items[current_index - 1]
    except (ValueError, IndexError):
        pass
    return None
