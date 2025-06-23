from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.ClientListView.as_view(), name='client_list'),
    path('cadastro/pessoa-fisica/', views.IndividualClientRegistrationView.as_view(), 
         name='individual_client_registration'),
    path('cadastro/pessoa-juridica/', views.CompanyClientRegistrationView.as_view(), 
         name='company_client_registration'),
    path('<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('<int:pk>/editar/', views.ClientUpdateView.as_view(), name='client_update'),
    path('<int:pk>/excluir/', views.ClientDeleteView.as_view(), name='client_delete'),
    path('api/company-clients/', views.api_company_clients, name='api_company_clients'),
    path('download-csv-template/', views.download_csv_template, name='download_csv_template'),
] 