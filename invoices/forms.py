from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from .models import CompanyConfig

# Validadores
cnpj_validator = RegexValidator(
    regex=r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',
    message=_('Digite um CNPJ válido no formato XX.XXX.XXX/XXXX-XX')
)

cep_validator = RegexValidator(
    regex=r'^\d{5}-\d{3}$',
    message=_('Digite um CEP válido no formato XXXXX-XXX')
)

class CompanyConfigForm(forms.ModelForm):
    """
    Formulário para configuração dos dados da empresa do professor para emissão de notas fiscais.
    """
    class Meta:
        model = CompanyConfig
        fields = [
            'enabled', 'cnpj', 'razao_social', 'nome_fantasia', 'inscricao_municipal',
            'regime_tributario', 'endereco', 'numero', 'complemento', 'bairro',
            'municipio', 'uf', 'cep', 'telefone', 'email', 'city_service_code',
            'rps_serie', 'rps_numero_atual', 'rps_lote'
        ]
        widgets = {
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-control'}),
            'regime_tributario': forms.Select(attrs={'class': 'form-select'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'municipio': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'city_service_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0107'}),
            'rps_serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'rps_numero_atual': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'rps_lote': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Torna os campos opcionais se o enabled for False
        if not self.instance.enabled and 'enabled' in self.fields:
            for field_name, field in self.fields.items():
                if field_name != 'enabled':
                    field.required = False
                    
    def clean_cnpj(self):
        """
        Validar e formatar o CNPJ, removendo pontuação e verificando o comprimento.
        """
        cnpj = self.cleaned_data.get('cnpj', '')
        # Remover formatação
        cnpj_digits_only = cnpj.replace('.', '').replace('/', '').replace('-', '')
        
        # Verificar se o CNPJ tem 14 dígitos
        if len(cnpj_digits_only) != 14:
            raise forms.ValidationError('CNPJ deve conter 14 dígitos.')
        
        # Verificar se é apenas números
        if not cnpj_digits_only.isdigit():
            raise forms.ValidationError('CNPJ deve conter apenas números.')
        
        return cnpj_digits_only

    def clean(self):
        cleaned_data = super().clean()
        enabled = cleaned_data.get('enabled')
        
        # Se a emissão de NF estiver habilitada, verifica se todos os campos obrigatórios estão preenchidos
        if enabled:
            required_fields = [
                'cnpj', 'razao_social', 'regime_tributario', 
                'endereco', 'numero', 'bairro', 'municipio', 'uf', 'cep',
                'city_service_code'
            ]
            
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _('Este campo é obrigatório quando a emissão de nota fiscal está habilitada.'))
                    
        return cleaned_data
