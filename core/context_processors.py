from .models import ModulePermission

def module_permissions(request):
    """
    Adiciona as permissões de módulo do usuário atual ao contexto global.
    """
    context = {
        'has_dashboard_access': False,
        'has_agenda_access': False,
        'has_cursos_access': False,
        'has_financas_access': False,
        'has_clientes_access': False,
    }
    
    # Verifica se o usuário está autenticado
    if request.user.is_authenticated:
        # Administradores têm acesso a tudo
        if request.user.is_admin:
            context.update({
                'has_dashboard_access': True,
                'has_agenda_access': True,
                'has_cursos_access': True,
                'has_financas_access': True,
                'has_clientes_access': True,
            })
        # Para professores, verifica as permissões específicas
        elif request.user.is_professor:
            # Obtém todas as permissões do usuário
            user_permissions = ModulePermission.objects.filter(
                user=request.user,
                has_access=True
            ).values_list('module', flat=True)
            
            # Atualiza o contexto com base nas permissões
            context.update({
                'has_dashboard_access': 'DASHBOARD' in user_permissions,
                'has_agenda_access': 'AGENDA' in user_permissions,
                'has_cursos_access': 'CURSOS' in user_permissions,
                'has_financas_access': 'FINANCAS' in user_permissions,
                'has_clientes_access': 'CLIENTES' in user_permissions,
            })
        # Alunos têm acesso apenas a seus próprios módulos
        elif request.user.is_student:
            context.update({
                'has_agenda_access': True,
                'has_cursos_access': True,
                'has_financas_access': True,
            })
    
    return context