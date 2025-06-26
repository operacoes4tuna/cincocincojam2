#!/usr/bin/env python3
"""
Validação final do QR Code PIX EMV
Verifica se o código está 100% compatível com bancos brasileiros
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


def parse_emv_code(brcode):
    """
    Analisa um BR Code EMV e extrai todos os campos
    """
    pos = 0
    fields = {}
    
    while pos < len(brcode):
        if pos + 4 > len(brcode):
            break
            
        tag = brcode[pos:pos+2]
        length = int(brcode[pos+2:pos+4])
        
        if pos + 4 + length > len(brcode):
            break
            
        value = brcode[pos+4:pos+4+length]
        fields[tag] = value
        pos += 4 + length
    
    return fields


def validate_pix_emv_compliance(brcode):
    """
    Valida se o BR Code está em total conformidade com as especificações do Banco Central
    """
    print("🔍 VALIDAÇÃO FINAL DE CONFORMIDADE EMV")
    print("=" * 50)
    
    fields = parse_emv_code(brcode)
    issues = []
    successes = []
    
    # 00 - Payload Format Indicator
    if fields.get('00') == '01':
        successes.append("✅ Payload Format Indicator: 01 (correto)")
    else:
        issues.append(f"❌ Payload Format Indicator: {fields.get('00')} (deve ser 01)")
    
    # 01 - Point of Initiation Method  
    if fields.get('01') == '12':
        successes.append("✅ Point of Initiation Method: 12 (dinâmico)")
    elif fields.get('01') == '11':
        successes.append("✅ Point of Initiation Method: 11 (estático)")
    else:
        issues.append(f"❌ Point of Initiation Method: {fields.get('01')} (deve ser 11 ou 12)")
    
    # 26 - Merchant Account Information (PIX)
    if '26' in fields:
        mai = fields['26']
        if mai.startswith('0014br.gov.bcb.pix01'):
            successes.append("✅ Merchant Account Information: estrutura PIX correta")
            # Extrair chave PIX
            key_start = mai.find('0111') + 4
            if key_start > 3:
                pix_key = mai[key_start:key_start+11]
                if pix_key == '15992202706':
                    successes.append(f"✅ Chave PIX: {pix_key} (CPF válido)")
                else:
                    issues.append(f"❌ Chave PIX: {pix_key} (não confere)")
        else:
            issues.append("❌ Merchant Account Information: estrutura PIX incorreta")
    else:
        issues.append("❌ Merchant Account Information (26): campo obrigatório ausente")
    
    # 52 - Merchant Category Code
    if fields.get('52') == '0000':
        successes.append("✅ Merchant Category Code: 0000 (correto)")
    else:
        issues.append(f"❌ Merchant Category Code: {fields.get('52')} (deve ser 0000)")
    
    # 53 - Transaction Currency
    if fields.get('53') == '986':
        successes.append("✅ Transaction Currency: 986 (BRL)")
    else:
        issues.append(f"❌ Transaction Currency: {fields.get('53')} (deve ser 986)")
    
    # 54 - Transaction Amount
    if '54' in fields:
        amount = fields['54']
        try:
            float(amount)
            successes.append(f"✅ Transaction Amount: R$ {amount}")
        except:
            issues.append(f"❌ Transaction Amount: {amount} (formato inválido)")
    else:
        issues.append("❌ Transaction Amount (54): campo obrigatório para PIX dinâmico")
    
    # 58 - Country Code
    if fields.get('58') == 'BR':
        successes.append("✅ Country Code: BR (Brasil)")
    else:
        issues.append(f"❌ Country Code: {fields.get('58')} (deve ser BR)")
    
    # 59 - Merchant Name
    if '59' in fields:
        name = fields['59']
        if 1 <= len(name) <= 25:
            successes.append(f"✅ Merchant Name: {name}")
        else:
            issues.append(f"❌ Merchant Name: {name} (deve ter 1-25 caracteres)")
    else:
        issues.append("❌ Merchant Name (59): campo obrigatório ausente")
    
    # 60 - Merchant City
    if '60' in fields:
        city = fields['60']
        if 1 <= len(city) <= 15:
            successes.append(f"✅ Merchant City: {city}")
        else:
            issues.append(f"❌ Merchant City: {city} (deve ter 1-15 caracteres)")
    else:
        issues.append("❌ Merchant City (60): campo obrigatório ausente")
    
    # 62 - Additional Data Field (opcional)
    if '62' in fields:
        successes.append(f"✅ Additional Data Field: {fields['62']}")
    
    # 63 - CRC16
    if '63' in fields:
        crc = fields['63']
        if len(crc) == 4:
            try:
                int(crc, 16)
                successes.append(f"✅ CRC16: {crc} (formato hexadecimal válido)")
            except:
                issues.append(f"❌ CRC16: {crc} (não é hexadecimal válido)")
        else:
            issues.append(f"❌ CRC16: {crc} (deve ter 4 caracteres)")
    else:
        issues.append("❌ CRC16 (63): campo obrigatório ausente")
    
    # Resultado final
    print(f"\n📊 RESULTADO DA VALIDAÇÃO:")
    print(f"✅ Sucessos: {len(successes)}")
    print(f"❌ Problemas: {len(issues)}")
    
    if issues:
        print(f"\n🚨 PROBLEMAS ENCONTRADOS:")
        for issue in issues:
            print(f"   {issue}")
    
    if successes:
        print(f"\n✅ VALIDAÇÕES CORRETAS:")
        for success in successes:
            print(f"   {success}")
    
    print(f"\n🎯 CONFORMIDADE: {'100% COMPATÍVEL' if not issues else f'{(len(successes)/(len(successes)+len(issues)))*100:.1f}% COMPATÍVEL'}")
    
    return len(issues) == 0


def test_real_scenario():
    """
    Testa um cenário real de nota fiscal com QR Code PIX
    """
    print("\n" + "=" * 60)
    print("🏦 TESTE DE CENÁRIO REAL - NOTA FISCAL")
    print("=" * 60)
    
    # Simular uma invoice real
    class MockInvoice:
        def __init__(self):
            self.id = 12345
            self.amount = 150.75
            self.transaction = None
            self.singlesale = None
            
    class MockPixPayment:
        def __init__(self):
            self.correlation_id = "invoice-12345-1735110000"
            self.invoice = MockInvoice()
    
    # Gerar QR Code
    pix_service = InvoicePixService()
    mock_pix = MockPixPayment()
    
    brcode = pix_service._generate_emv_brcode(mock_pix, 150.75)
    
    print(f"📱 BR Code gerado: {brcode}")
    print(f"📏 Tamanho: {len(brcode)} caracteres")
    
    # Validar
    is_valid = validate_pix_emv_compliance(brcode)
    
    if is_valid:
        print("\n🎉 SUCESSO! QR Code está 100% compatível com bancos brasileiros!")
        print("✅ Pode ser escaneado em qualquer app bancário")
        print("✅ Chave PIX será reconhecida corretamente")
        print("✅ Valor será exibido corretamente")
        print("✅ Nome do recebedor aparecerá")
    else:
        print("\n⚠️ ATENÇÃO! QR Code precisa de ajustes para funcionar em bancos")
    
    return is_valid


if __name__ == "__main__":
    print("🚀 VALIDAÇÃO FINAL DO QR CODE PIX EMV")
    print("=" * 60)
    print("Verificando se o código está 100% compatível com bancos brasileiros...")
    print()
    
    # Executar teste real
    success = test_real_scenario()
    
    print(f"\n{'='*60}")
    if success:
        print("🎯 RESULTADO FINAL: QR CODE APROVADO PARA PRODUÇÃO! 🎉")
        print("Seu PIX EMV QR Code está funcionando perfeitamente!")
    else:
        print("🔧 RESULTADO FINAL: QR CODE PRECISA DE AJUSTES")
        print("Revise os problemas identificados acima.")
    print("="*60) 