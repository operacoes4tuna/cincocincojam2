# -*- coding: utf-8 -*-
"""
Configuração para QR Code PIX Fixo
=================================

Este arquivo contém as informações bancárias fixas que serão utilizadas
para gerar o QR Code PIX estático para todos os pagamentos.
"""

# DADOS BANCÁRIOS FIXOS PARA PIX
FIXED_PIX_CONFIG = {
    # Chave PIX (pode ser CPF, CNPJ, email, telefone ou chave aleatória)
    'pix_key': 'exemplo@cincocinco.com',  # ALTERE PARA SUA CHAVE PIX REAL
    
    # Nome do beneficiário (titular da conta)
    'beneficiary_name': 'CINCOCINCO JAM MUSIC SCHOOL',  # ALTERE PARA O NOME REAL
    
    # Cidade do beneficiário
    'beneficiary_city': 'SAO PAULO',  # ALTERE PARA A CIDADE REAL
    
    # CEP do beneficiário (opcional)
    'beneficiary_postal_code': '01234567',  # ALTERE PARA O CEP REAL
    
    # Identificador da transação (será usado como base)
    'transaction_id_prefix': 'CURSO',
    
    # Descrição padrão para o PIX
    'description_template': 'Pagamento Curso: {course_name}',
    
    # QR Code fixo como fallback (opcional)
    # Você pode gerar um QR code fixo para sua chave PIX em:
    # https://gerarqrcodepix.com.br/ ou similar
    'fixed_qr_code': 'https://chart.googleapis.com/chart?chs=300x300&cht=qr&chl=00020126360014BR.GOV.BCB.PIX0114+5511999999999520400005303986540550.005802BR5925CINCOCINCO JAM MUSIC SCHO6009SAO PAULO62070503***6304ABCD',
    
    # Instruções para o usuário
    'payment_instructions': [
        'Abra o aplicativo do seu banco',
        'Escolha a opção PIX',
        'Escaneie o QR Code ou cole a chave PIX',
        'Confirme o pagamento do valor exato',
        'Aguarde a confirmação automática'
    ],
    
    # Dados bancários para exibição (opcional)
    'bank_info': {
        'bank_name': 'Banco Exemplo',  # ALTERE PARA O BANCO REAL
        'account_type': 'Conta Corrente',
        'account_holder': 'CINCOCINCO JAM MUSIC SCHOOL',  # ALTERE PARA O TITULAR REAL
        # Não coloque dados sensíveis como número da conta aqui
    },
    
    # Tempo para expiração do pagamento (em minutos)
    'payment_expiry_minutes': 60,
    
    # Habilitar deep linking para apps bancários
    'enable_bank_deep_linking': True,
    
    # URLs de deep linking para principais bancos
    'bank_deep_links': {
        'pix_universal': 'br.gov.bcb.pix://qr/v2/{pix_code}',
        'inter': 'inter://pix/payment?pix={pix_code}',
        'nubank': 'nubank://pix?code={pix_code}',
        'itau': 'itau://pix?codigo={pix_code}',
        'bradesco': 'bradesco://pix/qrcode/{pix_code}',
        'caixa': 'caixatemaqui://pix?qrcode={pix_code}',
        'bb': 'bancodobrasil://pix/qrcode/{pix_code}',
        'santander': 'santander://pix?qrcode={pix_code}',
    }
}

def generate_pix_code(course, student, amount):
    """
    Gera um código PIX simples para a transação.
    
    Args:
        course: Instância do curso
        student: Instância do estudante
        amount: Valor do pagamento
    
    Returns:
        str: Código PIX formatado
    """
    import re
    
    # Sanitizar nome do curso para usar no código
    course_safe = re.sub(r'[^A-Za-z0-9\s]', '', course.title)[:20]
    course_safe = course_safe.replace(' ', '').upper()
    
    # Sanitizar nome do estudante
    student_safe = re.sub(r'[^A-Za-z0-9\s]', '', student.get_full_name() or student.email)[:15]
    student_safe = student_safe.replace(' ', '').upper()
    
    # Formato: CURSO{ID}-{STUDENT}-{COURSE}
    pix_code = f"{FIXED_PIX_CONFIG['transaction_id_prefix']}{course.id}-{student_safe}-{course_safe}"
    
    return pix_code[:35]  # Limitar tamanho

def get_payment_description(course):
    """
    Gera a descrição do pagamento baseada no template.
    
    Args:
        course: Instância do curso
    
    Returns:
        str: Descrição formatada do pagamento
    """
    return FIXED_PIX_CONFIG['description_template'].format(
        course_name=course.title
    )

def get_fixed_qr_code_url():
    """
    Retorna a URL do QR Code fixo.
    
    Returns:
        str: URL do QR Code
    """
    return FIXED_PIX_CONFIG['fixed_qr_code']

def get_pix_key():
    """
    Retorna a chave PIX configurada.
    
    Returns:
        str: Chave PIX
    """
    return FIXED_PIX_CONFIG['pix_key']

def get_payment_instructions():
    """
    Retorna as instruções de pagamento.
    
    Returns:
        list: Lista de instruções
    """
    return FIXED_PIX_CONFIG['payment_instructions']

def get_bank_deep_links(pix_code):
    """
    Gera os links para abrir o PIX em apps bancários.
    
    Args:
        pix_code: Código PIX da transação
    
    Returns:
        dict: Dicionário com os deep links
    """
    deep_links = {}
    for bank, template in FIXED_PIX_CONFIG['bank_deep_links'].items():
        deep_links[bank] = template.format(pix_code=pix_code)
    return deep_links 