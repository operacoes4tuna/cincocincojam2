from django.urls import path
from . import views
from . import pix_views
from . import card_views

app_name = 'payments'

# URLs para professores
professor_patterns = [
    path('dashboard/', views.ProfessorFinancialDashboardView.as_view(), name='professor_dashboard'),
    path('transactions/', views.ProfessorTransactionListView.as_view(), name='professor_transactions'),
    path('course/<int:course_id>/enrollments/', views.ProfessorCourseEnrollmentListView.as_view(), name='professor_course_enrollments'),
    
    # Novas URLs para gestão de alunos
    path('students/', views.ProfessorStudentListView.as_view(), name='professor_students'),
    path('student/<int:pk>/', views.ProfessorStudentDetailView.as_view(), name='professor_student_detail'),
    
    # URL para emitir cobrança
    path('transaction/<int:transaction_id>/emit-charge/', views.emit_payment_charge, name='emit_payment_charge'),
]

# URLs para administradores
admin_patterns = [
    path('admin/dashboard/', views.AdminFinancialDashboardView.as_view(), name='admin_dashboard'),
    path('admin/transactions/', views.AdminTransactionListView.as_view(), name='admin_transactions'),
    path('admin/professor/<int:pk>/', views.AdminProfessorDetailView.as_view(), name='admin_professor_detail'),
]

# URLs para alunos
student_patterns = [
    path('student/payments/', views.StudentPaymentListView.as_view(), name='student_payments'),
    path('student/enrollment/<int:pk>/', views.StudentEnrollmentDetailView.as_view(), name='student_enrollment_detail'),
]

# URLs para opções de pagamento
payment_options_patterns = [
    path('payment-options/<int:course_id>/', views.payment_options, name='payment_options'),
]

# URLs para pagamentos via Pix
pix_patterns = [
    path('pix/payment/<int:course_id>/', pix_views.create_pix_payment, name='create_pix_payment'),
    path('pix/detail/<int:payment_id>/', pix_views.pix_payment_detail, name='pix_payment_detail'),
    path('pix/webhook/', pix_views.pix_webhook, name='pix_webhook'),
    path('pix/check_status/<int:payment_id>/', pix_views.check_payment_status, name='check_pix_status'),
    path('pix/simulate/<int:payment_id>/', pix_views.simulate_pix_payment, name='simulate_pix_payment'),
]

# URLs para pagamentos com cartão
card_patterns = [
    path('card/create/<int:course_id>/', card_views.create_card_payment, name='create_card_payment'),
    path('card/detail/<int:payment_id>/', card_views.card_payment_detail, name='card_payment_detail'),
    path('card/webhook/', card_views.card_webhook, name='card_webhook'),
    path('card/simulate/<int:payment_id>/', card_views.simulate_card_payment, name='simulate_card_payment'),
]

# URLs para vendas avulsas
singlesale_patterns = [
    path('sales/', views.SingleSaleListView.as_view(), name='singlesale_list'),
    path('sales/new/', views.SingleSaleCreateView.as_view(), name='singlesale_create'),
    path('sales/<int:pk>/', views.SingleSaleDetailView.as_view(), name='singlesale_detail'),
    path('sales/<int:pk>/edit/', views.SingleSaleUpdateView.as_view(), name='singlesale_update'),
    path('sales/<int:sale_id>/pix/create/', views.create_singlesale_pix, name='create_singlesale_pix'),
    path('sales/<int:sale_id>/pix/', views.singlesale_pix_detail, name='singlesale_pix_detail'),
    path('sales/<int:sale_id>/check-status/', views.check_singlesale_payment_status, name='check_singlesale_status'),
    path('admin/sales/', views.SingleSaleAdminListView.as_view(), name='admin_singlesale_list'),
    path('transactions/', views.transaction_list, name='transactions'),
    path('transactions/emit-invoice/<int:transaction_id>/', views.emit_invoice_from_transactions, name='emit_invoice_from_transactions'),
    # Nova URL para API de criação de venda
    path('api/sales/create/', views.create_singlesale_api, name='create_singlesale_api'),
]

urlpatterns = [
    # Incluir todas as URLs
    *professor_patterns,
    *admin_patterns,
    *student_patterns,
    *payment_options_patterns,
    *pix_patterns,
    *card_patterns,
    *singlesale_patterns,
]
