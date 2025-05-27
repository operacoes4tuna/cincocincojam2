from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from .models import CompanyConfig
import json # Importar json

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
            'city_service_code': forms.HiddenInput(),
            'rps_serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'rps_numero_atual': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'rps_lote': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Passar os códigos de serviço existentes para o template via atributo do widget
        # para que o JavaScript possa reconstruir os campos.
        # O valor inicial do campo oculto já será a string JSON.
        if self.instance and self.instance.pk and self.instance.city_service_code:
            try:
                # O valor já deve ser uma string JSON do modelo
                current_codes_json = self.instance.city_service_code
                # Apenas para garantir que é um JSON válido e passar para o widget
                json.loads(current_codes_json) # testar se é um JSON válido
                self.fields['city_service_code'].widget.attrs['data-initial-codes'] = current_codes_json
            except json.JSONDecodeError:
                # Se não for um JSON válido (ex: dados antigos), usar um valor padrão ou tratar
                self.fields['city_service_code'].widget.attrs['data-initial-codes'] = '["0107"]'
                self.initial['city_service_code'] = '["0107"]'


        if not self.instance.enabled and 'enabled' in self.fields:
            for field_name, field in self.fields.items():
                if field_name != 'enabled':
                    field.required = False
                    
    def clean_cnpj(self):
        """
        Validar e formatar o CNPJ, removendo pontuação e verificando o comprimento.
        """
        cnpj = self.cleaned_data.get('cnpj', '')
        cnpj_digits_only = cnpj.replace('.', '').replace('/', '').replace('-', '')
        
        if len(cnpj_digits_only) != 14:
            raise forms.ValidationError('CNPJ deve conter 14 dígitos.')
        
        if not cnpj_digits_only.isdigit():
            raise forms.ValidationError('CNPJ deve conter apenas números.')
        
        return cnpj_digits_only

    def clean_city_service_code(self):
        # O JavaScript enviará os códigos como uma string JSON através do campo oculto.
        # Aqui, apenas garantimos que seja uma string JSON válida.
        # Se o campo estiver vazio, usamos o default do modelo (lista com '0107')
        codes_json_string = self.cleaned_data.get('city_service_code')
        if not codes_json_string:
            return '["0107"]' # Default como string JSON
        
        try:
            # Validar se é um JSON e se é uma lista de strings
            codes_list = json.loads(codes_json_string)
            if not isinstance(codes_list, list) or not all(isinstance(code, str) for code in codes_list):
                raise forms.ValidationError(_('Formato inválido para códigos de serviço.'))
            if not codes_list: # Não permitir lista vazia, garantir pelo menos um
                 return '["0107"]'
            return codes_json_string # Retorna a string JSON para ser salva no TextField
        except json.JSONDecodeError:
            raise forms.ValidationError(_('Códigos de serviço devem estar em formato JSON válido.'))


    def clean(self):
        cleaned_data = super().clean()
        enabled = cleaned_data.get('enabled')
        
        if enabled:
            required_fields = [
                'cnpj', 'razao_social', 'regime_tributario', 
                'endereco', 'numero', 'bairro', 'municipio', 'uf', 'cep',
                'city_service_code' 
            ]
            
            city_service_code_value = cleaned_data.get('city_service_code')
            # Para city_service_code, verificar se a lista JSON não está vazia após o clean específico
            if city_service_code_value:
                try:
                    codes = json.loads(city_service_code_value)
                    if not codes: # Se a lista estiver vazia
                         self.add_error('city_service_code', _('Pelo menos um código de serviço é obrigatório quando a emissão está habilitada.'))
                except json.JSONDecodeError:
                     self.add_error('city_service_code', _('Formato inválido para códigos de serviço.'))


            for field in required_fields:
                if field == 'city_service_code': # Já tratado acima
                    continue
                if not cleaned_data.get(field):
                    self.add_error(field, _('Este campo é obrigatório quando a emissão de nota fiscal está habilitada.'))
                    
        return cleaned_data
