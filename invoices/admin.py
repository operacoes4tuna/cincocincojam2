from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import CompanyConfig, Invoice, MunicipalServiceCode, BoletoBancario

class MunicipalServiceCodeInline(admin.TabularInline):
    model = MunicipalServiceCode
    extra = 1

@admin.register(CompanyConfig)
class CompanyConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'razao_social', 'cnpj', 'enabled', 'is_complete', 'created_at')
    list_filter = ('enabled', 'regime_tributario', 'uf', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'razao_social', 'cnpj')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Usuário'), {
            'fields': ('user', 'enabled')
        }),
        (_('Dados da Empresa'), {
            'fields': ('cnpj', 'razao_social', 'nome_fantasia', 'regime_tributario')
        }),
        (_('Endereço'), {
            'fields': ('endereco', 'numero', 'complemento', 'bairro', 'municipio', 'uf', 'cep')
        }),
        (_('Contato'), {
            'fields': ('telefone', 'email')
        }),
        (_('Configurações Fiscais'), {
            'fields': ('inscricao_municipal', 'city_service_code')
        }),
        (_('RPS'), {
            'fields': ('rps_serie', 'rps_numero_atual', 'rps_lote')
        }),
        (_('Controle'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [MunicipalServiceCodeInline]
    
    def is_complete(self, obj):
        return obj.is_complete()
    is_complete.boolean = True
    is_complete.short_description = _('Configuração completa')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_customer_name', 'get_amount', 'status', 'type', 'created_at', 'emitted_at')
    list_filter = ('status', 'type', 'created_at', 'emitted_at')
    search_fields = ('customer_name', 'customer_email', 'external_id', 'focus_reference', 'description')
    readonly_fields = ('created_at', 'updated_at', 'emitted_at', 'response_data')
    
    fieldsets = (
        (_('Relacionamentos'), {
            'fields': ('transaction', 'singlesale')
        }),
        (_('Dados do Cliente'), {
            'fields': ('customer_name', 'customer_email', 'customer_tax_id', 'description', 'amount')
        }),
        (_('Nota Fiscal'), {
            'fields': ('type', 'status', 'rps_serie', 'rps_numero', 'rps_lote')
        }),
        (_('API Externa'), {
            'fields': ('external_id', 'focus_id', 'focus_reference', 'focus_status', 'focus_message')
        }),
        (_('URLs'), {
            'fields': ('focus_url', 'focus_pdf_url', 'focus_xml_url')
        }),
        (_('Controle'), {
            'fields': ('created_at', 'updated_at', 'emitted_at', 'error_message', 'response_data'),
            'classes': ('collapse',)
        })
    )
    
    def get_customer_name(self, obj):
        if obj.transaction:
            return f"{obj.transaction.enrollment.student.first_name} {obj.transaction.enrollment.student.last_name}"
        elif obj.singlesale:
            return obj.singlesale.customer_name
        return obj.customer_name or '-'
    get_customer_name.short_description = _('Cliente')
    
    def get_amount(self, obj):
        if obj.transaction:
            return obj.transaction.amount
        elif obj.singlesale:
            return obj.singlesale.amount
        return obj.amount
    get_amount.short_description = _('Valor')

@admin.register(BoletoBancario)
class BoletoBancarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero_documento', 'get_invoice_id', 'get_customer_name', 'valor_documento', 'data_vencimento', 'status', 'created_at')
    list_filter = ('status', 'data_vencimento', 'data_emissao', 'banco_codigo', 'created_at')
    search_fields = ('numero_documento', 'nosso_numero', 'invoice__customer_name', 'invoice__external_id')
    readonly_fields = ('created_at', 'updated_at', 'codigo_barras', 'linha_digitavel')
    date_hierarchy = 'data_vencimento'
    
    fieldsets = (
        (_('Relacionamento'), {
            'fields': ('invoice',)
        }),
        (_('Dados do Boleto'), {
            'fields': ('numero_documento', 'nosso_numero', 'codigo_barras', 'linha_digitavel')
        }),
        (_('Valores'), {
            'fields': ('valor_documento', 'valor_juros', 'valor_multa')
        }),
        (_('Datas'), {
            'fields': ('data_emissao', 'data_vencimento', 'data_pagamento')
        }),
        (_('Status e Controle'), {
            'fields': ('status',)
        }),
        (_('Dados Bancários'), {
            'fields': ('banco_codigo', 'agencia', 'conta'),
            'classes': ('collapse',)
        }),
        (_('Arquivos e URLs'), {
            'fields': ('url_pdf', 'arquivo_pdf'),
            'classes': ('collapse',)
        }),
        (_('API Externa'), {
            'fields': ('external_id', 'external_data'),
            'classes': ('collapse',)
        }),
        (_('Metadados'), {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        (_('Controle'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_invoice_id(self, obj):
        return f"NFe #{obj.invoice.id}"
    get_invoice_id.short_description = _('Nota Fiscal')
    
    def get_customer_name(self, obj):
        return obj.metadata.get('cliente_nome', 'N/A')
    get_customer_name.short_description = _('Cliente')
    
    actions = ['marcar_como_pago', 'cancelar_boletos']
    
    def marcar_como_pago(self, request, queryset):
        """Marca os boletos selecionados como pagos"""
        count = 0
        for boleto in queryset:
            if boleto.status not in ['paid', 'cancelled']:
                boleto.mark_as_paid()
                count += 1
        
        self.message_user(request, f'{count} boleto(s) marcado(s) como pago(s).')
    marcar_como_pago.short_description = _('Marcar como pago')
    
    def cancelar_boletos(self, request, queryset):
        """Cancela os boletos selecionados"""
        count = 0
        for boleto in queryset:
            if boleto.status not in ['paid', 'cancelled']:
                boleto.cancel()
                count += 1
        
        self.message_user(request, f'{count} boleto(s) cancelado(s).')
    cancelar_boletos.short_description = _('Cancelar boletos')
