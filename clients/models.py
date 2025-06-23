from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

# Validators
cpf_validator = RegexValidator(
    regex=r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
    message=_('Digite um CPF válido no formato XXX.XXX.XXX-XX')
)

cnpj_validator = RegexValidator(
    regex=r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',
    message=_('Digite um CNPJ válido no formato XX.XXX.XXX/XXXX-XX')
)

cep_validator = RegexValidator(
    regex=r'^\d{5}-\d{3}$',
    message=_('Digite um CEP válido no formato XXXXX-XXX')
)

# UF choices for Brazilian states
UF_CHOICES = [
    ('AC', 'Acre'),
    ('AL', 'Alagoas'),
    ('AP', 'Amapá'),
    ('AM', 'Amazonas'),
    ('BA', 'Bahia'),
    ('CE', 'Ceará'),
    ('DF', 'Distrito Federal'),
    ('ES', 'Espírito Santo'),
    ('GO', 'Goiás'),
    ('MA', 'Maranhão'),
    ('MT', 'Mato Grosso'),
    ('MS', 'Mato Grosso do Sul'),
    ('MG', 'Minas Gerais'),
    ('PA', 'Pará'),
    ('PB', 'Paraíba'),
    ('PR', 'Paraná'),
    ('PE', 'Pernambuco'),
    ('PI', 'Piauí'),
    ('RJ', 'Rio de Janeiro'),
    ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'),
    ('RO', 'Rondônia'),
    ('RR', 'Roraima'),
    ('SC', 'Santa Catarina'),
    ('SP', 'São Paulo'),
    ('SE', 'Sergipe'),
    ('TO', 'Tocantins'),
]


class Client(models.Model):
    """
    Modelo base para clientes (tanto pessoa física quanto jurídica)
    """
    class Type(models.TextChoices):
        INDIVIDUAL = 'INDIVIDUAL', _('Pessoa Física')
        COMPANY = 'COMPANY', _('Pessoa Jurídica')
    
    # The professor who registered this client
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='clients',
        verbose_name=_('professor')
    )
    
    # Basic fields for all clients
    email = models.EmailField(_('email'), max_length=255, blank=True, null=True)
    phone = models.CharField(
        _('telefone'), max_length=20, blank=True, null=True
    )
    
    # Address fields
    address = models.CharField(_('endereço'), max_length=255, blank=True, null=True)
    address_number = models.CharField(_('número'), max_length=20, blank=True, null=True)
    address_complement = models.CharField(
        _('complemento'), max_length=100, blank=True, null=True
    )
    neighborhood = models.CharField(_('bairro'), max_length=100, blank=True, null=True)
    city = models.CharField(_('cidade'), max_length=100, blank=True, null=True)
    state = models.CharField(_('estado'), max_length=2, choices=UF_CHOICES, blank=True, null=True)
    zipcode = models.CharField(
        _('CEP'), max_length=9, validators=[cep_validator], blank=True, null=True
    )
    
    # Type of client
    client_type = models.CharField(
        _('tipo de cliente'),
        max_length=10,
        choices=Type.choices,
        default=Type.INDIVIDUAL
    )
    
    # Tracking fields
    created_at = models.DateTimeField(_('criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('atualizado em'), auto_now=True)
    
    class Meta:
        verbose_name = _('cliente')
        verbose_name_plural = _('clientes')
        ordering = ['client_type', '-created_at']
    
    def __str__(self):
        if hasattr(self, 'individual'):
            return f"{self.individual.full_name} (PF)"
        elif hasattr(self, 'company'):
            return f"{self.company.company_name} (PJ)"
        return f"Cliente #{self.id}"
    
    def save(self, *args, **kwargs):
        # Formatting zipcode to remove any non-digit characters
        if self.zipcode:
            digits = ''.join(filter(str.isdigit, self.zipcode))
            if len(digits) == 8:
                self.zipcode = f"{digits[:5]}-{digits[5:]}"
        super().save(*args, **kwargs)


class IndividualClient(models.Model):
    """
    Modelo para clientes pessoa física (alunos)
    """
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name='individual',
        verbose_name=_('cliente')
    )
    
    # Personal information
    full_name = models.CharField(_('nome completo'), max_length=255)
    cpf = models.CharField(
        _('CPF'), max_length=14, validators=[cpf_validator], blank=True, null=True
    )
    rg = models.CharField(_('RG'), max_length=30, blank=True, null=True)
    birth_date = models.DateField(
        _('data de nascimento'), blank=True, null=True
    )
    
    class Meta:
        verbose_name = _('cliente pessoa física')
        verbose_name_plural = _('clientes pessoa física')
        constraints = [
            models.UniqueConstraint(
                fields=['cpf'],
                condition=models.Q(cpf__isnull=False),
                name='unique_non_null_cpf'
            )
        ]
        
    def __str__(self):
        return f"{self.full_name} - {self.cpf}"
    
    def save(self, *args, **kwargs):
        # Ensure client_type is INDIVIDUAL
        if self.client:
            self.client.client_type = Client.Type.INDIVIDUAL
            self.client.save(update_fields=['client_type'])
            
        # Format CPF
        if self.cpf:
            digits = ''.join(filter(str.isdigit, self.cpf))
            if len(digits) == 11:
                fmt = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
                self.cpf = fmt
                
        super().save(*args, **kwargs)


class CompanyClient(models.Model):
    """
    Modelo para clientes pessoa jurídica (empresas/produtoras)
    """
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name='company',
        verbose_name=_('cliente')
    )
    
    # Company information
    company_name = models.CharField(_('razão social'), max_length=255)
    trade_name = models.CharField(
        _('nome fantasia'), max_length=255, blank=True, null=True
    )
    cnpj = models.CharField(
        _('CNPJ'), max_length=18, validators=[cnpj_validator], unique=True
    )
    state_registration = models.CharField(
        _('inscrição estadual'), max_length=30, blank=True, null=True
    )
    municipal_registration = models.CharField(
        _('inscrição municipal'), max_length=30, blank=True, null=True
    )
    
    # Responsible person
    responsible_name = models.CharField(
        _('nome do responsável'), max_length=255, blank=True, null=True
    )
    responsible_cpf = models.CharField(
        _('CPF do responsável'), max_length=14, validators=[cpf_validator],
        blank=True, null=True
    )
    
    class Meta:
        verbose_name = _('cliente pessoa jurídica')
        verbose_name_plural = _('clientes pessoa jurídica')
        
    def __str__(self):
        return f"{self.company_name} - {self.cnpj}"
    
    def save(self, *args, **kwargs):
        # Ensure client_type is COMPANY
        if self.client:
            self.client.client_type = Client.Type.COMPANY
            self.client.save(update_fields=['client_type'])
            
        # Format CNPJ
        if self.cnpj:
            digits = ''.join(filter(str.isdigit, self.cnpj))
            if len(digits) == 14:
                fmt = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/"
                fmt += f"{digits[8:12]}-{digits[12:]}"
                self.cnpj = fmt
                
        # Format responsible CPF
        if self.responsible_cpf:
            digits = ''.join(filter(str.isdigit, self.responsible_cpf))
            if len(digits) == 11:
                fmt = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
                self.responsible_cpf = fmt
                
        super().save(*args, **kwargs)
