from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect

def professor_required(view_func):
    """
    Decorator para verificar se o usuário é um professor.
    Redirecionará para a página de login se o usuário não estiver autenticado.
    Retornará erro 403 se o usuário estiver autenticado mas não for professor.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_professor:
            raise PermissionDenied("Você precisa ser um professor para acessar esta página.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """
    Decorator para verificar se o usuário é um administrador.
    Redirecionará para a página de login se o usuário não estiver autenticado.
    Retornará erro 403 se o usuário estiver autenticado mas não for administrador.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin:
            raise PermissionDenied("Você precisa ser um administrador para acessar esta página.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def student_required(view_func):
    """
    Decorator para verificar se o usuário é um aluno.
    Redirecionará para a página de login se o usuário não estiver autenticado.
    Retornará erro 403 se o usuário estiver autenticado mas não for aluno.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_student:
            raise PermissionDenied("Você precisa ser um aluno para acessar esta página.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
