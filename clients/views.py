from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from courses.views import ProfessorRequiredMixin
from .models import Client, IndividualClient, CompanyClient
from .forms import ClientRegistrationForm, ClientForm, IndividualClientForm, CompanyClientForm


class ClientListView(LoginRequiredMixin, ProfessorRequiredMixin, ListView):
    """
    Lista de clientes cadastrados pelo professor
    """
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20
    
    def get_queryset(self):
        """Retorna apenas clientes do professor logado"""
        queryset = Client.objects.filter(professor=self.request.user)
        
        # Filtros por tipo de cliente
        client_type = self.request.GET.get('client_type')
        if client_type and client_type in dict(Client.Type.choices):
            queryset = queryset.filter(client_type=client_type)
            
        # Busca por nome, email, cpf ou cnpj
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(individual__full_name__icontains=search) |
                Q(individual__cpf__icontains=search) |
                Q(company__company_name__icontains=search) |
                Q(company__trade_name__icontains=search) |
                Q(company__cnpj__icontains=search)
            ).distinct()
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adicionar contadores para filtros
        context['total_clients'] = Client.objects.filter(
            professor=self.request.user
        ).count()
        context['individual_count'] = Client.objects.filter(
            professor=self.request.user, 
            client_type=Client.Type.INDIVIDUAL
        ).count()
        context['company_count'] = Client.objects.filter(
            professor=self.request.user,
            client_type=Client.Type.COMPANY
        ).count()
        
        # Parâmetros de filtro atuais
        context['client_type'] = self.request.GET.get('client_type', '')
        context['search'] = self.request.GET.get('search', '')
        
        # Verificar URLs disponíveis para integrações
        available_urls = []
        try:
            from django.urls import NoReverseMatch
            # Verificar se a URL para emissão de nota fiscal existe
            try:
                reverse('invoices:emit')
                available_urls.append('invoices:emit')
            except NoReverseMatch:
                pass
        except ImportError:
            pass
        
        context['available_urls'] = available_urls
        
        return context


class IndividualClientRegistrationView(LoginRequiredMixin, ProfessorRequiredMixin, View):
    """
    Formulário específico para cadastro de clientes pessoa física
    """
    template_name = 'clients/individual_client_registration.html'
    
    def get(self, request):
        form = ClientRegistrationForm(initial={'client_type': Client.Type.INDIVIDUAL})
        # Remover os campos específicos para pessoa jurídica
        form.fields.pop('company_name', None)
        form.fields.pop('trade_name', None)
        form.fields.pop('cnpj', None)
        form.fields.pop('state_registration', None)
        form.fields.pop('municipal_registration', None)
        form.fields.pop('responsible_name', None)
        form.fields.pop('responsible_cpf', None)
        
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        # Forçar o tipo para pessoa física
        post_data = request.POST.copy()
        post_data['client_type'] = Client.Type.INDIVIDUAL
        
        form = ClientRegistrationForm(post_data, professor=request.user)
        if form.is_valid():
            client, specific = form.save()
            messages.success(
                request, 
                _('Cliente pessoa física cadastrado com sucesso!')
            )
            return redirect('clients:client_detail', pk=client.pk)
        return render(request, self.template_name, {'form': form})


class CompanyClientRegistrationView(LoginRequiredMixin, ProfessorRequiredMixin, View):
    """
    Formulário específico para cadastro de clientes pessoa jurídica
    """
    template_name = 'clients/company_client_registration.html'
    
    def get(self, request):
        form = ClientRegistrationForm(initial={'client_type': Client.Type.COMPANY})
        # Remover os campos específicos para pessoa física
        form.fields.pop('full_name', None)
        form.fields.pop('cpf', None)
        form.fields.pop('rg', None)
        form.fields.pop('birth_date', None)
        
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        # Forçar o tipo para pessoa jurídica
        post_data = request.POST.copy()
        post_data['client_type'] = Client.Type.COMPANY
        
        form = ClientRegistrationForm(post_data, professor=request.user)
        if form.is_valid():
            client, specific = form.save()
            messages.success(
                request, 
                _('Cliente pessoa jurídica cadastrado com sucesso!')
            )
            return redirect('clients:client_detail', pk=client.pk)
        return render(request, self.template_name, {'form': form})


class ClientDetailView(LoginRequiredMixin, ProfessorRequiredMixin, DetailView):
    """
    Exibe detalhes de um cliente
    """
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'
    
    def get_queryset(self):
        """Retorna apenas clientes do professor logado"""
        return Client.objects.filter(professor=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.get_object()
        
        # Adicionar dados específicos conforme o tipo de cliente
        if client.client_type == Client.Type.INDIVIDUAL:
            context['individual'] = getattr(client, 'individual', None)
        elif client.client_type == Client.Type.COMPANY:
            context['company'] = getattr(client, 'company', None)
            
        return context


class ClientUpdateView(LoginRequiredMixin, ProfessorRequiredMixin, View):
    """
    Atualização de cliente com formulário dinâmico
    """
    template_name = 'clients/client_update.html'
    
    def get_client(self):
        """Retorna o cliente a ser editado"""
        return get_object_or_404(
            Client, 
            pk=self.kwargs['pk'], 
            professor=self.request.user
        )
    
    def get(self, request, pk):
        client = self.get_client()
        client_form = ClientForm(instance=client)
        
        # Formulário específico conforme o tipo de cliente
        specific_form = None
        if client.client_type == Client.Type.INDIVIDUAL:
            if hasattr(client, 'individual'):
                specific_form = IndividualClientForm(instance=client.individual)
        elif client.client_type == Client.Type.COMPANY:
            if hasattr(client, 'company'):
                specific_form = CompanyClientForm(instance=client.company)
        
        return render(request, self.template_name, {
            'client': client,
            'client_form': client_form,
            'specific_form': specific_form
        })
    
    def post(self, request, pk):
        client = self.get_client()
        client_form = ClientForm(request.POST, instance=client)
        
        # Formulário específico conforme o tipo de cliente
        specific_form = None
        if client.client_type == Client.Type.INDIVIDUAL:
            if hasattr(client, 'individual'):
                specific_form = IndividualClientForm(
                    request.POST, 
                    instance=client.individual
                )
        elif client.client_type == Client.Type.COMPANY:
            if hasattr(client, 'company'):
                specific_form = CompanyClientForm(
                    request.POST, 
                    instance=client.company
                )
        
        if client_form.is_valid() and (specific_form is None or specific_form.is_valid()):
            client_form.save()
            if specific_form:
                specific_form.save()
            
            messages.success(request, _('Cliente atualizado com sucesso!'))
            return redirect('clients:client_detail', pk=client.pk)
        
        return render(request, self.template_name, {
            'client': client,
            'client_form': client_form,
            'specific_form': specific_form
        })


class ClientDeleteView(LoginRequiredMixin, ProfessorRequiredMixin, View):
    """
    Exclui um cliente (seja pessoa física ou jurídica)
    """
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk, professor=request.user)
        
        # Guardar o tipo para mensagem personalizada
        is_company = client.client_type == Client.Type.COMPANY
        
        # Nome para mensagem
        client_name = ""
        if client.client_type == Client.Type.INDIVIDUAL and hasattr(client, 'individual'):
            client_name = client.individual.full_name
        elif client.client_type == Client.Type.COMPANY and hasattr(client, 'company'):
            client_name = client.company.company_name
        
        # Excluir cliente
        client.delete()
        
        if is_company:
            messages.success(request, _(f'Cliente pessoa jurídica "{client_name}" excluído com sucesso!'))
        else:
            messages.success(request, _(f'Cliente pessoa física "{client_name}" excluído com sucesso!'))
        
        return redirect('clients:client_list')


@login_required
@require_GET
def api_company_clients(request):
    """
    API endpoint to fetch company clients for the logged-in professor
    Returns JSON data with company information
    """
    if not hasattr(request.user, 'is_professor') or not request.user.is_professor:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Fetch company clients for this professor
    companies = CompanyClient.objects.filter(
        client__professor=request.user
    ).select_related('client')
    
    # Format the data
    company_data = []
    for company in companies:
        company_data.append({
            'id': company.id,
            'company_name': company.company_name,
            'trade_name': company.trade_name,
            'cnpj': company.cnpj,
            'email': company.client.email,
            'phone': company.client.phone,
            'address': company.client.address,
            'address_number': company.client.address_number,
            'address_complement': company.client.address_complement,
            'neighborhood': company.client.neighborhood,
            'city': company.client.city,
            'state': company.client.state,
            'zipcode': company.client.zipcode,
            'responsible_name': company.responsible_name,
            'responsible_cpf': company.responsible_cpf,
        })
    
    return JsonResponse({'companies': company_data})
