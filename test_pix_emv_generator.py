#!/usr/bin/env python3
"""
Script de teste para o gerador de PIX EMV dinâmico
Demonstra a geração de QR Code PIX seguindo padrões do Banco Central
"""

import os
import sys
import django
from decimal import Decimal

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from invoices.pix_service import InvoicePixService
from invoices.models import Invoice, InvoicePixPayment


def validate_emv_structure(brcode):
    """
    Valida a estrutura básica do BR Code EMV de forma mais rigorosa
    """
    validations = []
    
    # Verificar início do payload (Payload Format Indicator)
    if brcode.startswith("000201"):
        validations.append("✅ Payload Format Indicator correto (000201)")
    else:
        validations.append("❌ Payload Format Indicator incorreto")
    
    # Verificar Point of Initiation Method (dinâmico)
    if "010212" in brcode:
        validations.append("✅ Point of Initiation Method correto (dinâmico)")
    else:
        validations.append("❌ Point of Initiation Method incorreto")
    
    # Verificar presença de chave PIX na posição correta
    if "15992202706" in brcode:
        validations.append("✅ Chave PIX presente (15992202706)")
    else:
        validations.append("❌ Chave PIX não encontrada")
    
    # Verificar GUI do PIX
    if "br.gov.bcb.pix" in brcode:
        validations.append("✅ GUI do PIX presente (br.gov.bcb.pix)")
    else:
        validations.append("❌ GUI do PIX não encontrado")
    
    # Verificar Merchant Category Code
    if "52040000" in brcode:
        validations.append("✅ Merchant Category Code correto (0000)")
    else:
        validations.append("❌ Merchant Category Code incorreto")
    
    # Verificar código do país
    if "5802BR" in brcode:
        validations.append("✅ Código do país presente (BR)")
    else:
        validations.append("❌ Código do país não encontrado")
    
    # Verificar moeda (BRL)
    if "5303986" in brcode:
        validations.append("✅ Código da moeda correto (986 = BRL)")
    else:
        validations.append("❌ Código da moeda incorreto")
    
    # Verificar nome do recebedor
    if "Fred Carvalho" in brcode:
        validations.append("✅ Nome do recebedor presente")
    else:
        validations.append("❌ Nome do recebedor não encontrado")
    
    # Verificar cidade
    if "RIO DE JANEIRO" in brcode:
        validations.append("✅ Cidade presente (RIO DE JANEIRO)")
    else:
        validations.append("❌ Cidade não encontrada")
    
    # Verificar CRC (últimos 4 dígitos devem ser hexadecimais)
    crc = brcode[-4:]
    try:
        int(crc, 16)
        validations.append("✅ CRC16 válido")
    except ValueError:
        validations.append("❌ CRC16 inválido")
    
    return validations


def test_pix_emv_generation():
    """
    Testa a geração de PIX EMV com diferentes valores
    """
    print("🚀 Testando Gerador de PIX EMV Dinâmico")
    print("=" * 50)
    
    # Criar instância do serviço
    pix_service = InvoicePixService()
    
    print(f"📋 Dados do Recebedor:")
    print(f"   Nome: {pix_service.receiver_data['name']}")
    print(f"   Cidade: {pix_service.receiver_data['city']}")
    print(f"   Chave PIX: {pix_service.receiver_data['pix_key']} (CPF)")
    print()
    
    # Simular dados de uma invoice fictícia
    class MockInvoice:
        def __init__(self, invoice_id, amount):
            self.id = invoice_id
            self.amount = amount
            self.transaction = None
            self.singlesale = None
            
    class MockPixPayment:
        def __init__(self, correlation_id, invoice):
            self.correlation_id = correlation_id
            self.invoice = invoice
    
    # Teste com diferentes valores
    test_values = [10.50, 25.99, 100.00, 1500.75]
    
    for i, amount in enumerate(test_values, 1):
        print(f"💰 Teste {i}: Valor R$ {amount:.2f}")
        print("-" * 30)
        
        # Criar objetos fictícios
        mock_invoice = MockInvoice(f"TEST{i:03d}", amount)
        mock_pix = MockPixPayment(f"test-{i}-123456789", mock_invoice)
        
        try:
            # Gerar BR Code EMV
            brcode = pix_service._generate_emv_brcode(mock_pix, amount)
            
            # Validar estrutura básica
            if brcode.startswith("000201") and len(brcode) > 50:
                print(f"✅ BR Code gerado com sucesso!")
                print(f"📱 Tamanho: {len(brcode)} caracteres")
                
                # Mostrar partes principais do código
                print(f"🔧 Detalhes técnicos:")
                print(f"   - Payload Format: {brcode[0:6]}")
                print(f"   - Point of Init: {brcode[6:12]}")
                print(f"   - PIX Key incluída: {'15992202706' in brcode}")
                print(f"   - Valor incluído: {f'{amount:.2f}' in brcode}")
                print(f"   - CRC16: {brcode[-4:]}")
                
                # Validação rigorosa
                print(f"🔍 Validação detalhada:")
                validations = validate_emv_structure(brcode)
                for validation in validations:
                    print(f"     {validation}")
                
                # Mostrar código completo (truncado para visualização)
                if len(brcode) > 80:
                    print(f"📄 BR Code: {brcode[:40]}...{brcode[-20:]}")
                else:
                    print(f"📄 BR Code: {brcode}")
                    
            else:
                print(f"❌ Erro: BR Code inválido ou mal formado")
                
        except Exception as e:
            print(f"❌ Erro ao gerar BR Code: {str(e)}")
            
        print()
    
    # Teste de QR Code
    print("🖼️  Testando geração de QR Code")
    print("-" * 30)
    
    try:
        mock_invoice = MockInvoice("QR001", 50.00)
        mock_pix = MockPixPayment("qrtest-123456789", mock_invoice)
        
        brcode = pix_service._generate_emv_brcode(mock_pix, 50.00)
        qr_data = pix_service._generate_local_qrcode(brcode)
        
        if qr_data and len(qr_data) > 100:
            print(f"✅ QR Code gerado com sucesso!")
            print(f"📊 Tamanho base64: {len(qr_data)} caracteres")
            print(f"🎯 Primeiro bytes: {qr_data[:50]}...")
        else:
            print(f"❌ Erro: QR Code inválido")
            
    except Exception as e:
        print(f"❌ Erro ao gerar QR Code: {str(e)}")
    
    print()
    print("🏁 Teste concluído!")
    
    # Exibir um exemplo de BR Code válido para comparação
    print("\n" + "=" * 60)
    print("📋 EXEMPLO DE BR CODE VÁLIDO PARA BANCOS:")
    print("=" * 60)
    mock_example = MockPixPayment("example-123", MockInvoice("001", 25.00))
    example_brcode = pix_service._generate_emv_brcode(mock_example, 25.00)
    print(f"BR Code completo: {example_brcode}")
    print()
    
    # Quebrar o código para análise
    print("🔍 ANÁLISE DETALHADA DO CÓDIGO:")
    print("-" * 40)
    pos = 0
    campos = [
        ("00", "Payload Format Indicator"),
        ("01", "Point of Initiation Method"),
        ("26", "Merchant Account Information"),
        ("52", "Merchant Category Code"),
        ("53", "Transaction Currency"),
        ("54", "Transaction Amount"),
        ("58", "Country Code"),
        ("59", "Merchant Name"),
        ("60", "Merchant City"),
        ("62", "Additional Data Field"),
        ("63", "CRC16")
    ]
    
    for tag, desc in campos:
        if pos < len(example_brcode) and example_brcode[pos:pos+2] == tag:
            length = int(example_brcode[pos+2:pos+4])
            value = example_brcode[pos+4:pos+4+length]
            print(f"{tag}: {desc}")
            print(f"    Tamanho: {length:02d}")
            print(f"    Valor: {value}")
            pos += 4 + length
    
    print("=" * 60)


if __name__ == "__main__":
    test_pix_emv_generation()
    
    print("\n" + "=" * 50)
    print("📚 Informações adicionais:")
    print("- Este gerador segue o padrão EMV QR Code")
    print("- Baseado nas especificações do Banco Central v2.3.0")
    print("- Chave PIX: CPF do Fred Carvalho (15992202706)")
    print("- Valores dinâmicos conforme nota fiscal")
    print("- QR Code compatível com aplicativos bancários")
    print("=" * 50) 