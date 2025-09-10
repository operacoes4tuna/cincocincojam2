from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
import csv
import io

from courses.views import ProfessorRequiredMixin
from .models import Client, IndividualClient, CompanyClient
from .forms import (
    ClientRegistrationForm, ClientForm, IndividualClientForm, 
    CompanyClientForm, CSVUploadForm
)


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
        
        # Adicionar o formulário de upload de CSV
        csv_form = CSVUploadForm()
        
        return render(request, self.template_name, {
            'form': form,
            'csv_form': csv_form
        })
    
    def post(self, request):
        # Verificar se o formulário de upload de CSV foi enviado
        if 'csv_file' in request.FILES:
            csv_form = CSVUploadForm(request.POST, request.FILES)
            if csv_form.is_valid():
                csv_file = request.FILES['csv_file']
                
                # Verificar se é um arquivo CSV
                if not csv_file.name.endswith('.csv'):
                    messages.error(
                        request,
                        _('Por favor, envie um arquivo CSV válido.')
                    )
                    return redirect('clients:individual_client_registration')
                
                # Processar o arquivo CSV
                success_count = 0
                error_count = 0
                
                try:
                    # Decodificar o arquivo com tentativas de diferentes encodings
                    encodings = ['utf-8', 'latin-1', 'cp1252']
                    decoded_content = None
                    
                    for encoding in encodings:
                        try:
                            decoded_content = csv_file.read().decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if decoded_content is None:
                        messages.error(request, _('Não foi possível decodificar o arquivo CSV.'))
                        return redirect('clients:individual_client_registration')
                    
                    # Criar um buffer de memória para manipular o conteúdo do CSV
                    csv_io = io.StringIO(decoded_content)
                    
                    # Detectar o dialeto (delimitador, etc.)
                    try:
                        dialect = csv.Sniffer().sniff(csv_io.read(1024))
                        csv_io.seek(0)
                    except csv.Error:
                        dialect = csv.excel  # usar o dialeto padrão
                        
                    # Ler o arquivo CSV para verificar o cabeçalho e validar os dados
                    reader = csv.DictReader(csv_io, dialect=dialect)
                    
                    # Verificar campos obrigatórios
                    required_fields = [
                        'nome_completo', 'cpf', 'endereco', 'numero', 
                        'bairro', 'cidade', 'estado', 'cep', 'email'
                    ]
                    header_normalized = [h.strip().lower() for h in reader.fieldnames or []]
                    
                    missing_fields = [field for field in required_fields if field not in header_normalized]
                    if missing_fields:
                        messages.error(
                            request,
                            _('O arquivo CSV não contém os campos obrigatórios: {}').format(
                                ', '.join(missing_fields)
                            )
                        )
                        return redirect('clients:individual_client_registration')
                    
                    # Verificar registros para CPFs duplicados no arquivo ou já existentes no banco
                    csv_io.seek(0)
                    next(reader)  # Pular o cabeçalho
                    
                    cpfs = []
                    cpfs_normalizados = []
                    cpf_duplicados_arquivo = set()
                    
                    # Iterar sobre todos os registros e verificar CPFs
                    for row in reader:
                        row_normalized = {k.strip().lower(): v.strip() for k, v in row.items()}
                        cpf_raw = row_normalized.get('cpf', '')
                        
                        if cpf_raw:
                            # Normalizar CPF removendo caracteres não numéricos
                            cpf_digits = ''.join(filter(str.isdigit, cpf_raw))
                            
                            # Verificar se o CPF tem o tamanho correto
                            if len(cpf_digits) == 11:
                                if cpf_digits in cpfs:
                                    cpf_duplicados_arquivo.add(cpf_digits)
                                else:
                                    cpfs.append(cpf_digits)
                                    formatted_cpf = (
                                        f"{cpf_digits[:3]}.{cpf_digits[3:6]}."
                                        f"{cpf_digits[6:9]}-{cpf_digits[9:]}"
                                    )
                                    cpfs_normalizados.append(formatted_cpf)
                    
                    if cpfs_normalizados:
                        cpfs_existentes = list(IndividualClient.objects.filter(
                            cpf__in=cpfs_normalizados
                        ).values_list('cpf', flat=True))
                    
                    # Se houver CPFs duplicados, exibir erro
                    if cpf_duplicados_arquivo:
                        duplicados_formatados = []
                        for cpf in cpf_duplicados_arquivo:
                            if len(cpf) == 11:
                                fmt_cpf = (
                                    f"{cpf[:3]}.{cpf[3:6]}."
                                    f"{cpf[6:9]}-{cpf[9:]}"
                                )
                                duplicados_formatados.append(fmt_cpf)
                            else:
                                duplicados_formatados.append(cpf)
                        
                        msg_sufixo = '...' if len(duplicados_formatados) > 10 else ''
                        duplicados_display = ', '.join(duplicados_formatados[:10])
                        
                        messages.error(
                            request,
                            _('Existem CPFs duplicados no arquivo CSV: {}').format(
                                duplicados_display + msg_sufixo
                            )
                        )
                        return redirect('clients:individual_client_registration')
                    
                    # Se houver CPFs já existentes no banco, exibir erro
                    if cpfs_existentes:
                        msg_sufixo = '...' if len(cpfs_existentes) > 10 else ''
                        cpfs_display = ', '.join(cpfs_existentes[:10])
                        
                        messages.error(
                            request,
                            _('Os seguintes CPFs já estão cadastrados no sistema: {}').format(
                                cpfs_display + msg_sufixo
                            )
                        )
                        return redirect('clients:individual_client_registration')
                    
                    # Voltar ao início do arquivo para processar
                    csv_io.seek(0)
                    reader = csv.DictReader(csv_io, dialect=dialect)
                    
                    # Processar cada linha do CSV
                    error_details = []
                    with transaction.atomic():  # Garante que todas as inserções sejam concluídas ou nenhuma
                        for i, row in enumerate(reader, start=2):  # start=2 para contar a partir da linha 2 (após cabeçalho)
                            try:
                                # Normalizar as chaves do dicionário removendo espaços
                                row_normalized = {k.strip().lower(): v for k, v in row.items()}
                                
                                # Criar o cliente base
                                client = Client(
                                    professor=request.user,
                                    email=row_normalized['email'],
                                    phone=row_normalized.get('telefone', ''),
                                    address=row_normalized['endereco'],
                                    address_number=row_normalized['numero'],
                                    address_complement=row_normalized.get('complemento', ''),
                                    neighborhood=row_normalized['bairro'],
                                    city=row_normalized['cidade'],
                                    state=row_normalized['estado'],
                                    zipcode=row_normalized['cep'],
                                    client_type=Client.Type.INDIVIDUAL
                                )
                                client.save()
                                
                                # Processar data de nascimento se existir
                                birth_date = None
                                if row_normalized.get('data_nascimento'):
                                    try:
                                        from datetime import datetime
                                        date_str = row_normalized['data_nascimento'].strip()
                                        
                                        # Tentar formatos comuns de data
                                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y']:
                                            try:
                                                birth_date = datetime.strptime(date_str, fmt).date()
                                                break
                                            except ValueError:
                                                continue
                                    except Exception:
                                        # Se não conseguir converter a data, deixar como None
                                        pass
                                
                                # Processar CPF - garantir formatação correta
                                cpf = ''
                                if row_normalized.get('cpf'):
                                    cpf_raw = row_normalized['cpf'].strip()
                                    cpf_digits = ''.join(filter(str.isdigit, cpf_raw))
                                    if len(cpf_digits) == 11:
                                        cpf = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
                                    else:
                                        cpf = cpf_raw
                                
                                # Criar o cliente pessoa física
                                individual = IndividualClient(
                                    client=client,
                                    full_name=row_normalized['nome_completo'],
                                    cpf=cpf,
                                    rg=row_normalized.get('rg', ''),
                                    birth_date=birth_date
                                )
                                individual.save()
                                
                                success_count += 1
                            except Exception as e:
                                error_count += 1
                                error_details.append(f"Linha {i}: {str(e)}")
                                # Continuar com a próxima linha em caso de erro
                                continue
                    
                    # Exibir mensagem de sucesso ou erro
                    if success_count > 0:
                        messages.success(
                            request,
                            _('Importação concluída. {} clientes importados com sucesso. {} com erros.').format(
                                success_count, error_count
                            )
                        )
                        if error_details:
                            messages.warning(
                                request, 
                                _('Alguns clientes não foram importados. Detalhes: {}').format(
                                    '; '.join(error_details[:5]) + 
                                    ('...' if len(error_details) > 5 else '')
                                )
                            )
                    else:
                        messages.error(
                            request,
                            _('Nenhum cliente foi importado. Verifique se o formato do arquivo está correto. '
                              'Se o erro persistir, verifique o delimitador (vírgula ou ponto-e-vírgula) '
                              'e se os cabeçalhos estão escritos exatamente como solicitado.')
                        )
                        if error_details:
                            messages.warning(
                                request, 
                                _('Detalhes dos erros: {}').format(
                                    '; '.join(error_details[:5]) + 
                                    ('...' if len(error_details) > 5 else '')
                                )
                            )
                
                except Exception as e:
                    messages.error(
                        request,
                        _('Erro ao processar o arquivo CSV: {}').format(str(e))
                    )
                
                return redirect('clients:client_list')
            else:
                # Se o formulário de CSV é inválido, exibir mensagem de erro
                messages.error(
                    request,
                    _('Por favor, selecione um arquivo CSV válido.')
                )
        
        # Processamento do formulário normal de cadastro
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
            
        # Se chegou aqui, é porque o formulário é inválido
        csv_form = CSVUploadForm()
        return render(request, self.template_name, {
            'form': form,
            'csv_form': csv_form
        })


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
        
        # Tornar campos de empresa obrigatórios
        form.fields['company_name'].required = True
        form.fields['cnpj'].required = True
        
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        # Forçar o tipo para pessoa jurídica
        post_data = request.POST.copy()
        post_data['client_type'] = Client.Type.COMPANY
        
        form = ClientRegistrationForm(post_data, professor=request.user)
        
        # Remover os campos específicos para pessoa física do formulário
        form.fields.pop('full_name', None)
        form.fields.pop('cpf', None)
        form.fields.pop('rg', None)
        form.fields.pop('birth_date', None)
        
        # Tornar campos de empresa obrigatórios
        form.fields['company_name'].required = True
        form.fields['cnpj'].required = True
        
        # Revalidar o formulário após ajustar os campos
        form.full_clean()
        
        if form.is_valid():
            try:
                client, specific = form.save()
                messages.success(
                    request, 
                    'Cliente pessoa jurídica cadastrado com sucesso!'
                )
                return redirect('clients:client_detail', pk=client.pk)
            except Exception as e:
                messages.error(request, 'Ocorreu um erro ao salvar. Por favor, tente novamente.')
        else:
            # Mensagem de erro mais amigável
            messages.error(request, "Por favor, verifique os campos destacados abaixo.")
            
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
    
    @transaction.atomic
    def post(self, request, pk):
        client = self.get_client()
        
        # Adicionar o client_type ao POST data
        post_data = request.POST.copy()
        post_data['client_type'] = client.client_type
        
        client_form = ClientForm(post_data, instance=client)
        
        # Formulário específico conforme o tipo de cliente
        specific_form = None
        if client.client_type == Client.Type.INDIVIDUAL:
            if hasattr(client, 'individual'):
                specific_form = IndividualClientForm(
                    request.POST, 
                    instance=client.individual
                )
            else:
                # Criar nova instância se não existir
                specific_form = IndividualClientForm(request.POST)
        elif client.client_type == Client.Type.COMPANY:
            if hasattr(client, 'company'):
                specific_form = CompanyClientForm(
                    request.POST, 
                    instance=client.company
                )
            else:
                # Criar nova instância se não existir
                specific_form = CompanyClientForm(request.POST)
        
        # Verificar validação
        client_form_valid = client_form.is_valid()
        specific_form_valid = specific_form is None or specific_form.is_valid()
        
        # Debugar erros de validação
        if not client_form_valid:
            print(f"Erros no formulário principal: {client_form.errors}")
        
        if specific_form is not None and not specific_form.is_valid():
            print(f"Erros no formulário específico: {specific_form.errors}")
        
        # Se ambos válidos, salvar
        if client_form_valid and specific_form_valid:
            try:
                # Salvar client primeiro
                saved_client = client_form.save()
                
                # Salvar modelo específico ligado ao client
                if specific_form:
                    if client.client_type == Client.Type.INDIVIDUAL:
                        # Checar se já existe
                        if hasattr(client, 'individual'):
                            # Atualiza modelo existente
                            individual = specific_form.save(commit=False)
                            individual.client = saved_client
                            individual.save()
                        else:
                            # Cria novo modelo relacionado
                            individual = specific_form.save(commit=False)
                            individual.client = saved_client
                            individual.save()
                    
                    elif client.client_type == Client.Type.COMPANY:
                        # Checar se já existe
                        if hasattr(client, 'company'):
                            # Atualiza modelo existente
                            company = specific_form.save(commit=False)
                            company.client = saved_client
                            company.save()
                        else:
                            # Cria novo modelo relacionado
                            company = specific_form.save(commit=False)
                            company.client = saved_client
                            company.save()
                
                # Sucesso - redirecionar para página de detalhes
                messages.success(request, _('Cliente atualizado com sucesso!'))
                return redirect('clients:client_detail', pk=saved_client.pk)
                
            except Exception as e:
                print(f"Erro ao salvar cliente: {str(e)}")
                messages.error(request, _('Erro ao atualizar cliente: ') + str(e))
        
        # Se chegou aqui, houve erros - mostrar formulário novamente
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


@login_required
def download_csv_template(request):
    """
    View para download de um arquivo CSV modelo para importação de clientes
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="modelo_clientes.csv"'
    
    # Criar o writer CSV com delimitador de ponto-e-vírgula (mais comum no Brasil)
    writer = csv.writer(response, delimiter=';')
    
    # Escrever cabeçalhos
    writer.writerow([
        'nome_completo', 'cpf', 'email', 'endereco', 'numero',
        'bairro', 'cidade', 'estado', 'cep', 'telefone',
        'complemento', 'rg', 'data_nascimento'
    ])
    
    # Escrever linha de exemplo
    writer.writerow([
        'João da Silva', '123.456.789-00', 'joao@exemplo.com',
        'Rua das Flores', '123', 'Centro', 'São Paulo', 'SP',
        '01234-567', '(11) 98765-4321', 'Apto 42', '12.345.678-9',
        '31/12/1980'
    ])
    
    return response
