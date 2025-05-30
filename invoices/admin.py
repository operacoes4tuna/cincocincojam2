from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import CompanyConfig, Invoice, ServiceCode

# Register your models here.

class ServiceCodeInline(admin.TabularInline):
    model = ServiceCode
    extra = 1
    fields = ('code', 'description', 'is_default')
    verbose_name = _('Código de Serviço')
    verbose_name_plural = _('Códigos de Serviço')

@admin.register(ServiceCode)
class ServiceCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'company_config', 'is_default', 'created_at')
    list_filter = ('is_default', 'created_at')
    search_fields = ('code', 'description', 'company_config__user__email', 'company_config__razao_social')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        (_('Informações do Código'), {
            'fields': ('company_config', 'code', 'description', 'is_default')
        }),
        (_('Informações do Sistema'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(CompanyConfig)
class CompanyConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'razao_social', 'cnpj', 'enabled', 'is_complete_status', 'service_codes_count')
    list_filter = ('enabled', 'regime_tributario')
    search_fields = ('user__email', 'razao_social', 'cnpj')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ServiceCodeInline]
    
    fieldsets = (
        (_('Usuário'), {
            'fields': ('user', 'enabled')
        }),
        (_('Dados da Empresa'), {
            'fields': ('cnpj', 'razao_social', 'nome_fantasia', 'inscricao_municipal', 'regime_tributario')
        }),
        (_('Endereço'), {
            'fields': ('endereco', 'numero', 'complemento', 'bairro', 'municipio', 'uf', 'cep')
        }),
        (_('Contato'), {
            'fields': ('telefone', 'email')
        }),
        (_('Configurações Fiscais'), {
            'fields': ('city_service_code', 'rps_serie', 'rps_numero_atual', 'rps_lote'),
            'description': _('O campo "código de serviço municipal (legado)" é mantido para compatibilidade. Use a seção "Códigos de Serviço" abaixo para gerenciar múltiplos códigos.')
        }),
        (_('Informações do Sistema'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_complete_status(self, obj):
        return obj.is_complete()
    is_complete_status.boolean = True
    is_complete_status.short_description = _('Configuração Completa')
    
    def service_codes_count(self, obj):
        return obj.service_codes.count()
    service_codes_count.short_description = _('Qtd. Códigos')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction', 'status', 'created_at', 'emitted_at')
    list_filter = ('status',)
    search_fields = ('transaction__id', 'focus_id')
    readonly_fields = ('transaction', 'status', 'focus_id', 'focus_url', 'focus_pdf_url', 
                      'response_data', 'error_message', 'created_at', 'updated_at', 'emitted_at')
    
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': ('transaction', 'status', 'emitted_at')
        }),
        (_('Referência FocusNFe'), {
            'fields': ('focus_id', 'focus_url', 'focus_pdf_url')
        }),
        (_('Dados Técnicos'), {
            'fields': ('response_data', 'error_message'),
            'classes': ('collapse',)
        }),
        (_('Informações do Sistema'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Desabilita a criação de notas fiscais pelo admin
        return False
