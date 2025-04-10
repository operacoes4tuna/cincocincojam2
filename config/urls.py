"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.http import HttpResponse
from django.contrib.auth import get_user_model

User = get_user_model()

# View personalizada para redirecionar para o dashboard apropriado com base no tipo de usuário
def dashboard_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('users:dashboard')
        elif request.user.is_professor:
            return redirect('courses:dashboard')
        elif request.user.is_student:
            return redirect('courses:student:course_list')
    return redirect('home')

# View temporária para criar usuários
def setup_users(request):
    """
    Endpoint temporário para criar usuários padrão.
    Acesse com /setup-users/?secret=sua_senha_secreta
    """
    # Proteja esta view com uma senha simples
    secret = request.GET.get('secret')
    if secret != 'setup55jam':  # Altere para uma senha secreta de sua escolha
        return HttpResponse("Acesso negado. Senha secreta incorreta.", status=403)
    
    # Criar superusuário para acesso ao admin Django
    superuser, created = User.objects.get_or_create(
        email='admin@cincocincojam.com',
        defaults={
            'first_name': 'Super',
            'last_name': 'Admin',
            'user_type': 'ADMIN',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        superuser.set_password('admin123')
        superuser.save()
        superuser_status = f"Superusuário criado: {superuser.email}"
    else:
        superuser_status = f"Superusuário já existe: {superuser.email}"

    # Criar usuário Admin regular
    admin, created = User.objects.get_or_create(
        email='admin@example.com',
        defaults={
            'first_name': 'Admin',
            'last_name': 'Sistema',
            'user_type': 'ADMIN',
            'is_staff': True,
            'bio': 'Administrador do sistema'
        }
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        admin_status = f"Admin criado: {admin.email}"
    else:
        admin_status = f"Admin já existe: {admin.email}"

    # Criar usuário Professor
    professor, created = User.objects.get_or_create(
        email='professor@example.com',
        defaults={
            'first_name': 'Professor',
            'last_name': 'Exemplo',
            'user_type': 'PROFESSOR',
            'bio': 'Professor da plataforma'
        }
    )
    if created:
        professor.set_password('prof123')
        professor.save()
        professor_status = f"Professor criado: {professor.email}"
    else:
        professor_status = f"Professor já existe: {professor.email}"

    # Criar usuário Aluno
    aluno, created = User.objects.get_or_create(
        email='aluno@example.com',
        defaults={
            'first_name': 'Aluno',
            'last_name': 'Teste',
            'user_type': 'STUDENT',
            'bio': 'Aluno da plataforma'
        }
    )
    if created:
        aluno.set_password('aluno123')
        aluno.save()
        aluno_status = f"Aluno criado: {aluno.email}"
    else:
        aluno_status = f"Aluno já existe: {aluno.email}"

    # Retornar HTML com informações dos usuários
    html = f"""
    <html>
    <head>
        <title>Usuários configurados</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            h1 {{ color: #2c3e50; }}
            .success {{ color: green; }}
            .info {{ color: blue; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1>Configuração de Usuários Concluída</h1>
        <p><strong class="success">{superuser_status}</strong></p>
        <p><strong class="success">{admin_status}</strong></p>
        <p><strong class="success">{professor_status}</strong></p>
        <p><strong class="success">{aluno_status}</strong></p>
        
        <h2>Informações de Acesso</h2>
        <table>
            <tr>
                <th>Email</th>
                <th>Senha</th>
                <th>Tipo</th>
                <th>Pode acessar admin?</th>
            </tr>
            <tr>
                <td>admin@cincocincojam.com</td>
                <td>admin123</td>
                <td>Superusuário</td>
                <td>Sim</td>
            </tr>
            <tr>
                <td>admin@example.com</td>
                <td>admin123</td>
                <td>Admin</td>
                <td>Sim</td>
            </tr>
            <tr>
                <td>professor@example.com</td>
                <td>prof123</td>
                <td>Professor</td>
                <td>Não</td>
            </tr>
            <tr>
                <td>aluno@example.com</td>
                <td>aluno123</td>
                <td>Aluno</td>
                <td>Não</td>
            </tr>
        </table>
        
        <p class="info">URL do Admin: <a href="/admin/">/admin/</a></p>
        <p class="info">URL da Aplicação: <a href="/">/</a></p>
        
        <h3>Importante!</h3>
        <p>Por motivos de segurança, remova esta view depois de usar.</p>
    </body>
    </html>
    """
    return HttpResponse(html)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),  # Inclui reset de senha e outras URLs de autenticação
    
    # Dashboard redirect
    path('dashboard/', dashboard_redirect, name='dashboard_redirect'),
    
    # User management
    path('users/', include('users.urls')),
    
    # Courses management
    path('courses/', include('courses.urls')),
    
    # Payments management
    path('payments/', include('payments.urls')),
    
    # Assistant
    path('assistant/', include('assistant.urls')),
    
    # Agenda do Professor
    path('agenda/', include('scheduler.urls')),
    
    # Invoices
    path('invoices/', include('invoices.urls')),
    
    # Setup users (endpoint temporário)
    path('setup-users/', setup_users, name='setup_users'),
    
    # Apps Parceiros
    path('apps-parceiros/', TemplateView.as_view(template_name='apps_parceiros.html'), name='apps_parceiros'),
    
    # Home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
