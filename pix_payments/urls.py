from django.urls import path
from . import views

app_name = 'pix_payments'

urlpatterns = [
    path('create/<int:course_id>/', views.create_pix_payment, name='create_payment'),
    path('detail/<int:payment_id>/', views.payment_detail, name='payment_detail'),
    path('webhook/', views.webhook, name='webhook'),
]
