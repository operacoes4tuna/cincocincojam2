from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    # URLs para professores
    path('settings/', views.company_settings, name='company_settings'),
    
    # URLs para emissão de notas fiscais
    path('emit/<int:transaction_id>/', views.emit_invoice, name='emit'),
    path('retry/<int:invoice_id>/', views.retry_invoice, name='retry'),
    path('check-status/<int:invoice_id>/', views.check_invoice_status, name='check_status'),
    path('check-status/<int:invoice_id>/json/', views.check_invoice_status, {'format': 'json'}, name='check_status_json'),
    path('cancel/<int:invoice_id>/', views.cancel_invoice, name='cancel'),
    path('delete/<int:invoice_id>/', views.delete_invoice, name='delete'),
    path('transaction/<int:transaction_id>/status/', views.transaction_invoice_status, name='transaction_invoice_status'),
    
    # URL para visualização de detalhes da nota fiscal
    path('detail/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    
    # URLs para visualizar o PDF da nota fiscal
    path('pdf/<int:invoice_id>/', views.view_pdf, name='view_pdf'),
    path('download-pdf/<str:invoice_id>/', views.download_pdf, name='download_pdf'),
    
    # URL para teste de aprovação manual (apenas para ambiente de desenvolvimento)
    path('approve-manually/<int:invoice_id>/', views.approve_invoice_manually, name='approve_manually'),
    
    # URLs para o modo de teste
    path('test-mode/', views.test_mode, name='test_mode'),
]
