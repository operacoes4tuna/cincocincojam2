from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import uuid

class UserManager(BaseUserManager):
    """
    Manager personalizado para o modelo User, permitindo criar usuários
    com email como identificador principal.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Cria e salva um usuário com o email e senha fornecidos.
        """
        if not email:
            raise ValueError(_('O email deve ser fornecido'))
        email = self.normalize_email(email)
        
        # Gera um username único baseado no email
        username = slugify(email.split('@')[0])
        if 'username' not in extra_fields:
            # Verifica se o username já existe e adiciona um código se necessário
            if self.model.objects.filter(username=username).exists():
                username = f"{username}-{uuid.uuid4().hex[:8]}"
            extra_fields['username'] = username
            
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Cria e salva um superusuário com o email e senha fornecidos.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Modelo de usuário personalizado com email como identificador principal e
    campos adicionais para diferentes tipos de usuário.
    """
    class Types(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrador')
        PROFESSOR = 'PROFESSOR', _('Professor')
        STUDENT = 'STUDENT', _('Aluno')
    
    # Campos de identificação
    email = models.EmailField(_('endereço de e-mail'), unique=True)
    username = models.CharField(_('nome de usuário'), max_length=150, unique=True)
    
    # Tipo de usuário
    user_type = models.CharField(
        _('tipo de usuário'),
        max_length=10,
        choices=Types.choices,
        default=Types.STUDENT,
    )
    
    # CPF (apenas para alunos)
    cpf = models.CharField(
        _('CPF'),
        max_length=14,
        blank=True,
        null=True,
        help_text=_('CPF do aluno no formato XXX.XXX.XXX-XX')
    )
    
    # Campos de endereço
    address_line = models.CharField(
        _('endereço'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Rua, Avenida, etc.')
    )
    address_number = models.CharField(
        _('número'),
        max_length=10,
        blank=True,
        null=True,
        help_text=_('Número do endereço')
    )
    neighborhood = models.CharField(
        _('bairro'),
        max_length=100,
        blank=True,
        null=True
    )
    city = models.CharField(
        _('cidade'),
        max_length=100,
        blank=True,
        null=True
    )
    state = models.CharField(
        _('estado'),
        max_length=2,
        blank=True,
        null=True,
        help_text=_('UF do estado (ex: SP, RJ)')
    )
    zipcode = models.CharField(
        _('CEP'),
        max_length=9,
        blank=True,
        null=True,
        help_text=_('CEP no formato XXXXX-XXX')
    )
    
    # Informações adicionais
    bio = models.TextField(_('biografia'), blank=True)
    profile_image = models.ImageField(
        _('imagem de perfil'),
        upload_to='profile_images/',
        blank=True,
        null=True
    )
    date_joined = models.DateTimeField(_('data de cadastro'), auto_now_add=True)
    
    # Define o email como campo de login
    USERNAME_FIELD = 'email'
    # Remove email do REQUIRED_FIELDS já que está no USERNAME_FIELD
    REQUIRED_FIELDS = []
    
    # Define o manager personalizado
    objects = UserManager()
    
    def save(self, *args, **kwargs):
        # Garante que o username seja único se não for fornecido
        if not self.username:
            base_username = slugify(self.email.split('@')[0])
            username = base_username
            counter = 1
            
            # Adiciona um contador até encontrar um username único
            while User.objects.filter(username=username).exclude(pk=self.pk).exists():
                username = f"{base_username}-{counter}"
                counter += 1
                
            self.username = username
            
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = _('usuário')
        verbose_name_plural = _('usuários')
    
    def __str__(self):
        return self.email
    
    # Propriedades para verificar o tipo de usuário
    @property
    def is_admin(self):
        return self.user_type == self.Types.ADMIN
    
    @property
    def is_professor(self):
        return self.user_type == self.Types.PROFESSOR
    
    @property
    def is_student(self):
        return self.user_type == self.Types.STUDENT
    
    # Método para verificar se um usuário é de um tipo específico
    def is_of_type(self, user_type):
        return self.user_type == user_type


class ModulePermission(models.Model):
    """
    Modelo para gerenciar permissões de acesso aos módulos do sistema para cada usuário.
    """
    class ModuleChoices(models.TextChoices):
        DASHBOARD = 'DASHBOARD', _('Dashboard')
        AGENDA = 'AGENDA', _('Agenda')
        CURSOS = 'CURSOS', _('Cursos')
        FINANCAS = 'FINANCAS', _('Finanças')
        CLIENTES = 'CLIENTES', _('Clientes')
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='module_permissions',
        verbose_name=_('usuário'),
        limit_choices_to={'user_type': User.Types.PROFESSOR}
    )
    
    module = models.CharField(
        _('módulo'),
        max_length=20,
        choices=ModuleChoices.choices
    )
    
    has_access = models.BooleanField(
        _('tem acesso'),
        default=True
    )
    
    created_at = models.DateTimeField(_('criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('atualizado em'), auto_now=True)
    
    class Meta:
        verbose_name = _('permissão de módulo')
        verbose_name_plural = _('permissões de módulos')
        unique_together = ['user', 'module']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_module_display()} - {'Acesso' if self.has_access else 'Bloqueado'}"
