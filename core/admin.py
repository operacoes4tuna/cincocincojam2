from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, ModulePermission


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Configuração da interface de administração para o modelo User personalizado.
    """
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_active', 'is_staff')
    list_filter = ('user_type', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = ('last_login',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informações Pessoais'), {'fields': ('first_name', 'last_name', 'user_type', 'bio', 'profile_image')}),
        (_('Permissões'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Datas Importantes'), {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type', 'first_name', 'last_name', 'is_staff', 'is_superuser'),
        }),
    )


class ModulePermissionInline(admin.TabularInline):
    """
    Inline para exibir e editar permissões de módulos diretamente na página de edição do usuário.
    """
    model = ModulePermission
    extra = 1
    verbose_name = _('Permissão de Módulo')
    verbose_name_plural = _('Permissões de Módulos')


# Adiciona o inline de permissões de módulos ao admin de usuários para professores
UserAdmin.inlines = [ModulePermissionInline]


@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo ModulePermission.
    """
    list_display = ('user', 'module', 'has_access', 'updated_at')
    list_filter = ('module', 'has_access', 'user__user_type')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    ordering = ('user__email', 'module')
    list_editable = ('has_access',)
    
    fieldsets = (
        (None, {'fields': ('user', 'module', 'has_access')}),
    )
    
    def get_queryset(self, request):
        # Filtra apenas usuários do tipo professor
        return super().get_queryset(request).filter(user__user_type=User.Types.PROFESSOR)
