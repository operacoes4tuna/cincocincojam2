from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import CompanyConfig, Invoice, MunicipalServiceCode, InvoicePixPayment

# Register your models here.

class MunicipalServiceCodeInline(admin.TabularInline):
    model = MunicipalServiceCode
    extra = 1


@admin.register(CompanyConfig)
class CompanyConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'razao_social', 'cnpj', 'enabled', 'is_complete_status')
    list_filter = ('enabled', 'regime_tributario')
    search_fields = ('user__email', 'razao_social', 'cnpj')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MunicipalServiceCodeInline]
    
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
        (_('Informações do Sistema'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_complete_status(self, obj):
        return obj.is_complete()
    is_complete_status.boolean = True
    is_complete_status.short_description = _('Configuração Completa')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_customer_name', 'get_amount', 'status', 'type', 'created_at')
    list_filter = ('status', 'type', 'created_at')
    search_fields = ('id', 'customer_name', 'customer_email', 'external_id')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Informações Básicas'), {
            'fields': ('transaction', 'singlesale', 'type', 'status')
        }),
        (_('Dados Diretos (quando aplicável)'), {
            'fields': ('amount', 'customer_name', 'customer_email', 'customer_tax_id', 'description'),
            'classes': ('collapse',)
        }),
        (_('API Externa'), {
            'fields': ('external_id', 'focus_id', 'focus_reference', 'focus_status', 'focus_message', 'focus_url', 'focus_pdf_url', 'focus_xml_url'),
            'classes': ('collapse',)
        }),
        (_('RPS'), {
            'fields': ('rps_serie', 'rps_numero', 'rps_lote'),
            'classes': ('collapse',)
        }),
        (_('Controle e Dados'), {
            'fields': ('response_data', 'focus_data', 'error_message', 'emitted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer_name(self, obj):
        if obj.transaction:
            return obj.transaction.enrollment.student.get_full_name()
        elif obj.singlesale:
            return obj.singlesale.customer_name
        elif obj.customer_name:
            return obj.customer_name
        return "Não informado"
    get_customer_name.short_description = 'Cliente'
    
    def get_amount(self, obj):
        if obj.amount:
            return f"R$ {obj.amount:.2f}"
        elif obj.transaction:
            return f"R$ {obj.transaction.amount:.2f}"
        elif obj.singlesale:
            return f"R$ {obj.singlesale.amount:.2f}"
        return "Não informado"
    get_amount.short_description = 'Valor'


@admin.register(InvoicePixPayment)
class InvoicePixPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'correlation_id', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'expires_at')
    search_fields = ('correlation_id', 'external_id', 'invoice__id')
    readonly_fields = ('created_at', 'updated_at', 'correlation_id')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('invoice', 'correlation_id', 'amount', 'status')
        }),
        ('Dados do Pix', {
            'fields': ('brcode', 'qrcode_image_url', 'qrcode_image_data'),
            'classes': ('collapse',)
        }),
        ('Controle Temporal', {
            'fields': ('expires_at', 'paid_at', 'created_at', 'updated_at')
        }),
        ('API Externa', {
            'fields': ('external_id', 'provider_response', 'error_message'),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # Editando
            readonly.extend(['invoice', 'amount'])
        return readonly


@admin.register(MunicipalServiceCode)
class MunicipalServiceCodeAdmin(admin.ModelAdmin):
    list_display = ('company_config', 'code', 'description')
    list_filter = ('company_config',)
    search_fields = ('code', 'description', 'company_config__razao_social')
