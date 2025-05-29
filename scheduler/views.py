from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme as is_safe_url
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView
from datetime import timedelta, datetime, time
import json

from core.models import User
from courses.models import Course
from .models import Event, EventLocation, EventParticipant
from .forms import EventForm, EventLocationForm, ParticipantForm

# Placeholder para views que serão implementadas na próxima etapa

@login_required
def calendar_view(request):
    """
    View para exibir o calendário principal do professor.
    Redireciona primeiro para a seleção de estúdios.
    """
    # Verifica se o usuário é professor
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Acesso restrito a professores.'))
        return redirect('home')
    
    # Verificar se um estúdio foi selecionado
    location_id = request.GET.get('location')
    if not location_id:
        # Se não houver estúdio selecionado, redireciona para a seleção de estúdios
        return redirect('scheduler:location_list')
    
    try:
        # Validar se o estúdio existe e está disponível para o usuário
        location = EventLocation.objects.get(
            Q(created_by=request.user) | Q(is_active=True),
            pk=location_id
        )
    except EventLocation.DoesNotExist:
        messages.error(request, _('Estúdio não encontrado ou indisponível.'))
        return redirect('scheduler:location_list')
        
    # Obtém os próximos eventos do professor neste estúdio
    upcoming_events = Event.objects.filter(
        professor=request.user,
        location=location,
        start_time__gte=timezone.now(),
        status__in=['SCHEDULED', 'CONFIRMED']
    ).order_by('start_time')[:5]
    
    context = {
        'upcoming_events': upcoming_events,
        'location': location,
        'page_title': _('Agenda - {}'.format(location.name))
    }
    
    return render(request, 'scheduler/calendar.html', context)

@login_required
def event_list(request):
    """
    Lista todos os eventos do professor.
    """
    # Verifica se o usuário é professor
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Acesso restrito a professores.'))
        return redirect('home')
    
    # Filtra eventos por parâmetros (se fornecidos)
    status_filter = request.GET.get('status', None)
    type_filter = request.GET.get('type', None)
    date_from = request.GET.get('from', None)
    date_to = request.GET.get('to', None)
    
    # Inicia com todos os eventos do professor
    events = Event.objects.filter(professor=request.user)
    
    # Aplica filtros se fornecidos
    if status_filter:
        events = events.filter(status=status_filter)
    if type_filter:
        events = events.filter(event_type=type_filter)
    if date_from:
        events = events.filter(start_time__date__gte=date_from)
    if date_to:
        events = events.filter(start_time__date__lte=date_to)
    
    # Ordena por data de início (mais recentes primeiro)
    events = events.order_by('-start_time')
    
    context = {
        'events': events,
        'page_title': _('Meus Eventos')
    }
    
    return render(request, 'scheduler/event_list.html', context)

@login_required
def event_create(request):
    """
    Cria um novo evento.
    """
    # Importações necessárias
    from .models import EventLocation
    
    # Verifica permissão
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Apenas professores podem criar eventos.'))
        return redirect('home')
    
    print("==== INICIANDO CRIAÇÃO DE EVENTO ====")
    print(f"Request method: {request.method}")
    
    if request.method == 'POST':
        print("POST data:", request.POST)
        
        # Verificar se é uma requisição do modal de agendamento rápido
        if 'from_modal' in request.POST and 'start_time' in request.POST and 'end_time' in request.POST:
            print("Detectada requisição do modal de agendamento rápido")
            
            # Obter dados básicos
            location_id = request.POST.get('location')
            location = get_object_or_404(EventLocation, id=location_id)
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            title = request.POST.get('title')
            event_type = request.POST.get('event_type', 'CLASS')
            
            # Verificações básicas
            if not title:
                title = f"{dict(Event.EVENT_TYPE_CHOICES).get(event_type, 'Evento')} - {start_time.split('T')[0]}"
            
            # Criar o evento
            event = Event(
                title=title,
                professor=request.user,
                event_type=event_type,
                location=location,
                start_time=start_time,
                end_time=end_time,
                status='SCHEDULED',
                color='#3788d8'  # Cor padrão azul
            )
            
            # Campos opcionais
            if request.POST.get('description'):
                event.description = request.POST.get('description')
            
            if request.POST.get('max_participants'):
                try:
                    event.max_participants = int(request.POST.get('max_participants'))
                except (ValueError, TypeError):
                    pass
            
            if request.POST.get('course'):
                from courses.models import Course
                try:
                    course = Course.objects.get(id=request.POST.get('course'))
                    event.course = course
                except Course.DoesNotExist:
                    pass
            
            # Salvar o evento
            event.save()
            
            # Adicionar participantes
            if request.POST.get('selected_students'):
                student_ids = [int(sid) for sid in request.POST.get('selected_students').split(',') if sid.strip()]
                if student_ids:
                    from core.models import User
                    students = User.objects.filter(id__in=student_ids, user_type='STUDENT')
                    for student in students:
                        EventParticipant.objects.create(
                            event=event,
                            student=student,
                            attendance_status='PENDING'
                        )
                    
                    messages.info(request, _(f'Convites enviados para {len(students)} aluno(s).'))
            
            # Mostrar mensagem de sucesso
            messages.success(request, _('Agendamento realizado com sucesso!'))
            
            # Redirecionar para o calendário
            return HttpResponseRedirect(reverse('scheduler:location_calendar', args=[location_id]) + '?success=true')
        
        # Fluxo normal para o formulário completo
        form = EventForm(request.POST, professor=request.user)
        if form.is_valid():
            print("Form válido, salvando evento...")
            event = form.save(commit=False)
            event.professor = request.user
            event.save()
            
            # Processar participantes
            selected_students = request.POST.get('selected_students', '')
            print(f"Alunos selecionados: {selected_students}")
            
            if selected_students:
                student_ids = [int(id) for id in selected_students.split(',') if id.strip()]
                if student_ids:
                    from core.models import User
                    students = User.objects.filter(id__in=student_ids, user_type='STUDENT')
                    print(f"Encontrados {students.count()} alunos para adicionar ao evento {event.id}")
                    
                    for student in students:
                        participant = EventParticipant.objects.create(
                            event=event,
                            student=student,
                            attendance_status='PENDING'
                        )
                        print(f"Criado participante ID {participant.id} para aluno {student.email}")
                    
                    total_participants = EventParticipant.objects.filter(event=event).count()
                    print(f"Total de participantes após criação: {total_participants}")
                    messages.info(request, _(f'Convites enviados para {students.count()} aluno(s).'))
            
            messages.success(request, _('Evento criado com sucesso!'))
            return redirect('scheduler:event_detail', pk=event.id)
        else:
            print("Erros no formulário:", form.errors)
    else:
        # Pré-preencher com data e hora sugeridas
        initial = {}
        
        # Se tiver location_id na query string, pré-selecionar o estúdio
        location_id = request.GET.get('location')
        if location_id:
            try:
                from scheduler.models import EventLocation
                initial['location'] = EventLocation.objects.get(id=location_id)
            except (EventLocation.DoesNotExist, ValueError):
                pass
        
        form = EventForm(professor=request.user, initial=initial)
    
    context = {
        'form': form,
        'page_title': _('Novo Evento')
    }
    
    return render(request, 'scheduler/event_form.html', context)

@login_required
def event_detail(request, pk):
    """
    Mostra detalhes de um evento específico.
    """
    event = get_object_or_404(Event, pk=pk)
    
    # Verifica permissão (somente o professor responsável pode ver o evento)
    if event.professor != request.user and request.user.user_type != 'ADMIN':
        return HttpResponseForbidden(_('Você não tem permissão para ver este evento.'))
    
    # Obtém participantes
    participants = event.participants.all().select_related('student')
    
    context = {
        'event': event,
        'participants': participants,
        'page_title': event.title
    }
    
    return render(request, 'scheduler/event_detail.html', context)

@login_required
def event_edit(request, pk):
    """
    Edita um evento existente.
    """
    event = get_object_or_404(Event, pk=pk)
    
    # Verifica permissão (somente o professor responsável pode editar o evento)
    if event.professor != request.user:
        return HttpResponseForbidden(_('Você não tem permissão para editar este evento.'))
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, professor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Evento atualizado com sucesso!'))
            return redirect('scheduler:event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event, professor=request.user)
    
    context = {
        'form': form,
        'event': event,
        'page_title': _('Editar Evento')
    }
    
    return render(request, 'scheduler/event_form.html', context)

@login_required
def event_delete(request, pk):
    """
    Remove um evento.
    """
    event = get_object_or_404(Event, pk=pk)
    
    # Verifica permissão (somente o professor responsável pode excluir o evento)
    if event.professor != request.user:
        return HttpResponseForbidden(_('Você não tem permissão para excluir este evento.'))
    
    if request.method == 'POST':
        # Guarda o título para a mensagem de feedback
        event_title = event.title
        event.delete()
        messages.success(request, _(f'O evento "{event_title}" foi removido com sucesso.'))
        return redirect('scheduler:event_list')
    
    context = {
        'event': event,
        'page_title': _('Confirmar Exclusão')
    }
    
    return render(request, 'scheduler/event_confirm_delete.html', context)

@login_required
def location_list(request):
    """
    Lista todos os estúdios disponíveis para o professor.
    View simplificada para melhor experiência do usuário.
    """
    # Verifica se o usuário é professor
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Acesso restrito a professores.'))
        return redirect('home')
    
    # Filtros para localizar estúdios (ativos ou criados pelo professor)
    locations = EventLocation.objects.filter(
        Q(created_by=request.user) | Q(is_active=True)
    )
    
    # Adicionar contagem de eventos para cada estúdio com nome diferente
    # para evitar conflito com a propriedade event_count do modelo
    locations = locations.annotate(events_count=Count('events'))
    
    # Filtros opcionais
    location_type = request.GET.get('type')
    if location_type == 'online':
        locations = locations.filter(is_online=True)
    elif location_type == 'physical':
        locations = locations.filter(is_online=False)
    
    # Ordenar por nome para facilitar localização
    locations = locations.order_by('name')
    
    context = {
        'locations': locations,
        'location_type': location_type,
        'page_title': _('Estúdios')
    }
    
    return render(request, 'scheduler/location_list.html', context)

@login_required
def location_create(request):
    """
    Cria um novo estúdio. 
    Redireciona para a lista de estúdios após a criação.
    """
    # Verificar se o usuário é professor
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Acesso restrito a professores.'))
        return redirect('home')
        
    if request.method == 'POST':
        form = EventLocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            location.created_by = request.user  # Garantir que o criador seja definido
            location.save()
            messages.success(request, _(f'Estúdio "{location.name}" criado com sucesso!'))
            return redirect('scheduler:location_list')
    else:
        form = EventLocationForm()
    
    context = {
        'form': form,
        'is_online': False,
        'page_title': _('Novo Estúdio')
    }
    
    return render(request, 'scheduler/location_form.html', context)

@login_required
def location_detail(request, pk):
    """
    Mostra detalhes de um estúdio específico.
    """
    location = get_object_or_404(EventLocation, pk=pk)
    
    # Verifica se o estúdio está ativo ou pertence ao usuário
    if not location.is_active and location.created_by != request.user:
        messages.error(request, _('Este estúdio não está disponível.'))
        return redirect('scheduler:location_list')
    
    # Obtém eventos associados a este estúdio
    events = Event.objects.filter(location=location)
    
    if request.user.user_type == 'PROFESSOR':
        # Professores só veem seus próprios eventos
        events = events.filter(professor=request.user)
    
    context = {
        'location': location,
        'events': events,
        'page_title': location.name
    }
    
    return render(request, 'scheduler/location_detail.html', context)

@login_required
def location_edit(request, pk):
    """
    Simplifica a edição de um estúdio existente para facilitar a atualização.
    
    Permite a qualquer professor editar os estúdios,
    e melhora o processo com feedback visual e redirecionamentos inteligentes.
    """
    location = get_object_or_404(EventLocation, pk=pk)
    
    # Verificar permissões - apenas professores podem editar
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Você não tem permissão para editar este estúdio.'))
        return redirect('scheduler:location_list')
    
    if request.method == 'POST':
        form = EventLocationForm(request.POST, instance=location)
        if form.is_valid():
            studio = form.save(commit=False)
            # Manter o created_by original
            studio.created_by = location.created_by
            studio.save()
            messages.success(request, _(f'Estúdio "{location.name}" atualizado com sucesso!'))
            
            # Redirecionamento inteligente - volta para a lista ou para onde o usuário estava
            next_url = request.POST.get('next')
            if next_url and is_safe_url(next_url, allowed_hosts=None):
                return redirect(next_url)
            return redirect('scheduler:location_list')
    else:
        form = EventLocationForm(instance=location)
    
    context = {
        'form': form,
        'is_online': location.is_online,
        'back_url': request.GET.get('next', reverse('scheduler:location_list')),
        'page_title': _('Editar Estúdio'),
    }
    
    return render(request, 'scheduler/location_form.html', context)

@login_required
def location_delete(request, pk):
    """
    Remove um estúdio.
    """
    location = get_object_or_404(EventLocation, pk=pk)
    
    # Verifica permissão (somente o criador ou um admin pode excluir)
    if location.created_by != request.user and request.user.user_type != 'ADMIN':
        return HttpResponseForbidden(_('Você não tem permissão para excluir este estúdio.'))
    
    if request.method == 'POST':
        # Guarda o nome para a mensagem de feedback
        location_name = location.name
        location.delete()
        messages.success(request, _(f'O estúdio "{location_name}" foi removido com sucesso.'))
        return redirect('scheduler:location_list')
    
    context = {
        'location': location,
        'page_title': _('Confirmar Exclusão')
    }
    
    return render(request, 'scheduler/location_confirm_delete.html', context)

@login_required
def participant_list(request, event_id):
    """
    Lista todos os participantes de um evento.
    """
    event = get_object_or_404(Event, pk=event_id)
    
    # Verifica permissão (somente o professor responsável pode ver os participantes)
    if event.professor != request.user and request.user.user_type != 'ADMIN':
        return HttpResponseForbidden(_('Você não tem permissão para ver os participantes deste evento.'))
    
    # Obtém participantes
    participants = event.participants.all().select_related('student')
    
    context = {
        'event': event,
        'participants': participants,
        'page_title': _('Participantes do Evento')
    }
    
    return render(request, 'scheduler/participant_list.html', context)

@login_required
def add_participant(request, event_id):
    """
    Adiciona um participante a um evento.
    """
    event = get_object_or_404(Event, pk=event_id)
    
    # Verifica permissão (somente o professor responsável pode adicionar participantes)
    if event.professor != request.user:
        return HttpResponseForbidden(_('Você não tem permissão para adicionar participantes a este evento.'))
    
    # Verificar se o evento já atingiu o limite de participantes
    if event.max_participants and event.participants.count() >= event.max_participants:
        messages.warning(request, _('Este evento já atingiu o limite máximo de participantes.'))
        return redirect('scheduler:participant_list', event_id=event.id)
    
    if request.method == 'POST':
        form = ParticipantForm(request.POST, event=event)
        if form.is_valid():
            participant = form.save(commit=False)
            participant.event = event
            participant.save()
            
            student_name = participant.student.get_full_name() or participant.student.email
            messages.success(request, _(f'{student_name} adicionado(a) ao evento com sucesso!'))
            return redirect('scheduler:participant_list', event_id=event.id)
    else:
        form = ParticipantForm(event=event)
    
    context = {
        'form': form,
        'event': event,
        'page_title': _('Adicionar Participante')
    }
    
    return render(request, 'scheduler/participant_form.html', context)

@login_required
def professor_dashboard(request):
    """
    Dashboard do professor com todas as informações sobre seus agendamentos.
    Exibe eventos próximos, convites pendentes e histórico.
    """
    # Verifica se o usuário é professor
    if request.user.user_type != 'PROFESSOR':
        messages.error(request, _('Acesso restrito a professores.'))
        return redirect('home')
    
    # Obtém a data atual
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    # Obtém eventos do professor (futuros, hoje e passados)
    upcoming_events = Event.objects.filter(
        professor=request.user,
        start_time__gt=today_end
    ).order_by('start_time')[:10]
    
    today_events = Event.objects.filter(
        professor=request.user,
        start_time__gte=today_start,
        start_time__lt=today_end
    ).order_by('start_time')
    
    past_events = Event.objects.filter(
        professor=request.user,
        end_time__lt=today_start
    ).order_by('-start_time')[:5]
    
    # Calcular estatísticas
    total_events = Event.objects.filter(professor=request.user).count()
    scheduled_events = Event.objects.filter(professor=request.user, status='SCHEDULED').count()
    confirmed_events = Event.objects.filter(professor=request.user, status='CONFIRMED').count()
    today_events_count = today_events.count()
    
    # Obter participantes com convites pendentes
    pending_responses = EventParticipant.objects.filter(
        event__professor=request.user,
        attendance_status='PENDING',
        event__start_time__gt=now
    ).select_related('student', 'event')
    
    context = {
        'upcoming_events': upcoming_events,
        'today_events': today_events_count,
        'past_events': past_events,
        'total_events': total_events,
        'scheduled_events': scheduled_events,
        'confirmed_events': confirmed_events,
        'pending_responses': pending_responses,
        'has_more_events': Event.objects.filter(professor=request.user).count() > 15,
        'page_title': _('Dashboard do Professor')
    }
    
    return render(request, 'scheduler/professor_dashboard.html', context)

@login_required
def student_notifications(request):
    """
    Exibe e gerencia convites de agendamentos para o aluno.
    Permite confirmar ou recusar convites.
    """
    # Verifica se o usuário é aluno
    if request.user.user_type != 'STUDENT':
        messages.error(request, _('Acesso restrito a alunos.'))
        return redirect('home')
    
    # Obtém a data atual
    now = timezone.now()
    
    # Obtém todos os convites do aluno
    all_invitations = EventParticipant.objects.filter(
        student=request.user
    ).select_related('event', 'event__professor', 'event__location', 'event__course')
    
    # Separa por status
    pending_invitations_list = all_invitations.filter(
        attendance_status='PENDING',
        event__start_time__gt=now
    ).order_by('event__start_time')
    
    confirmed_invitations_list = all_invitations.filter(
        attendance_status='CONFIRMED',
        event__start_time__gt=now
    ).order_by('event__start_time')
    
    # Contadores
    total_invitations = all_invitations.count()
    pending_invitations = pending_invitations_list.count()
    confirmed_invitations = confirmed_invitations_list.count()
    
    context = {
        'total_invitations': total_invitations,
        'pending_invitations': pending_invitations,
        'confirmed_invitations': confirmed_invitations,
        'pending_invitations_list': pending_invitations_list,
        'confirmed_invitations_list': confirmed_invitations_list,
        'page_title': _('Convites para Agendamentos')
    }
    
    return render(request, 'scheduler/student_notifications.html', context)

# Views da API para integração com FullCalendar.js (serão detalhadas na próxima etapa)

@login_required
def api_events(request):
    """API para fornecer eventos para o calendário."""
    try:
        location_id = request.GET.get('location')
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')
        
        # Verificar se o location_id está vazio ou não é válido
        if not location_id:
            return JsonResponse({'error': 'ID da localização é obrigatório'}, status=400)
            
        # Converter de string para data
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month.replace(day=1)
        
        events = Event.objects.filter(
            location_id=location_id,
            start_time__gte=start_date,
            end_time__lte=end_date
        ).select_related('professor', 'course')
        
        result = []
        for event in events:
            can_edit = request.user.is_staff or request.user == event.professor
            
            event_data = {
                'id': event.id,
                'title': event.title,
                'start': event.start_time.isoformat(),
                'end': event.end_time.isoformat(),
                'extendedProps': {
                    'description': event.description,
                    'event_type': event.event_type,
                    'status': event.status,
                    'professor_name': str(event.professor) if event.professor else None,
                    'course_name': str(event.course) if event.course else None,
                    'max_participants': event.max_participants,
                    'current_participants': event.participants.count(),
                    'can_edit': can_edit
                },
                'className': 'booked'
            }
            
            # Se o usuário atual é o professor do evento ou participante, destaque
            if request.user == event.professor or request.user in event.participants.all():
                event_data['className'] = 'my-booking'
            
            result.append(event_data)
        
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_event_detail(request, pk):
    """
    API para obter detalhes de um evento específico.
    """
    try:
        event = Event.objects.get(pk=pk)
        
        # Verifica permissão (apenas o professor do evento ou admin)
        if event.professor != request.user and request.user.user_type != 'ADMIN':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Obter participantes
        participants = [{
            'id': p.id,
            'student_id': p.student.id,
            'name': p.student.get_full_name(),
            'email': p.student.email,
            'status': p.attendance_status,
            'confirmed_at': p.confirmed_at.isoformat() if p.confirmed_at else None,
            'notes': p.notes
        } for p in event.participants.all().select_related('student')]
        
        # Formatar dados do evento
        event_data = {
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'start_time': event.start_time.isoformat(),
            'end_time': event.end_time.isoformat(),
            'all_day': event.all_day,
            'event_type': event.event_type,
            'status': event.status,
            'is_recurring': event.is_recurring,
            'recurrence_rule': event.recurrence_rule,
            'color': event.color,
            'max_participants': event.max_participants,
            'current_participants': len(participants),
            'location': {
                'id': event.location.id,
                'name': event.location.name,
                'is_online': event.location.is_online,
                'address': event.location.address,
                'meeting_link': event.location.meeting_link
            } if event.location else None,
            'course': {
                'id': event.course.id,
                'title': event.course.title
            } if event.course else None,
            'participants': participants,
            'created_at': event.created_at.isoformat(),
            'updated_at': event.updated_at.isoformat()
        }
        
        return JsonResponse(event_data)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)

class LocationCalendarView(LoginRequiredMixin, DetailView):
    model = EventLocation
    template_name = 'scheduler/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"{_('Agenda')}: {self.object.name}"
        
        # Adicionar cursos do professor ao contexto
        if self.request.user.user_type == 'PROFESSOR':
            from courses.models import Course
            context['professor_courses'] = Course.objects.filter(
                professor=self.request.user
            ).values('id', 'title')
            
            # Adicionar contagem de alunos a cada curso
            for course in context['professor_courses']:
                course_obj = Course.objects.get(id=course['id'])
                course['student_count'] = course_obj.get_enrolled_students_count()
        
        return context

# API Views
def api_available_slots(request):
    """API para fornecer horários disponíveis para uma data e unidade específicas."""
    try:
        date_str = request.GET.get('date')
        location_id = request.GET.get('location')
        custom_check = request.GET.get('custom_check') == 'true'
        custom_start = request.GET.get('start_time')  # Formato HH:MM
        custom_end = request.GET.get('end_time')      # Formato HH:MM
        
        if not date_str or not location_id:
            return JsonResponse({'error': 'Data e localização são obrigatórios'}, status=400)
        
        # Converter a string de data para um objeto date
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Verificar se a data é válida (não é no passado e está dentro do período permitido)
        today = timezone.localdate()
        max_future_date = today + timedelta(days=90)  # 3 meses
        
        if selected_date < today:
            return JsonResponse({'error': 'Não é possível agendar para datas passadas'}, status=400)
        
        if selected_date > max_future_date:
            return JsonResponse({'error': 'Não é possível agendar com mais de 3 meses de antecedência'}, status=400)
        
        # Obter unidade
        try:
            location = EventLocation.objects.get(id=location_id, is_active=True)
        except EventLocation.DoesNotExist:
            return JsonResponse({'error': 'Unidade não encontrada'}, status=404)
        
        # Definir horários de funcionamento do local
        # Isso deve vir do modelo de Location no futuro, mas por enquanto vamos padronizar
        operating_hours = {
            0: [],  # Segunda (0 = segunda na convenção Python para dias da semana)
            1: [(time(8, 0), time(20, 0))],  # Terça
            2: [(time(8, 0), time(20, 0))],  # Quarta
            3: [(time(8, 0), time(20, 0))],  # Quinta
            4: [(time(8, 0), time(20, 0))],  # Sexta
            5: [(time(9, 0), time(16, 0))],  # Sábado
            6: []  # Domingo
        }
        
        # Obter eventos existentes para a data e local
        day_start = timezone.make_aware(datetime.combine(selected_date, time.min))
        day_end = timezone.make_aware(datetime.combine(selected_date, time.max))
        
        existing_events = Event.objects.filter(
            location=location,
            start_time__date=selected_date,
            status__in=['SCHEDULED', 'CONFIRMED']  # Considerar apenas eventos não cancelados
        ).order_by('start_time')
        
        # Para fins de debug, também retornamos os eventos existentes
        existing_events_data = [{
            'id': event.id,
            'title': event.title,
            'start': event.start_time.isoformat(),
            'end': event.end_time.isoformat(),
            'professor': event.professor.get_full_name() or event.professor.email
        } for event in existing_events]
        
        # Se for uma verificação de horário personalizado
        if custom_check and custom_start and custom_end:
            try:
                # Converter strings de horário para objetos time
                start_time = datetime.strptime(custom_start, '%H:%M').time()
                end_time = datetime.strptime(custom_end, '%H:%M').time()
                
                # Criar datetime para comparação
                slot_start = timezone.make_aware(datetime.combine(selected_date, start_time))
                slot_end = timezone.make_aware(datetime.combine(selected_date, end_time))
                
                # Verificar duração (máximo 3 horas)
                duration_minutes = (slot_end - slot_start).total_seconds() / 60
                
                if duration_minutes > 180:  # 3 horas = 180 minutos
                    return JsonResponse({'error': 'Duração máxima permitida é de 3 horas',
                                        'available': False}, status=400)
                
                # Verificar disponibilidade
                is_available = True
                conflicting_event = None
                
                # Verificar se está dentro do horário de funcionamento
                weekday = selected_date.weekday()
                within_operating_hours = False
                
                if operating_hours[weekday]:
                    for open_start, open_end in operating_hours[weekday]:
                        if start_time >= open_start and end_time <= open_end:
                            within_operating_hours = True
                            break
                
                if not within_operating_hours:
                    return JsonResponse({
                        'available': False,
                        'reason': 'outside_hours',
                        'message': 'O horário selecionado está fora do horário de funcionamento'
                    })
                
                # Verificar conflitos com outros eventos
                for event in existing_events:
                    if (slot_start < event.end_time and slot_end > event.start_time):
                        is_available = False
                        conflicting_event = {
                            'id': event.id,
                            'title': event.title,
                            'start': event.start_time.isoformat(),
                            'end': event.end_time.isoformat()
                        }
                        break
                
                return JsonResponse({
                    'available': is_available,
                    'custom_start': slot_start.isoformat(),
                    'custom_end': slot_end.isoformat(),
                    'conflicting_event': conflicting_event,
                    'existing_events': existing_events_data
                })
                
            except ValueError as e:
                return JsonResponse({'error': f'Formato de horário inválido: {str(e)}'}, status=400)
        
        # Criar slots de tempo disponíveis (padrão de 1 hora)
        weekday = selected_date.weekday()  # 0 = segunda, 6 = domingo
        available_slots = []
        
        # Se for um dia em que a unidade funciona
        if operating_hours[weekday]:
            for start_hour, end_hour in operating_hours[weekday]:
                current_time = start_hour
                while current_time < end_hour:
                    slot_start = timezone.make_aware(datetime.combine(selected_date, current_time))
                    
                    # Duração padrão do slot: 1 hora
                    next_hour = (
                        datetime.combine(selected_date, current_time) + timedelta(hours=1)
                    ).time()
                    
                    slot_end = timezone.make_aware(datetime.combine(selected_date, next_hour))
                    
                    # Verificar se este slot está disponível
                    is_available = True
                    conflicting_event = None
                    
                    for event in existing_events:
                        # Verificar se há sobreposição de horário
                        if (slot_start < event.end_time and slot_end > event.start_time):
                            is_available = False
                            conflicting_event = {
                                'id': event.id,
                                'title': event.title
                            }
                            break
                    
                    # Adicionar o slot à lista
                    time_slot = {
                        'start_time': slot_start.strftime('%H:%M'),
                        'end_time': slot_end.strftime('%H:%M'),
                        'start_time_raw': slot_start.isoformat(),
                        'end_time_raw': slot_end.isoformat(),
                        'available': is_available,
                        'conflicting_event': conflicting_event
                    }
                    
                    available_slots.append(time_slot)
                    
                    # Avançar para o próximo slot
                    current_time = next_hour
        
        return JsonResponse({
            'available_slots': available_slots,
            'existing_events': existing_events_data,
            'date': selected_date.isoformat(),
            'location': {
                'id': location.id,
                'name': location.name
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class LocationListView(LoginRequiredMixin, ListView):
    model = EventLocation
    template_name = 'scheduler/location_list.html'
    context_object_name = 'object_list'
    
    def get_queryset(self):
        """Filtra apenas unidades ativas."""
        return EventLocation.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

# Class-based Views para Eventos
class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    template_name = 'scheduler/event_form.html'
    form_class = EventForm
    
    def get(self, request, *args, **kwargs):
        # Verificar se estamos vindo do modal de calendário
        if request.GET.get('from_modal') == 'true':
            # Redirecionar de volta para o calendário
            location_id = request.GET.get('location', 1)
            return HttpResponseRedirect(reverse('scheduler:location_calendar', args=[location_id]))
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        # Verificar se a requisição vem do modal (com campos ISO)
        if 'start_time' in request.POST and 'end_time' in request.POST and 'from_modal' in request.POST:
            # 1. Criar evento com os dados do modal
            location_id = request.POST.get('location')
            location = get_object_or_404(EventLocation, id=location_id)
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            title = request.POST.get('title')
            event_type = request.POST.get('event_type', 'CLASS')
            
            # Verificações básicas
            if not title:
                title = f"{dict(Event.EVENT_TYPE_CHOICES).get(event_type, 'Evento')} - {start_time.split('T')[0]}"
            
            # Criar o evento
            event = Event(
                title=title,
                professor=request.user,
                event_type=event_type,
                location=location,
                start_time=start_time,
                end_time=end_time,
                status='SCHEDULED',
                color='#3788d8'  # Cor padrão azul
            )
            
            # Campos opcionais
            if request.POST.get('description'):
                event.description = request.POST.get('description')
            
            if request.POST.get('max_participants'):
                try:
                    event.max_participants = int(request.POST.get('max_participants'))
                except (ValueError, TypeError):
                    pass
            
            if request.POST.get('course'):
                from courses.models import Course
                try:
                    course = Course.objects.get(id=request.POST.get('course'))
                    event.course = course
                except Course.DoesNotExist:
                    pass
            
            # Salvar o evento
            event.save()
            
            # 2. Adicionar participantes
            if request.POST.get('selected_students'):
                student_ids = [int(sid) for sid in request.POST.get('selected_students').split(',') if sid.strip()]
                if student_ids:
                    students = User.objects.filter(id__in=student_ids, user_type='STUDENT')
                    for student in students:
                        EventParticipant.objects.create(
                            event=event,
                            student=student,
                            attendance_status='PENDING'
                        )
                    
                    messages.info(request, _(f'Convites enviados para {len(students)} aluno(s).'))
            
            # 3. Mostrar mensagem de sucesso
            messages.success(request, _('Agendamento realizado com sucesso!'))
            
            # 4. Redirecionar para o calendário
            return HttpResponseRedirect(reverse('scheduler:location_calendar', args=[location_id]) + '?success=true')
        
        # Caso não seja do modal, seguir o fluxo normal
        return super().post(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Novo Agendamento')
        context['is_create'] = True
        
        # Adicionar cursos do professor ao contexto
        if self.request.user.user_type == 'PROFESSOR':
            from courses.models import Course
            context['professor_courses'] = Course.objects.filter(
                professor=self.request.user
            ).values('id', 'title', 'status')
        
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['professor'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        # Redirecionar de volta para o calendário da unidade com um parâmetro de sucesso
        location_id = self.object.location.id
        return reverse('scheduler:location_calendar', args=[location_id]) + '?success=true'
    
    def form_valid(self, form):
        """
        Processar o formulário de agendamento vindo do modal.
        Aceita diretamente os campos start_time e end_time em formato ISO.
        """
        # Configurar professor como o usuário atual
        form.instance.professor = self.request.user
        
        # Obter dados do form de agendamento
        try:
            # Obter dados do formulário
            location_id = self.request.POST.get('location')
            start_time_str = self.request.POST.get('start_time')
            end_time_str = self.request.POST.get('end_time')
            course_id = self.request.POST.get('course')
            selected_students = self.request.POST.get('selected_students', '')
            
            # Verificar que os dados necessários foram fornecidos
            if not all([location_id, start_time_str, end_time_str]):
                messages.error(self.request, _('Dados de agendamento incompletos. Por favor, preencha todos os campos.'))
                return self.form_invalid(form)
            
            # Configurar o local do evento
            try:
                form.instance.location = EventLocation.objects.get(pk=location_id)
            except EventLocation.DoesNotExist:
                messages.error(self.request, _('Estúdio não encontrado.'))
                return self.form_invalid(form)
            
            # Converter strings ISO para objetos datetime
            try:
                form.instance.start_time = datetime.fromisoformat(start_time_str)
                form.instance.end_time = datetime.fromisoformat(end_time_str)
            except ValueError:
                messages.error(self.request, _('Formato de data/hora inválido.'))
                return self.form_invalid(form)
            
            # Verificar se a duração não ultrapassa 3 horas (verificação de segurança no backend)
            duration = (form.instance.end_time - form.instance.start_time).total_seconds() / 3600
            if duration > 3:
                messages.error(self.request, _('A duração máxima permitida é de 3 horas.'))
                return self.form_invalid(form)
            
            # Associar ao curso, se selecionado
            if course_id:
                from courses.models import Course
                try:
                    course = Course.objects.get(pk=course_id, professor=self.request.user)
                    form.instance.course = course
                except Course.DoesNotExist:
                    messages.warning(self.request, _('Curso selecionado não encontrado ou não pertence a você.'))
            
            # Verificar se este horário está disponível
            overlapping_events = Event.objects.filter(
                location_id=location_id,
                start_time__lt=form.instance.end_time,
                end_time__gt=form.instance.start_time,
                status__in=['SCHEDULED', 'CONFIRMED']
            )
            
            if overlapping_events.exists():
                messages.error(self.request, _('Este horário já está ocupado. Por favor, escolha outro.'))
                return self.form_invalid(form)
            
            # Configurar status inicial
            form.instance.status = 'SCHEDULED'
            
            # Se for do tipo "OTHER", converter para o tipo especificado
            if form.instance.event_type == 'OTHER' and self.request.POST.get('other_type'):
                form.instance.description = f"Tipo: {self.request.POST.get('other_type')}\n\n{form.instance.description or ''}"
            
            # Salvar o evento
            response = super().form_valid(form)
            
            # Criar participantes se alunos foram selecionados
            if selected_students:
                student_ids = [int(id) for id in selected_students.split(',') if id.strip()]
                if student_ids:
                    from core.models import User
                    students = User.objects.filter(id__in=student_ids, user_type='STUDENT')
                    
                    for student in students:
                        EventParticipant.objects.create(
                            event=self.object,
                            student=student,
                            attendance_status='PENDING'
                        )
                    
                    messages.info(self.request, _(f'Convites enviados para {len(students)} aluno(s).'))
            
            # Adicionar mensagem de sucesso
            messages.success(self.request, _('Agendamento realizado com sucesso!'))
            return response
            
        except Exception as e:
            messages.error(self.request, _(f'Erro ao agendar: {str(e)}'))
            return self.form_invalid(form)

class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'scheduler/event_list.html'
    context_object_name = 'events'
    paginate_by = 10
    
    def get_queryset(self):
        # Filtrar eventos por professor
        queryset = Event.objects.filter(
            professor=self.request.user  # Aqui está corrigido
        ).order_by('-start_time')
        
        # Filtrar por status, se fornecido
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset

class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'scheduler/event_detail.html'
    context_object_name = 'event'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        user = self.request.user
        
        # Verificar se o usuário atual pode editar este evento
        context['can_edit'] = user.is_staff or user == event.professor
        
        # Verificar se o usuário atual é participante
        context['is_participant'] = user in event.participants.all()
        
        return context

class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    fields = ['title', 'event_type', 'description', 'max_participants', 'status']
    template_name = 'scheduler/event_form.html'
    
    def get_success_url(self):
        return reverse_lazy('scheduler:event_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Editar Agendamento')
        return context
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar se o usuário tem permissão para editar
        event = self.get_object()
        if not (request.user.is_staff or request.user == event.professor):
            messages.error(request, _('Você não tem permissão para editar este agendamento.'))
            return HttpResponseRedirect(reverse('scheduler:event_detail', args=[event.id]))
        return super().dispatch(request, *args, **kwargs)

class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    template_name = 'scheduler/event_confirm_delete.html'
    success_url = reverse_lazy('scheduler:event_list')
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar se o usuário tem permissão para excluir
        event = self.get_object()
        if not (request.user.is_staff or request.user == event.professor):
            messages.error(request, _('Você não tem permissão para cancelar este agendamento.'))
            return HttpResponseRedirect(reverse('scheduler:event_detail', args=[event.id]))
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        event = self.get_object()
        
        # Em vez de excluir, marcar como cancelado
        event.status = 'CANCELLED'
        event.save()
        
        messages.success(request, _('Agendamento cancelado com sucesso.'))
        return HttpResponseRedirect(self.success_url)

# API para buscar alunos de um curso
@login_required
def api_course_students(request):
    """API para buscar alunos matriculados em um curso específico."""
    try:
        course_id = request.GET.get('course_id')
        if not course_id:
            return JsonResponse({'error': 'ID do curso é obrigatório'}, status=400)
        
        # Verificar se o curso existe e pertence ao professor
        from courses.models import Course, Enrollment
        
        try:
            course = Course.objects.get(pk=course_id)
            # Verificar se o usuário tem permissão para acessar este curso
            if request.user != course.professor and not request.user.is_staff:
                return JsonResponse({'error': 'Acesso negado'}, status=403)
        except Course.DoesNotExist:
            return JsonResponse({'error': 'Curso não encontrado'}, status=404)
        
        # Buscar alunos matriculados ativos
        enrollments = Enrollment.objects.filter(
            course=course, 
            status=Enrollment.Status.ACTIVE
        ).select_related('student')
        
        students = [{
            'id': enrollment.student.id,
            'name': enrollment.student.get_full_name() or enrollment.student.email,
            'email': enrollment.student.email,
            'avatar': enrollment.student.profile_image.url if enrollment.student.profile_image else None,
            'enrollment_id': enrollment.id,
            'progress': enrollment.progress
        } for enrollment in enrollments]
        
        return JsonResponse({
            'course': {
                'id': course.id,
                'title': course.title
            },
            'students': students
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# API para gerenciar participantes
@login_required
def api_manage_participants(request, event_id):
    """API para adicionar, remover ou atualizar participantes de um evento."""
    try:
        event = get_object_or_404(Event, pk=event_id)
        
        # Verificar permissão (somente o professor responsável pode gerenciar participantes)
        if event.professor != request.user and not request.user.is_staff:
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        
        if request.method == 'GET':
            # Listar participantes
            participants = event.participants.all().select_related('student')
            return JsonResponse({
                'participants': [{
                    'id': participant.id,
                    'student_id': participant.student.id,
                    'name': participant.student.get_full_name() or participant.student.email,
                    'email': participant.student.email,
                    'status': participant.attendance_status,
                    'confirmed_at': participant.confirmed_at.isoformat() if participant.confirmed_at else None,
                    'notes': participant.notes
                } for participant in participants]
            })
        
        elif request.method == 'POST':
            # Adicionar participantes
            data = json.loads(request.body)
            student_ids = data.get('student_ids', [])
            
            if not student_ids:
                return JsonResponse({'error': 'Lista de IDs de alunos é obrigatória'}, status=400)
            
            # Verificar se o evento já atingiu o limite de participantes
            if event.max_participants and event.participants.count() >= event.max_participants:
                return JsonResponse({
                    'error': 'Este evento já atingiu o limite máximo de participantes'
                }, status=400)
            
            # Verificar alunos
            from core.models import User
            students = User.objects.filter(id__in=student_ids, user_type='STUDENT')
            
            if len(students) != len(student_ids):
                return JsonResponse({'error': 'Um ou mais alunos não encontrados'}, status=400)
            
            # Adicionar alunos como participantes
            participants_added = []
            for student in students:
                participant, created = EventParticipant.objects.get_or_create(
                    event=event,
                    student=student,
                    defaults={'attendance_status': 'PENDING'}
                )
                
                # Se o participante já existia mas estava cancelado, reativar
                if not created and participant.attendance_status == 'CANCELLED':
                    participant.attendance_status = 'PENDING'
                    participant.save()
                
                participants_added.append({
                    'id': participant.id,
                    'student_id': student.id,
                    'name': student.get_full_name() or student.email,
                    'email': student.email,
                    'status': participant.attendance_status,
                    'created': created
                })
                
                # TODO: Enviar notificação para o aluno
            
            return JsonResponse({
                'message': f'{len(participants_added)} participante(s) adicionado(s) com sucesso',
                'participants': participants_added
            })
        
        elif request.method == 'DELETE':
            # Remover participante
            data = json.loads(request.body)
            student_id = data.get('student_id')
            
            if not student_id:
                return JsonResponse({'error': 'ID do aluno é obrigatório'}, status=400)
            
            try:
                participant = EventParticipant.objects.get(event=event, student_id=student_id)
                participant.delete()
                return JsonResponse({'message': 'Participante removido com sucesso'})
            except EventParticipant.DoesNotExist:
                return JsonResponse({'error': 'Participante não encontrado'}, status=404)
        
        elif request.method == 'PATCH':
            # Atualizar status de um participante
            data = json.loads(request.body)
            student_id = data.get('student_id')
            status = data.get('status')
            
            if not student_id or not status:
                return JsonResponse({'error': 'ID do aluno e status são obrigatórios'}, status=400)
            
            try:
                participant = EventParticipant.objects.get(event=event, student_id=student_id)
                
                # Verificar se o status é válido
                if status not in [choice[0] for choice in EventParticipant.ATTENDANCE_STATUS_CHOICES]:
                    return JsonResponse({'error': 'Status inválido'}, status=400)
                
                participant.attendance_status = status
                
                # Se o status for CONFIRMED, registre a data/hora
                if status == 'CONFIRMED' and not participant.confirmed_at:
                    participant.confirmed_at = timezone.now()
                
                participant.save()
                
                return JsonResponse({
                    'message': 'Status atualizado com sucesso',
                    'participant': {
                        'id': participant.id,
                        'status': participant.attendance_status,
                        'confirmed_at': participant.confirmed_at.isoformat() if participant.confirmed_at else None
                    }
                })
            except EventParticipant.DoesNotExist:
                return JsonResponse({'error': 'Participante não encontrado'}, status=404)
        
        else:
            return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# API para confirmar presença (para alunos)
@login_required
def api_confirm_attendance(request, event_id):
    """API para que alunos confirmem ou cancelem sua presença em um evento."""
    try:
        event = get_object_or_404(Event, pk=event_id)
        
        # Verificar se o usuário é um aluno
        if request.user.user_type != 'STUDENT':
            return JsonResponse({'error': 'Apenas alunos podem confirmar presença'}, status=403)
        
        # Verificar se o aluno é participante do evento
        try:
            participant = EventParticipant.objects.get(event=event, student=request.user)
        except EventParticipant.DoesNotExist:
            return JsonResponse({'error': 'Você não está convidado para este evento'}, status=404)
        
        if request.method == 'POST':
            data = json.loads(request.body)
            status = data.get('status', 'CONFIRMED')
            
            # Apenas permitir que o aluno defina como confirmado ou cancelado
            if status not in ['CONFIRMED', 'CANCELLED']:
                return JsonResponse({'error': 'Status inválido'}, status=400)
            
            participant.attendance_status = status
            
            if status == 'CONFIRMED':
                participant.confirmed_at = timezone.now()
            
            participant.save()
            
            return JsonResponse({
                'message': 'Presença confirmada com sucesso',
                'status': participant.attendance_status,
                'confirmed_at': participant.confirmed_at.isoformat() if participant.confirmed_at else None
            })
        
        else:
            return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# API para obter notificações de eventos para um aluno
@login_required
def api_student_event_notifications(request):
    """API para alunos verem notificações de eventos pendentes."""
    try:
        # Verificar se o usuário é um aluno
        if request.user.user_type != 'STUDENT':
            return JsonResponse({'error': 'Apenas alunos podem acessar esta API'}, status=403)
        
        # Buscar convites pendentes para o aluno
        pending_invitations = EventParticipant.objects.filter(
            student=request.user,
            attendance_status='PENDING',
            event__start_time__gt=timezone.now()  # Apenas eventos futuros
        ).select_related('event', 'event__professor', 'event__location', 'event__course')
        
        invitations = []
        for invitation in pending_invitations:
            event = invitation.event
            invitations.append({
                'id': invitation.id,
                'event_id': event.id,
                'title': event.title,
                'start_time': event.start_time.isoformat(),
                'end_time': event.end_time.isoformat(),
                'professor': event.professor.get_full_name() or event.professor.email,
                'location': event.location.name if event.location else 'Sem local definido',
                'course': event.course.title if event.course else None,
                'event_type': event.event_type
            })
        
        return JsonResponse({
            'count': len(invitations),
            'invitations': invitations
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
