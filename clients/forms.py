from django import forms
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from .models import Client, IndividualClient, CompanyClient

class CSVUploadForm(forms.Form):
    """
    Formulário para upload de arquivo CSV de clientes pessoa física
    """
    csv_file = forms.FileField(
        label=_('Arquivo CSV'),
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    )

class ClientForm(forms.ModelForm):
    """
    Formulário base para clientes
    """
    class Meta:
        model = Client
        fields = [
            'email', 'phone', 'address', 'address_number', 'address_complement',
            'neighborhood', 'city', 'state', 'zipcode', 'client_type'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(11) 98765-4321'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'address_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address_complement': forms.TextInput(attrs={'class': 'form-control'}),
            'neighborhood': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.Select(attrs={'class': 'form-select'}),
            'zipcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),
            'client_type': forms.RadioSelect()
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar todos os campos opcionais exceto client_type
        self.fields['email'].required = False
        self.fields['address'].required = False
        self.fields['address_number'].required = False
        self.fields['neighborhood'].required = False
        self.fields['city'].required = False
        self.fields['state'].required = False
        self.fields['zipcode'].required = False


class IndividualClientForm(forms.ModelForm):
    """
    Formulário para clientes pessoa física
    """
    class Meta:
        model = IndividualClient
        fields = ['full_name', 'cpf', 'rg', 'birth_date']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
            'rg': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar somente o nome obrigatório
        self.fields['cpf'].required = False
        self.fields['rg'].required = False
        self.fields['birth_date'].required = False

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if cpf:
            # Formatar CPF para comparação consistente
            cpf_digits = ''.join(filter(str.isdigit, cpf))
            if len(cpf_digits) == 11:
                formatted_cpf = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
            else:
                formatted_cpf = cpf
            
            # Verificar se já existe no banco, excluindo a instância atual se estiver editando
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                existing = IndividualClient.objects.filter(cpf=formatted_cpf).exclude(pk=instance.pk).exists()
            else:
                existing = IndividualClient.objects.filter(cpf=formatted_cpf).exists()
            
            if existing:
                raise ValidationError(_('Este CPF já está cadastrado no sistema.'))
        
        return cpf


class CompanyClientForm(forms.ModelForm):
    """
    Formulário para clientes pessoa jurídica
    """
    class Meta:
        model = CompanyClient
        fields = [
            'company_name', 'trade_name', 'cnpj',
            'state_registration', 'municipal_registration',
            'responsible_name', 'responsible_cpf'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'trade_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'state_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'municipal_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'responsible_name': forms.TextInput(attrs={'class': 'form-control'}),
            'responsible_cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'})
        }
    
    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')
        if cnpj:
            # Formatar CNPJ para comparação consistente
            cnpj_digits = ''.join(filter(str.isdigit, cnpj))
            if len(cnpj_digits) == 14:
                formatted_cnpj = f"{cnpj_digits[:2]}.{cnpj_digits[2:5]}.{cnpj_digits[5:8]}/{cnpj_digits[8:12]}-{cnpj_digits[12:]}"
            else:
                formatted_cnpj = cnpj
            
            # Verificar se já existe no banco, excluindo a instância atual se estiver editando
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                existing = CompanyClient.objects.filter(cnpj=formatted_cnpj).exclude(pk=instance.pk).exists()
            else:
                existing = CompanyClient.objects.filter(cnpj=formatted_cnpj).exists()
            
            if existing:
                raise ValidationError(_('Este CNPJ já está cadastrado no sistema.'))
        
        return cnpj


class ClientRegistrationForm(forms.Form):
    """
    Formulário combinado que mudará seus campos dependendo do tipo de cliente selecionado
    """
    # Campos do Cliente Base
    client_type = forms.ChoiceField(
        label=_('Tipo de Cliente'),
        choices=Client.Type.choices,
        widget=forms.RadioSelect(attrs={'onchange': 'toggleClientType(this.value)'})
    )
    email = forms.EmailField(
        label=_('Email'),
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        label=_('Telefone'), 
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(11) 98765-4321'})
    )
    
    # Campos de Endereço
    address = forms.CharField(
        label=_('Endereço'),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_number = forms.CharField(
        label=_('Número'),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_complement = forms.CharField(
        label=_('Complemento'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    neighborhood = forms.CharField(
        label=_('Bairro'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    city = forms.CharField(
        label=_('Cidade'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    state = forms.ChoiceField(
        label=_('Estado'),
        required=False,
        choices=[('', 'Selecione...')] + list(Client._meta.get_field('state').choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    zipcode = forms.CharField(
        label=_('CEP'),
        max_length=9,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'})
    )
    
    # Campos de Pessoa Física
    full_name = forms.CharField(
        label=_('Nome Completo'),
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-type': 'individual'})
    )
    cpf = forms.CharField(
        label=_('CPF'),
        max_length=14,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '000.000.000-00',
            'data-type': 'individual'
        })
    )
    rg = forms.CharField(
        label=_('RG (opcional)'),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-type': 'individual'})
    )
    birth_date = forms.DateField(
        label=_('Data de Nascimento'),
        required=False,
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date', 'data-type': 'individual'}
        )
    )
    
    # Campos de Pessoa Jurídica
    company_name = forms.CharField(
        label=_('Razão Social'),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-type': 'company'})
    )
    trade_name = forms.CharField(
        label=_('Nome Fantasia'),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-type': 'company'})
    )
    cnpj = forms.CharField(
        label=_('CNPJ'),
        max_length=18,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '00.000.000/0000-00',
            'data-type': 'company'
        })
    )
    state_registration = forms.CharField(
        label=_('Inscrição Estadual (se aplicável)'),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-type': 'company'})
    )
    municipal_registration = forms.CharField(
        label=_('Inscrição Municipal (se aplicável)'),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-type': 'company'})
    )
    responsible_name = forms.CharField(
        label=_('Nome do Responsável'),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-type': 'company'})
    )
    responsible_cpf = forms.CharField(
        label=_('CPF do Responsável'),
        max_length=14,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '000.000.000-00',
            'data-type': 'company'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.professor = kwargs.pop('professor', None)
        super().__init__(*args, **kwargs)
        
    def clean(self):
        """
        Valida os campos de acordo com o tipo de cliente selecionado
        """
        cleaned_data = super().clean()
        client_type = cleaned_data.get('client_type')
        
        if client_type == Client.Type.INDIVIDUAL:
            # Validar apenas nome como obrigatório para pessoa física
            required_fields = ['full_name']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _('Este campo é obrigatório para pessoa física.'))
            
            # Validar CPF único apenas se for fornecido
            cpf = cleaned_data.get('cpf')
            if cpf:
                # Formatar CPF para comparação consistente - remover todos os caracteres não numéricos
                cpf_digits = ''.join(filter(str.isdigit, cpf))
                
                # Verificar se o CPF tem tamanho válido
                if len(cpf_digits) != 11:
                    self.add_error('cpf', _('CPF deve conter 11 dígitos.'))
                    return cleaned_data
                
                # Formatar para o padrão XXX.XXX.XXX-XX
                formatted_cpf = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
                
                # Substituir o CPF pelo valor formatado
                cleaned_data['cpf'] = formatted_cpf
                
                # Verificar se já existe no banco de dados
                if IndividualClient.objects.filter(cpf=formatted_cpf).exists():
                    self.add_error('cpf', _('Este CPF já está cadastrado no sistema.'))
        
        elif client_type == Client.Type.COMPANY:
            # Validar campos de pessoa jurídica
            required_fields = ['company_name', 'cnpj']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _('Este campo é obrigatório para pessoa jurídica.'))
            
            # Validar CNPJ único
            cnpj = cleaned_data.get('cnpj')
            if cnpj:
                # Formatar CNPJ para comparação consistente
                cnpj_digits = ''.join(filter(str.isdigit, cnpj))
                if len(cnpj_digits) == 14:
                    formatted_cnpj = f"{cnpj_digits[:2]}.{cnpj_digits[2:5]}.{cnpj_digits[5:8]}/"
                    formatted_cnpj += f"{cnpj_digits[8:12]}-{cnpj_digits[12:]}"
                else:
                    formatted_cnpj = cnpj
                
                # Substituir o CNPJ pelo valor formatado
                cleaned_data['cnpj'] = formatted_cnpj
                
                if CompanyClient.objects.filter(cnpj=formatted_cnpj).exists():
                    self.add_error('cnpj', _('Este CNPJ já está cadastrado no sistema.'))
        
        return cleaned_data
    
    @transaction.atomic
    def save(self):
        """
        Salva o cliente e seus dados específicos conforme o tipo selecionado
        """
        client_type = self.cleaned_data['client_type']
        
        # Cria o cliente base
        client = Client(
            professor=self.professor,
            email=self.cleaned_data.get('email', ''),
            phone=self.cleaned_data.get('phone', ''),
            address=self.cleaned_data.get('address', ''),
            address_number=self.cleaned_data.get('address_number', ''),
            address_complement=self.cleaned_data.get('address_complement', ''),
            neighborhood=self.cleaned_data.get('neighborhood', ''),
            city=self.cleaned_data.get('city', ''),
            state=self.cleaned_data.get('state', ''),
            zipcode=self.cleaned_data.get('zipcode', ''),
            client_type=client_type
        )
        client.save()
        
        # Cria os dados específicos conforme o tipo
        if client_type == Client.Type.INDIVIDUAL:
            # Verificar se o CPF já existe antes de criar
            cpf = self.cleaned_data.get('cpf', '')
            if cpf:
                # CPF já formatado pelo método clean()
                if IndividualClient.objects.filter(cpf=cpf).exists():
                    raise ValidationError(_('Este CPF já está cadastrado no sistema.'))
                
            individual = IndividualClient(
                client=client,
                full_name=self.cleaned_data['full_name'],
                cpf=cpf,
                rg=self.cleaned_data.get('rg', ''),
                birth_date=self.cleaned_data.get('birth_date')
            )
            individual.save()
            return client, individual
        
        elif client_type == Client.Type.COMPANY:
            # Verificar se o CNPJ já existe antes de criar
            cnpj = self.cleaned_data.get('cnpj', '')
            if cnpj:
                # CNPJ já formatado pelo método clean()
                if CompanyClient.objects.filter(cnpj=cnpj).exists():
                    raise ValidationError(_('Este CNPJ já está cadastrado no sistema.'))
                
            company = CompanyClient(
                client=client,
                company_name=self.cleaned_data['company_name'],
                trade_name=self.cleaned_data['trade_name'],
                cnpj=cnpj,
                state_registration=self.cleaned_data.get('state_registration', ''),
                municipal_registration=self.cleaned_data.get('municipal_registration', ''),
                responsible_name=self.cleaned_data['responsible_name'],
                responsible_cpf=self.cleaned_data['responsible_cpf']
            )
            company.save()
            return client, company
        
        return client, None 