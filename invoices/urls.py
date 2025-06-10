from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    # URLs para professores
    path('settings/', views.company_settings, name='company_settings'),
    
    # URLs para emissão de notas fiscais
    path('emit/<int:transaction_id>/', views.emit_invoice, name='emit'),
    path('emit-sale/<int:sale_id>/', views.emit_singlesale_invoice, name='emit_sale'),
    path('retry/<int:invoice_id>/', views.retry_invoice, name='retry'),
    path('check-status/<int:invoice_id>/', views.check_invoice_status, name='check_status'),
    path('check-status/<int:invoice_id>/json/', views.check_invoice_status, {'format': 'json'}, name='check_status_json'),
    path('cancel/<int:invoice_id>/', views.cancel_invoice, name='cancel'),
    path('delete/<int:invoice_id>/', views.delete_invoice, name='delete'),
    path('transaction/<int:transaction_id>/status/', views.transaction_invoice_status, name='transaction_status'),
    path('sync/<int:invoice_id>/', views.sync_invoice_status, name='sync_status'),
    path('retry-waiting/', views.retry_waiting_invoices, name='retry_waiting'),
    path('test-mode/', views.test_mode, name='test_mode'),
    
    # URLs para visualização de notas fiscais
    path('detail/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('detail/<int:invoice_id>/json/', views.invoice_detail_json, name='invoice_detail_json'),
    path('view_pdf/<int:invoice_id>/', views.view_pdf, name='view_pdf'),
    path('pdf/<str:invoice_id>/', views.download_pdf, name='download_pdf'),
    
    # URLs para boletos bancários
    path('boleto/generate/<int:invoice_id>/', views.generate_boleto, name='generate_boleto'),
    path('boleto/send/<int:boleto_id>/', views.send_boleto_email, name='send_boleto_email'),
    path('boleto/detail/<int:boleto_id>/', views.boleto_detail, name='boleto_detail'),
    path('boleto/cancel/<int:boleto_id>/', views.cancel_boleto, name='cancel_boleto'),
    path('boleto/pdf/<int:boleto_id>/', views.boleto_pdf, name='boleto_pdf'),
    
    # URLs administrativas
    path('admin/approve/<int:invoice_id>/', views.approve_invoice_manually, name='admin_approve'),
]
