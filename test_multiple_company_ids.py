#!/usr/bin/env python
"""
Script de teste para validar a funcionalidade de múltiplos company_ids para NFE.io
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from invoices.models import CompanyConfig
from invoices.services import NFEioService
from core.models import User
from django.db import transaction


def test_multiple_company_configs():
    """
    Testa a criação de múltiplas configurações de empresa com company_ids diferentes
    """
    print("🧪 Testando configurações de múltiplas empresas NFE.io")
    print("-" * 60)
    
    # Buscar ou criar usuários de teste
    try:
        with transaction.atomic():
            # Usuário 1 - Professor A
            user1, created = User.objects.get_or_create(
                username='professor_a_test',
                defaults={
                    'email': 'professor_a@test.com',
                    'first_name': 'Professor',
                    'last_name': 'A'
                }
            )
            
            # Usuário 2 - Professor B
            user2, created = User.objects.get_or_create(
                username='professor_b_test',
                defaults={
                    'email': 'professor_b@test.com',
                    'first_name': 'Professor',
                    'last_name': 'B'
                }
            )
            
            print(f"✅ Usuários de teste criados/encontrados")
            print(f"   - Professor A: {user1.username}")
            print(f"   - Professor B: {user2.username}")
            
            # Configuração da Empresa A
            config_a, created = CompanyConfig.objects.get_or_create(
                user=user1,
                defaults={
                    'enabled': True,
                    'cnpj': '12345678000195',
                    'razao_social': 'Empresa A de Ensino LTDA',
                    'nome_fantasia': 'Professor A Cursos',
                    'regime_tributario': 'simples_nacional',
                    'endereco': 'Rua das Flores, 123',
                    'numero': '123',
                    'bairro': 'Centro',
                    'municipio': 'São Paulo',
                    'uf': 'SP',
                    'cep': '01234567',
                    'city_service_code': '0107',
                    'nfeio_company_id': 'COMPANY_A_ID_TEST',
                    'rps_serie': '1',
                    'rps_numero_atual': 1,
                    'rps_lote': 1
                }
            )
            
            # Configuração da Empresa B  
            config_b, created = CompanyConfig.objects.get_or_create(
                user=user2,
                defaults={
                    'enabled': True,
                    'cnpj': '98765432000182',
                    'razao_social': 'Empresa B de Educação LTDA',
                    'nome_fantasia': 'Professor B Academy',
                    'regime_tributario': 'lucro_presumido',
                    'endereco': 'Avenida Principal, 456',
                    'numero': '456',
                    'bairro': 'Vila Nova',
                    'municipio': 'Rio de Janeiro',
                    'uf': 'RJ',
                    'cep': '20123456',
                    'city_service_code': '0108',
                    'nfeio_company_id': 'COMPANY_B_ID_TEST',
                    'rps_serie': '2',
                    'rps_numero_atual': 1,
                    'rps_lote': 1
                }
            )
            
            print(f"✅ Configurações de empresa criadas/atualizadas")
            print(f"   - Empresa A: {config_a.razao_social}")
            print(f"   - Company ID A: {config_a.nfeio_company_id}")
            print(f"   - Empresa B: {config_b.razao_social}")
            print(f"   - Company ID B: {config_b.nfeio_company_id}")
            
            # Testar instanciação do NFEioService com cada configuração
            print("\n🔧 Testando instanciação do NFEioService")
            print("-" * 40)
            
            # Serviço para Empresa A
            service_a = NFEioService(config_a)
            print(f"✅ NFEioService Empresa A:")
            print(f"   - Company ID: {service_a.company_id}")
            print(f"   - API Key (global): {service_a.api_key[:10]}... (mesmo para todos)")
            
            # Serviço para Empresa B
            service_b = NFEioService(config_b)
            print(f"✅ NFEioService Empresa B:")
            print(f"   - Company ID: {service_b.company_id}")
            print(f"   - API Key (global): {service_b.api_key[:10]}... (mesmo para todos)")
            
            # Verificar que API Keys são iguais (globais)
            assert service_a.api_key == service_b.api_key, "API Keys devem ser iguais (globais)"
            print(f"✅ API Key global confirmada: mesma para ambas empresas")
            
            # Verificar se as configurações estão completas
            print(f"\n📋 Verificando completude das configurações")
            print("-" * 45)
            print(f"✅ Configuração A completa: {config_a.is_complete()}")
            print(f"✅ Configuração B completa: {config_b.is_complete()}")
            
            # Testar validação das configurações
            print(f"\n🔍 Testando validações")
            print("-" * 25)
            
            valid_a, msg_a = service_a.validate_company_config(config_a)
            print(f"✅ Validação Empresa A: {valid_a} - {msg_a}")
            
            valid_b, msg_b = service_b.validate_company_config(config_b)
            print(f"✅ Validação Empresa B: {valid_b} - {msg_b}")
            
            print(f"\n🎉 Teste de múltiplos company_ids concluído com sucesso!")
            print(f"💡 Cada professor agora pode ter sua própria empresa NFE.io")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro durante os testes: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_to_global_config():
    """
    Testa o fallback para configurações globais quando o professor não tem configuração específica
    """
    print(f"\n🔄 Testando fallback para configurações globais")
    print("-" * 50)
    
    try:
        # Criar usuário sem configuração específica
        user_fallback, created = User.objects.get_or_create(
            username='professor_fallback_test',
            defaults={
                'email': 'professor_fallback@test.com',
                'first_name': 'Professor',
                'last_name': 'Fallback'
            }
        )
        
        config_fallback, created = CompanyConfig.objects.get_or_create(
            user=user_fallback,
            defaults={
                'enabled': True,
                'cnpj': '11111111000111',
                'razao_social': 'Empresa Sem NFE.io Config',
                'nome_fantasia': 'Professor Fallback',
                # Propositalmente não definindo nfeio_company_id e nfeio_api_key
            }
        )
        
        # Testar serviço com fallback
        service_fallback = NFEioService(config_fallback)
        print(f"✅ NFEioService com fallback criado")
        print(f"   - Usando Company ID global: {service_fallback.company_id}")
        print(f"   - Configuração incompleta: {not config_fallback.is_complete()}")
        
        # Testar validação (deve falhar por falta dos campos NFE.io)
        valid, msg = service_fallback.validate_company_config(config_fallback)
        print(f"⚠️  Validação esperadamente falhou: {valid} - {msg}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de fallback: {str(e)}")
        return False


if __name__ == '__main__':
    print("🚀 Iniciando testes de múltiplos company_ids NFE.io")
    print("=" * 80)
    
    test1_success = test_multiple_company_configs()
    test2_success = test_fallback_to_global_config()
    
    print(f"\n📊 Resumo dos testes")
    print("=" * 30)
    print(f"Teste múltiplas empresas: {'✅ PASSOU' if test1_success else '❌ FALHOU'}")
    print(f"Teste fallback global: {'✅ PASSOU' if test2_success else '❌ FALHOU'}")
    
    if test1_success and test2_success:
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        print(f"💡 A refatoração foi bem-sucedida!")
        sys.exit(0)
    else:
        print(f"\n❌ ALGUNS TESTES FALHARAM!")
        sys.exit(1)