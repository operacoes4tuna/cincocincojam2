from django import forms
from django.utils.translation import gettext_lazy as _
from .models import SingleSale

class SingleSaleForm(forms.ModelForm):
    """
    Custom form for SingleSale model with improved field labels
    """
    class Meta:
        model = SingleSale
        fields = [
            'description', 'amount', 
            'customer_name', 'customer_email', 'customer_cpf',
            'customer_address', 'customer_address_number', 'customer_address_complement',
            'customer_neighborhood', 'customer_city', 'customer_state', 'customer_zipcode',
            'customer_phone',
            'product_code', 'ncm_code', 'cfop_code', 'quantity', 'unit_value',
            'invoice_type', 'generate_invoice', 'status'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Change the label for customer_cpf to include CNPJ
        self.fields['customer_cpf'].label = _('CNPJ/CPF do Cliente')
    
    def clean_customer_cpf(self):
        """Remove formatting characters from CPF/CNPJ"""
        cpf = self.cleaned_data.get('customer_cpf')
        if cpf:
            # Remove dots, slashes, and hyphens
            cpf = cpf.replace('.', '').replace('/', '').replace('-', '')
        return cpf 