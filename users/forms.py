from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """
    Formulário para criação de novos usuários, com campos personalizados.
    """
    email = forms.EmailField(label='Email', required=True)
    first_name = forms.CharField(label='Nome', required=True)
    last_name = forms.CharField(label='Sobrenome', required=True)
    user_type = forms.ChoiceField(
        label='Tipo de Usuário',
        choices=User.Types.choices,
        required=True
    )
    cpf = forms.CharField(
        label='CPF',
        required=False,
        max_length=14,
        help_text='Digite o CPF no formato XXX.XXX.XXX-XX'
    )
    
    # Campos de endereço
    address_line = forms.CharField(
        label='Endereço',
        required=False,
        max_length=255,
        help_text='Rua, Avenida, etc.'
    )
    address_number = forms.CharField(
        label='Número',
        required=False,
        max_length=10,
        help_text='Número do endereço'
    )
    neighborhood = forms.CharField(
        label='Bairro',
        required=False,
        max_length=100
    )
    city = forms.CharField(
        label='Cidade',
        required=False,
        max_length=100
    )
    state = forms.CharField(
        label='Estado',
        required=False,
        max_length=2,
        help_text='UF do estado (ex: SP, RJ)'
    )
    zipcode = forms.CharField(
        label='CEP',
        required=False,
        max_length=9,
        help_text='CEP no formato XXXXX-XXX'
    )
    
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'user_type', 'cpf',
            'address_line', 'address_number', 'neighborhood', 'city',
            'state', 'zipcode', 'password1', 'password2'
        )
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adicionar mensagens de ajuda
        self.fields['password1'].help_text = 'Sua senha deve conter pelo menos 8 caracteres e não pode ser muito comum.'
        self.fields['password2'].help_text = 'Repita a senha para confirmação.'
        self.fields['email'].help_text = 'Este será o login do usuário. Precisa ser um email válido.'
        
        # Tornar campos obrigatórios apenas para alunos
        if self.data.get('user_type') == 'STUDENT':
            self.fields['cpf'].required = True
            self.fields['address_line'].required = True
            self.fields['address_number'].required = True
            self.fields['neighborhood'].required = True
            self.fields['city'].required = True
            self.fields['state'].required = True
            self.fields['zipcode'].required = True


class CustomUserChangeForm(UserChangeForm):
    """
    Formulário para edição de usuários existentes, com campos personalizados.
    Não inclui campo de senha diretamente, pois isso é tratado separadamente.
    """
    password = None  # Remove o campo de senha deste formulário
    
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'user_type', 'cpf',
            'address_line', 'address_number', 'neighborhood', 'city',
            'state', 'zipcode', 'bio', 'profile_image', 'is_active'
        )
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar alguns campos obrigatórios
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        
        # Verificar se o usuário atual é admin
        request = kwargs.get('initial', {}).get('request')
        if request and not request.user.is_admin:
            # Se não for admin, remover campos que usuários comuns não devem editar
            self.fields.pop('user_type', None)
            self.fields.pop('is_active', None)
            
            # E fazer o email somente leitura
            self.fields['email'].widget.attrs['readonly'] = True
            
        # Tornar campos obrigatórios apenas para alunos
        if self.instance and self.instance.user_type == 'STUDENT':
            self.fields['cpf'].required = True
            self.fields['address_line'].required = True
            self.fields['address_number'].required = True
            self.fields['neighborhood'].required = True
            self.fields['city'].required = True
            self.fields['state'].required = True
            self.fields['zipcode'].required = True