from django.urls import path, include
from django.views.generic.base import RedirectView
from . import views
from . import student_views
from . import api

app_name = 'courses'

# URLs específicas para estudantes
student_patterns = [
    path('dashboard/', student_views.StudentDashboardView.as_view(), name='dashboard'),
    path('catalog/', student_views.CourseListView.as_view(), name='course_list'),
    path('course/<int:pk>/', student_views.CourseDetailView.as_view(), name='course_detail'),
    path('course/<int:pk>/enroll/', student_views.CourseEnrollView.as_view(), name='course_enroll'),
    path('course/<int:pk>/learn/', student_views.CourseLearnView.as_view(), name='course_learn'),
    path('course/<int:pk>/cancel/', student_views.EnrollmentCancelView.as_view(), name='enrollment_cancel'),
    path('course/<int:course_id>/lesson/<int:lesson_id>/complete/', 
         student_views.LessonCompleteView.as_view(), name='lesson_complete'),
    path('class-group/<int:pk>/', student_views.ClassGroupDetailView.as_view(), name='class_group_detail'),
]

urlpatterns = [
    # Dashboard do professor
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Cursos - Professor
    path('', views.CourseListView.as_view(), name='course_list'),
    path('create/', views.CourseCreateView.as_view(), name='course_create'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('<int:pk>/update/', views.CourseUpdateView.as_view(), name='course_update'),
    path('<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('<int:pk>/publish/', views.CoursePublishView.as_view(), name='course_publish'),
    
    # Aulas - Professor
    path('<int:course_id>/lessons/create/', views.LessonCreateView.as_view(), name='lesson_create'),
    path('lesson/<int:pk>/update/', views.LessonUpdateView.as_view(), name='lesson_update'),
    path('lesson/<int:pk>/delete/', views.LessonDeleteView.as_view(), name='lesson_delete'),
    
    # Redirecionamentos para URLs legadas (para compatibilidade)
    path('lessons/<int:pk>/update/', RedirectView.as_view(pattern_name='courses:lesson_update'), name='legacy_lesson_update'),
    path('lessons/<int:pk>/delete/', RedirectView.as_view(pattern_name='courses:lesson_delete'), name='legacy_lesson_delete'),
    
    # Alunos - Incluir submódulo de URLs
    path('student/', include((student_patterns, 'student'))),
    
    # APIs
    path('api/professor-courses/', views.api_professor_courses, name='api_professor_courses'),
    
    # APIs de progresso de vídeo
    path('api/video-progress/update/', api.update_video_progress, name='api_update_video_progress'),
    path('api/video-progress/<int:lesson_id>/', api.get_video_progress, name='api_get_video_progress'),
    path('api/course-progress/<int:course_id>/', api.get_course_video_progress, name='api_course_progress'),
    
    # Rotas para turmas (Class Groups)
    path('class-groups/', views.ClassGroupListView.as_view(), name='class_group_list'),
    path('class-groups/create/', views.ClassGroupCreateView.as_view(), name='class_group_create'),
    path('class-groups/<int:pk>/', views.ClassGroupDetailView.as_view(), name='class_group_detail'),
    path('class-groups/<int:pk>/update/', views.ClassGroupUpdateView.as_view(), name='class_group_update'),
    path('class-groups/<int:pk>/delete/', views.ClassGroupDeleteView.as_view(), name='class_group_delete'),
    
    # Rotas para liberação de aulas (Lesson Releases)
    path('class-groups/<int:class_group_id>/lesson-release/create/', 
         views.LessonReleaseCreateView.as_view(), 
         name='lesson_release_create'),
    path('lesson-release/<int:pk>/update/', 
         views.LessonReleaseUpdateView.as_view(), 
         name='lesson_release_update'),
    path('lesson-release/<int:pk>/delete/', 
         views.LessonReleaseDeleteView.as_view(), 
         name='lesson_release_delete'),
]
