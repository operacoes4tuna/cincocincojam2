from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Constantes
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

REGIME_TRIBUTARIO_CHOICES = [
    ('simples_nacional', _('Simples Nacional')),
    ('lucro_presumido', _('Lucro Presumido')),
    ('lucro_real', _('Lucro Real'))
]

class ServiceCode(models.Model):
    """
    Modelo para armazenar códigos de serviço municipal.
    Permite múltiplos códigos por empresa.
    """
    company_config = models.ForeignKey(
        'CompanyConfig',
        on_delete=models.CASCADE,
        related_name='service_codes',
        verbose_name=_('configuração da empresa')
    )
    code = models.CharField(
        max_length=10,
        verbose_name=_('código de serviço'),
        help_text=_('Código de serviço municipal (ex: 0107, 1401, etc.)')
    )
    description = models.CharField(
        max_length=255,
        verbose_name=_('descrição do serviço'),
        help_text=_('Descrição do tipo de serviço prestado')
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('código padrão'),
        help_text=_('Marque como padrão para usar automaticamente em novas notas')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('criado em')
    )
    
    class Meta:
        verbose_name = _('código de serviço')
        verbose_name_plural = _('códigos de serviço')
        unique_together = ['company_config', 'code']
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.description}"
    
    def save(self, *args, **kwargs):
        # Se este código está sendo marcado como padrão, desmarcar outros
        if self.is_default:
            ServiceCode.objects.filter(
                company_config=self.company_config,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

class CompanyConfig(models.Model):
    """
    Configurações da empresa para emissão de notas fiscais.
    Cada professor que deseja emitir notas precisa ter uma configuração.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='company_config',
        verbose_name=_('usuário')
    )
    enabled = models.BooleanField(
        default=False, 
        verbose_name=_('habilitar emissão de nota')
    )
    
    # Dados da empresa emissora (Professor)
    cnpj = models.CharField(
        max_length=14, 
        blank=True, 
        null=True, 
        verbose_name=_('CNPJ')
    )
    razao_social = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('razão social')
    )
    nome_fantasia = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('nome fantasia')
    )
    endereco = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('endereço')
    )
    numero = models.CharField(
        max_length=10, 
        blank=True, 
        null=True, 
        verbose_name=_('número')
    )
    complemento = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_('complemento')
    )
    bairro = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_('bairro')
    )
    municipio = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_('município')
    )
    uf = models.CharField(
        max_length=2, 
        choices=UF_CHOICES,
        blank=True, 
        null=True, 
        verbose_name=_('UF')
    )
    cep = models.CharField(
        max_length=8, 
        blank=True, 
        null=True, 
        verbose_name=_('CEP')
    )
    telefone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name=_('telefone')
    )
    email = models.EmailField(
        blank=True, 
        null=True, 
        verbose_name=_('e-mail')
    )
    
    # Configurações fiscais
    inscricao_municipal = models.CharField(
        max_length=30, 
        blank=True, 
        null=True, 
        verbose_name=_('inscrição municipal')
    )
    regime_tributario = models.CharField(
        max_length=20, 
        choices=REGIME_TRIBUTARIO_CHOICES, 
        default='simples_nacional',
        verbose_name=_('regime tributário')
    )
    city_service_code = models.CharField(
        max_length=10,
        default='0107',
        verbose_name=_('código de serviço municipal (legado)'),
        help_text=_('Campo mantido para compatibilidade. Use os códigos de serviço relacionados.')
    )
    
    # Campos para controle de RPS (Recibo Provisório de Serviço)
    rps_serie = models.CharField(
        max_length=5,
        default='1',
        verbose_name=_('série do RPS'),
        help_text=_('Série do Recibo Provisório de Serviço')
    )
    rps_numero_atual = models.PositiveIntegerField(
        default=1,
        verbose_name=_('número atual do RPS'),
        help_text=_('Número sequencial do último RPS emitido')
    )
    rps_lote = models.PositiveIntegerField(
        default=1,
        verbose_name=_('lote de RPS'),
        help_text=_('Número do lote de RPS para envio em lote')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('criado em')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('atualizado em')
    )
    
    class Meta:
        verbose_name = _('configuração da empresa')
        verbose_name_plural = _('configurações da empresa')
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} - {self.razao_social or 'Sem configuração'}"
    
    def save(self, *args, **kwargs):
        # Remover formatação do CNPJ antes de salvar
        if self.cnpj:
            self.cnpj = self.cnpj.replace('.', '').replace('/', '').replace('-', '')
        super().save(*args, **kwargs)
        
        # Se não há códigos de serviço e existe um código legado, criar o primeiro código
        if not self.service_codes.exists() and self.city_service_code:
            ServiceCode.objects.create(
                company_config=self,
                code=self.city_service_code,
                description='Código padrão migrado',
                is_default=True
            )
    
    def get_default_service_code(self):
        """
        Retorna o código de serviço padrão.
        Se não houver códigos cadastrados, retorna o campo legado.
        """
        default_code = self.service_codes.filter(is_default=True).first()
        if default_code:
            return default_code.code
        
        # Fallback para o primeiro código disponível
        first_code = self.service_codes.first()
        if first_code:
            return first_code.code
            
        # Fallback final para o campo legado
        return self.city_service_code or '0107'
    
    def get_service_code_choices(self):
        """
        Retorna uma lista de tuplas (código, descrição) para uso em formulários.
        """
        return [(sc.code, f"{sc.code} - {sc.description}") for sc in self.service_codes.all()]
    
    def is_complete(self):
        """
        Verifica se todos os campos obrigatórios para emissão de notas fiscais estão preenchidos.
        """
        required_fields = [
            self.cnpj, 
            self.razao_social, 
            self.nome_fantasia, 
            self.regime_tributario, 
            self.endereco, 
            self.numero, 
            self.bairro, 
            self.municipio, 
            self.uf, 
            self.cep
        ]
        
        # Verificar se há pelo menos um código de serviço ou o campo legado
        has_service_code = (
            self.service_codes.exists() or 
            (self.city_service_code and self.city_service_code.strip())
        )
        
        return (
            all(field is not None and field != '' for field in required_fields) and 
            self.enabled and 
            has_service_code
        )


class Invoice(models.Model):
    """
    Modelo para armazenar informações sobre notas fiscais emitidas
    """
    STATUS_CHOICES = [
        ('draft', _('Rascunho')),
        ('pending', _('Pendente')),
        ('processing', _('Processando')),
        ('issued', _('Emitida')),
        ('approved', _('Aprovada')),
        ('cancelled', _('Cancelada')),
        ('error', _('Erro'))
    ]
    
    transaction = models.ForeignKey(
        'payments.PaymentTransaction', 
        on_delete=models.CASCADE, 
        related_name='invoices',
        verbose_name=_('transação'),
        null=True,
        blank=True
    )
    
    singlesale = models.ForeignKey(
        'payments.SingleSale',
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name=_('venda avulsa'),
        null=True,
        blank=True
    )
    
    # Campos para uso direto (quando não houver transação ou venda avulsa)
    amount = models.DecimalField(
        _('valor'), 
        max_digits=10, 
        decimal_places=2,
        null=True,
        blank=True
    )
    customer_name = models.CharField(
        _('nome do cliente'),
        max_length=255,
        null=True,
        blank=True
    )
    customer_email = models.EmailField(
        _('email do cliente'),
        max_length=255,
        null=True,
        blank=True
    )
    customer_tax_id = models.CharField(
        _('CPF/CNPJ do cliente'),
        max_length=20,
        null=True,
        blank=True
    )
    description = models.CharField(
        _('descrição'),
        max_length=255,
        null=True,
        blank=True
    )
    
    type = models.CharField(
        _('tipo'),
        max_length=10,
        choices=[('nfse', 'NFSe'), ('nfe', 'NFe'), ('rps', 'RPS')],
        default='rps'
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name=_('status')
    )
    
    # Referência para API FocusNFe
    focus_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('ID no Focus')
    )
    focus_reference = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Referência no Focus')
    )
    focus_status = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('Status no Focus')
    )
    
    # ID externo para a API NFE.io
    external_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('ID externo API')
    )
    
    focus_message = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_('Mensagem do Focus')
    )
    focus_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_('URL no Focus')
    )
    focus_pdf_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_('URL do PDF')
    )
    focus_xml_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name=_('URL do XML')
    )
    focus_data = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_('Dados completos do Focus')
    )
    
    # Campos de RPS
    rps_serie = models.CharField(
        max_length=5,
        blank=True, 
        null=True,
        verbose_name=_('série RPS')
    )
    rps_numero = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('número RPS')
    )
    rps_lote = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name=_('lote RPS')
    )
    
    # Campos de resposta e controle
    response_data = models.JSONField(
        blank=True, 
        null=True,
        verbose_name=_('dados da resposta')
    )
    error_message = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_('mensagem de erro')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('criado em')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('atualizado em')
    )
    emitted_at = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name=_('emitido em')
    )
    
    class Meta:
        verbose_name = _('nota fiscal')
        verbose_name_plural = _('notas fiscais')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"NFe #{self.id} - {self.transaction.id if self.transaction else self.singlesale.id} - {self.get_status_display()}"
