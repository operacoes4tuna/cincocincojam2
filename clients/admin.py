from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Client, IndividualClient, CompanyClient


class IndividualClientInline(admin.StackedInline):
    model = IndividualClient
    can_delete = False
    verbose_name = _('Informações de Pessoa Física')
    verbose_name_plural = _('Informações de Pessoa Física')
    
    
class CompanyClientInline(admin.StackedInline):
    model = CompanyClient
    can_delete = False
    verbose_name = _('Informações de Pessoa Jurídica')
    verbose_name_plural = _('Informações de Pessoa Jurídica')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'client_type', 'email', 'phone', 'city', 
                    'professor', 'created_at')
    list_filter = ('client_type', 'city', 'state', 'professor')
    search_fields = ('email', 'individual__full_name', 'company__company_name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    
    def get_inlines(self, request, obj=None):
        """Retorna os inlines apropriados com base no tipo de cliente"""
        if obj is None:
            return []
        if obj.client_type == Client.Type.INDIVIDUAL:
            return [IndividualClientInline]
        elif obj.client_type == Client.Type.COMPANY:
            return [CompanyClientInline]
        return []
    
    def client_name(self, obj):
        """Retorna o nome do cliente, seja pessoa física ou jurídica"""
        if hasattr(obj, 'individual'):
            return obj.individual.full_name
        elif hasattr(obj, 'company'):
            return obj.company.company_name
        return _('Cliente sem nome')
    client_name.short_description = _('Nome do Cliente')
    
    def save_model(self, request, obj, form, change):
        """Salva o usuário logado como professor, se não especificado"""
        if not obj.professor_id and hasattr(request.user, 'is_professor'):
            if request.user.is_professor:
                obj.professor = request.user
        super().save_model(request, obj, form, change)


@admin.register(IndividualClient)
class IndividualClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'cpf', 'get_email', 'get_phone', 'get_professor')
    search_fields = ('full_name', 'cpf', 'client__email')
    list_filter = ('client__professor', 'client__city', 'client__state')
    raw_id_fields = ('client',)
    
    def get_email(self, obj):
        return obj.client.email
    get_email.short_description = _('Email')
    
    def get_phone(self, obj):
        return obj.client.phone
    get_phone.short_description = _('Telefone')
    
    def get_professor(self, obj):
        return obj.client.professor
    get_professor.short_description = _('Professor')


@admin.register(CompanyClient)
class CompanyClientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'trade_name', 'cnpj', 
                    'get_email', 'get_phone', 'get_professor')
    search_fields = ('company_name', 'trade_name', 'cnpj', 'client__email')
    list_filter = ('client__professor', 'client__city', 'client__state')
    raw_id_fields = ('client',)
    
    def get_email(self, obj):
        return obj.client.email
    get_email.short_description = _('Email')
    
    def get_phone(self, obj):
        return obj.client.phone
    get_phone.short_description = _('Telefone')
    
    def get_professor(self, obj):
        return obj.client.professor
    get_professor.short_description = _('Professor')
