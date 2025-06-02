from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from .models import SingleSale

class SingleSaleForm(forms.ModelForm):
    """
    Custom form for SingleSale model with improved field labels and validation
    """
    # Campos adicionais que não estão no modelo mas são usados no template
    emission_date = forms.DateField(
        label=_('Data de emissão'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    due_date = forms.DateField(
        label=_('Vencimento do boleto'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    recurrence_count = forms.IntegerField(
        label=_('Quantidade de recorrências'),
        initial=0,
        required=False,
        widget=forms.Select(choices=[
            (0, _('Sem recorrência')),
            (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'),
            (7, '7'), (8, '8'), (9, '9'), (10, '10'), (11, '11'),
            (12, '12'), (13, '13'), (14, '14'), (15, '15'),
            (16, '16'), (17, '17'), (18, '18'), (19, '19'), (20, '20')
        ], attrs={'class': 'form-select'})
    )
    generate_boleto = forms.BooleanField(
        label=_('Gerar boleto'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    has_boleto = forms.BooleanField(
        label=_('Possui boleto'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = SingleSale
        fields = [
            'description', 'amount', 'status',
            'customer_name', 'customer_email', 'customer_cpf',
            'customer_address', 'customer_address_number', 'customer_address_complement',
            'customer_neighborhood', 'customer_city', 'customer_state', 'customer_zipcode',
            'customer_phone'
        ]
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Descrição do produto/serviço')}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nome completo')}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('email@exemplo.com')}),
            'customer_cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('CPF ou CNPJ')}),
            'customer_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Rua, Avenida, etc.')}),
            'customer_address_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nº')}),
            'customer_address_complement': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Apto, Sala, etc.')}),
            'customer_neighborhood': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Bairro')}),
            'customer_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Cidade')}),
            'customer_state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('UF'), 'maxlength': '2'}),
            'customer_zipcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('00000-000')}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('(11) 99999-9999')}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Change the label for customer_cpf to include CNPJ
        self.fields['customer_cpf'].label = _('CNPJ/CPF do Cliente')
        
        # Adicionar validadores
        self.fields['amount'].validators = [MinValueValidator(0.01)]
        
        # Tornar campos obrigatórios
        self.fields['description'].required = True
        self.fields['amount'].required = True
        self.fields['customer_name'].required = True
        self.fields['customer_email'].required = True
        
        # Configurar campos opcionais
        for field_name in ['customer_cpf', 'customer_address', 'customer_address_number', 'customer_address_complement',
                          'customer_neighborhood', 'customer_city', 'customer_state', 'customer_zipcode',
                          'customer_phone']:
            if field_name in self.fields:
                self.fields[field_name].required = False
    
    def clean_customer_cpf(self):
        """Remove formatting characters from CPF/CNPJ"""
        cpf = self.cleaned_data.get('customer_cpf')
        if cpf:
            # Remove dots, slashes, and hyphens
            cpf = cpf.replace('.', '').replace('/', '').replace('-', '').replace(' ', '')
        return cpf
    
    def clean_amount(self):
        """Validate amount is positive"""
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError(_('O valor deve ser maior que zero.'))
        return amount
    
    def clean_customer_state(self):
        """Validate state is 2 characters"""
        state = self.cleaned_data.get('customer_state')
        if state and len(state) > 2:
            return state[:2].upper()
        return state.upper() if state else state
    
    def save(self, commit=True):
        """Override save to handle additional logic and set default values for removed fields"""
        instance = super().save(commit=False)
        
        # Definir valores padrão para campos que foram removidos da interface mas são necessários no modelo
        if not hasattr(instance, 'quantity') or instance.quantity is None:
            instance.quantity = 1
        
        if not hasattr(instance, 'unit_value') or instance.unit_value is None:
            instance.unit_value = instance.amount
            
        # Garantir valores padrão para campos de nota fiscal
        if not hasattr(instance, 'generate_invoice') or instance.generate_invoice is None:
            instance.generate_invoice = False
            
        if not hasattr(instance, 'invoice_type') or not instance.invoice_type:
            instance.invoice_type = 'nfse'
            
        if commit:
            instance.save()
        return instance 