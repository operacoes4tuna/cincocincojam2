"""
URLs para o aplicativo de agenda do professor.
"""
from django.urls import path
from . import views

app_name = 'scheduler'

urlpatterns = [
    # Visualização principal do calendário
    path('', views.calendar_view, name='calendar'),
    
    # Gerenciamento de eventos
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    
    # Gerenciamento de estúdios
    path('locations/', views.location_list, name='location_list'),
    path('locations/create/', views.location_create, name='location_create'),
    path('locations/<int:pk>/', views.location_detail, name='location_detail'),
    path('locations/<int:pk>/edit/', views.location_edit, name='location_update'),
    path('locations/<int:pk>/delete/', views.location_delete, name='location_delete'),
    
    # Gerenciamento de participantes
    path('events/<int:event_id>/participants/', views.participant_list, name='participant_list'),
    path('events/<int:event_id>/participants/add/', views.add_participant, name='add_participant'),
    
    # Dashboard e Notificações
    path('professor/dashboard/', views.professor_dashboard, name='professor_dashboard'),
    path('student/notifications/', views.student_notifications, name='student_notifications'),
    
    # API para AJAX/Fetch
    path('api/events/', views.api_events, name='api_events'),
    path('api/events/<int:pk>/', views.api_event_detail, name='api_event_detail'),
    path('api/available-slots/', views.api_available_slots, name='api_available_slots'),
    path('api/course-students/', views.api_course_students, name='api_course_students'),
    path('api/events/<int:event_id>/participants/', views.api_manage_participants, name='api_manage_participants'),
    path('api/events/<int:event_id>/confirm/', views.api_confirm_attendance, name='api_confirm_attendance'),
    path('api/student-notifications/', views.api_student_event_notifications, name='api_student_notifications'),
    
    # Visualização do calendário por estúdio
    path('locations/<int:pk>/calendar/', views.LocationCalendarView.as_view(), name='location_calendar'),
    
    # Views baseadas em classes
    path('events/class/list/', views.EventListView.as_view(), name='event_list_view'),
    path('events/class/<int:pk>/', views.EventDetailView.as_view(), name='event_detail_view'),
    path('events/class/create/', views.EventCreateView.as_view(), name='event_create_view'),
    path('events/class/<int:pk>/update/', views.EventUpdateView.as_view(), name='event_update_view'),
    path('events/class/<int:pk>/delete/', views.EventDeleteView.as_view(), name='event_delete_view'),
]
