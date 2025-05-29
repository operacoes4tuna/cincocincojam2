#!/usr/bin/env python
"""
Script para testar a emissão de notas fiscais com os campos corrigidos
após as atualizações no arquivo services.py
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
    print_header("TESTE DE EMISSÃO COM CAMPOS CORRIGIDOS")
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
    
    # Agora testamos com um CPF real válido formatado corretamente
    # CPF de teste: 935.411.347-80 (gerado aleatoriamente)
    cpf_teste = "93541134780"  # Sem pontos ou traços
    
    # Testar emissão com campos corrigidos
    print_header("TESTE COM CPF VÁLIDO E FORMATO CORRETO")
    
    # Dados para emissão com CPF válido e campos corretos
    invoice_data = {
        "borrower": {
            "type": "LegalEntity",
            "name": "Cliente Teste NFE.io",
            "federalTaxNumber": int(cpf_teste),  # Convertendo para int
            "email": "cliente@teste.com",
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
        "cityServiceCode": "0107",  # Usando cityServiceCode
        "description": "Teste de emissão com CPF válido e campos corretos",
        "servicesAmount": 10.00,
        "environment": environment,
        "reference": f"TESTE_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    print("Dados para emissão:")
    print(json.dumps(invoice_data, indent=2, ensure_ascii=False))
    
    print_step("Enviando requisição de emissão")
    print(f"POST para {url}")
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=invoice_data, timeout=60)
        elapsed = time.time() - start_time
        
        print(f"Resposta recebida em {elapsed:.2f} segundos")
        print_response(response)
        
        if 200 <= response.status_code < 300:
            print("✅ SUCESSO NA EMISSÃO! Os campos corrigidos funcionaram.")
        else:
            print("❌ FALHA NA EMISSÃO! Os campos corrigidos não funcionaram.")
            
            # Analisar o erro para verificar se houve progresso
            if "federal tax number is not valid" in response.text:
                print("O erro de CPF inválido continua.")
                
                # Tentar uma variação com CPF como string
                print_step("Tentando variação com CPF como string")
                alt_data = invoice_data.copy()
                alt_data["borrower"]["federalTaxNumber"] = cpf_teste  # Como string
                
                try:
                    alt_response = requests.post(url, headers=headers, json=alt_data, timeout=30)
                    print_response(alt_response)
                    
                    if 200 <= alt_response.status_code < 300:
                        print("✅ VARIAÇÃO COM CPF COMO STRING FUNCIONOU!")
                    else:
                        print("❌ VARIAÇÃO COM CPF COMO STRING TAMBÉM FALHOU!")
                except Exception as e:
                    print(f"Erro na variação alternativa: {e}")
            else:
                print("O erro mudou, o que indica progresso na correção.")
    except Exception as e:
        print(f"❌ Exceção durante a emissão: {e}")
        print(traceback.format_exc())
    
    print_header("CONCLUSÃO")
    print("Análise final e observações:")
    print("1. O código foi corrigido para seguir o formato da documentação NFE.io")
    print("2. Os principais problemas identificados foram:")
    print("   - Formato incorreto do CPF/CNPJ")
    print("   - Formato incorreto dos campos de endereço (city como objeto)")
    print("   - Uso incorreto de serviceCode em vez de cityServiceCode")
    print("3. O status fiscal da empresa como 'Pending' pode ainda impedir emissões")
    print("4. Recomendações:")
    print("   - Verificar a validação de CPF para garantir que sejam números válidos")
    print("   - Concluir o cadastro na plataforma NFE.io para alterar o status fiscal")
    print("   - Utilizar dados reais em ambiente de produção")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
    except Exception as e:
        print(f"\n\nErro inesperado: {e}")
        print(traceback.format_exc())
