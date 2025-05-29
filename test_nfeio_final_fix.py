#!/usr/bin/env python
"""
Script final para testar a emissão de notas fiscais com os campos corrigidos
e o tipo de pessoa correto.
"""
import os
import json
import requests
import time
from datetime import datetime
import traceback

def print_header(title):
    """Imprime um cabeçalho formatado no terminal"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def print_step(step):
    """Imprime uma etapa no terminal"""
    print(f"\n--> {step}")

def print_response(response):
    """Imprime uma resposta de API no terminal"""
    print(f"Status: {response.status_code}")
    print(f"Headers:\n{json.dumps(dict(response.headers), indent=2)}")
    
    content_text = response.text
    content_length = len(content_text)
    
    print(f"Conteúdo ({content_length} bytes):")
    if content_length > 0:
        # Mostrar todo o conteúdo da resposta se for pequeno
        if content_length < 1000:
            print(content_text)
        else:
            # Caso contrário, mostrar início e fim
            print(content_text[:500] + "\n...\n" + content_text[-500:])
        
        # Tentar decodificar como JSON se possível
        try:
            json_content = response.json()
            print("\nJSON formatado:")
            print(json.dumps(json_content, indent=2, ensure_ascii=False))
        except:
            print("\nA resposta não é um JSON válido")
    else:
        print("(Conteúdo vazio)")

def load_env():
    """Carrega variáveis do arquivo .env"""
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value.strip('"\'')
        return env_vars
    except Exception as e:
        print(f"Erro ao carregar .env: {e}")
        return {}

def main():
    print_header("TESTE FINAL COM CORREÇÕES COMPLETAS")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Carregar variáveis de ambiente
    print_step("Carregando configurações")
    env_vars = load_env()
    api_key = env_vars.get("NFEIO_API_KEY")
    company_id = env_vars.get("NFEIO_COMPANY_ID")
    environment = env_vars.get("NFEIO_ENVIRONMENT", "Development")
    
    if not api_key or not company_id:
        print("❌ API Key ou Company ID não encontrados no arquivo .env")
        return
    
    print(f"API Key: {api_key[:5]}...{api_key[-5:]} ({len(api_key)} caracteres)")
    print(f"Company ID: {company_id}")
    print(f"Environment: {environment}")
    
    # Configuração da API
    url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    # CPF de teste para pessoa física: 935.411.347-80 (gerado aleatoriamente)
    cpf_teste = "93541134780"  # Sem pontos ou traços
    
    # CNPJ de teste para pessoa jurídica: 65.658.849/0001-00 (gerado aleatoriamente)
    cnpj_teste = "65658849000100"  # Sem pontos, traços ou barras
    
    # Teste 1: Pessoa Física com CPF
    print_header("TESTE 1: PESSOA FÍSICA COM CPF")
    
    invoice_data_1 = {
        "borrower": {
            "type": "NaturalPerson",  # Pessoa Física
            "name": "Cliente Teste Pessoa Física",
            "federalTaxNumber": int(cpf_teste),  # CPF como número
            "email": "cliente.pf@teste.com",
            "address": {
                "country": "BRA",
                "postalCode": "01001000",
                "street": "Rua de Teste",
                "number": "100",
                "additionalInformation": "Andar 1",
                "district": "Centro",
                "city": {
                    "code": "3550308",  # Código IBGE para São Paulo
                    "name": "São Paulo"
                },
                "state": "SP"
            }
        },
        "cityServiceCode": "0107",
        "description": "Teste de emissão para pessoa física com CPF",
        "servicesAmount": 10.00,
        "environment": environment,
        "reference": f"TESTE_PF_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    print("Dados para emissão (Pessoa Física):")
    print(json.dumps(invoice_data_1, indent=2, ensure_ascii=False))
    
    print_step("Enviando requisição para pessoa física")
    print(f"POST para {url}")
    
    try:
        response_1 = requests.post(url, headers=headers, json=invoice_data_1, timeout=60)
        print_response(response_1)
        
        if 200 <= response_1.status_code < 300:
            print("✅ SUCESSO NA EMISSÃO PARA PESSOA FÍSICA!")
        else:
            print("❌ FALHA NA EMISSÃO PARA PESSOA FÍSICA")
    except Exception as e:
        print(f"❌ Exceção durante a emissão para pessoa física: {e}")
    
    # Teste 2: Pessoa Jurídica com CNPJ
    print_header("TESTE 2: PESSOA JURÍDICA COM CNPJ")
    
    invoice_data_2 = {
        "borrower": {
            "type": "LegalEntity",  # Pessoa Jurídica
            "name": "Empresa Teste LTDA",
            "federalTaxNumber": int(cnpj_teste),  # CNPJ como número
            "email": "contato@empresateste.com.br",
            "address": {
                "country": "BRA",
                "postalCode": "04538133",
                "street": "Avenida Brigadeiro Faria Lima",
                "number": "3477",
                "additionalInformation": "Torre Norte, 14º andar",
                "district": "Itaim Bibi",
                "city": {
                    "code": "3550308",
                    "name": "São Paulo"
                },
                "state": "SP"
            }
        },
        "cityServiceCode": "0107",
        "description": "Teste de emissão para pessoa jurídica com CNPJ",
        "servicesAmount": 50.00,
        "environment": environment,
        "reference": f"TESTE_PJ_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    print("Dados para emissão (Pessoa Jurídica):")
    print(json.dumps(invoice_data_2, indent=2, ensure_ascii=False))
    
    print_step("Enviando requisição para pessoa jurídica")
    print(f"POST para {url}")
    
    try:
        response_2 = requests.post(url, headers=headers, json=invoice_data_2, timeout=60)
        print_response(response_2)
        
        if 200 <= response_2.status_code < 300:
            print("✅ SUCESSO NA EMISSÃO PARA PESSOA JURÍDICA!")
        else:
            print("❌ FALHA NA EMISSÃO PARA PESSOA JURÍDICA")
    except Exception as e:
        print(f"❌ Exceção durante a emissão para pessoa jurídica: {e}")
    
    print_header("MODIFICAÇÕES NECESSÁRIAS NO CÓDIGO")
    print("Com base nos testes, as seguintes alterações devem ser feitas no arquivo services.py:")
    print("\n1. Verificar o tipo do tomador de serviço:")
    print('   - Se for pessoa física (CPF), usar "type": "NaturalPerson"')
    print('   - Se for pessoa jurídica (CNPJ), usar "type": "LegalEntity"')
    print("\n2. Garantir que o federalTaxNumber seja compatível com o tipo:")
    print("   - Para pessoas físicas, enviar CPF (11 dígitos)")
    print("   - Para pessoas jurídicas, enviar CNPJ (14 dígitos)")
    print("\n3. Garantir que o campo city seja um objeto com code e name")
    print("\n4. Usar cityServiceCode em vez de serviceCode")
    
    print_header("CONCLUSÃO FINAL")
    print("A API NFE.io exige consistência entre o tipo de pessoa e o documento fiscal:")
    print("1. O status fiscal 'Pending' da empresa pode ainda impedir emissões em produção")
    print("2. É necessário verificar se o estudante é pessoa física ou jurídica")
    print("3. O formato do endereço precisa seguir exatamente o padrão da API")
    print("4. Recomenda-se finalizar a configuração da empresa na plataforma NFE.io")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
    except Exception as e:
        print(f"\n\nErro inesperado: {e}")
        print(traceback.format_exc())
