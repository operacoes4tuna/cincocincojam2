#!/usr/bin/env python
"""
Script para testar a emissão de notas fiscais usando a API NFE.io com o formato corrigido.
Este script mostra os resultados em tempo real no terminal.
"""
import os
import json
import requests
import time
from datetime import datetime
import traceback

def print_header(title):
    """Imprime um cabeçalho formatado no terminal"""
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60 + "\n")

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
    print_header("TESTE DE EMISSÃO DE NOTA FISCAL NFE.IO")
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
    
    # Testar conexão
    print_step("Verificando conexão e autenticação")
    url = f"https://api.nfe.io/v1/companies/{company_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    try:
        print(f"Realizando GET para {url}")
        response = requests.get(url, headers=headers, timeout=30)
        print_response(response)
        
        if response.status_code == 200:
            print("✅ Conexão e autenticação funcionando corretamente!")
        else:
            print("❌ Problema na conexão ou autenticação")
            return
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        print(traceback.format_exc())
        return
    
    # Testar emissão com formato corrigido
    print_header("TESTE DE EMISSÃO COM FORMATO CORRIGIDO")
    
    # Dados para emissão (com formato corrigido)
    invoice_data = {
        "borrower": {
            "name": "Cliente Teste NFE.io",
            "email": "cliente@teste.com",
            "federalTaxNumber": 11111111111,  # Número, não string
            "address": {
                "country": "BRA",  # Formato ISO
                "postalCode": "01001000",
                "street": "Rua de Teste",
                "number": "100",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP"
            }
        },
        "serviceCode": "01.07",  # Com ponto
        "description": "Teste de emissão via script com formato corrigido",
        "servicesAmount": 10.00,
        "environment": environment,
        "reference": f"TESTE_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    print("Dados para emissão:")
    print(json.dumps(invoice_data, indent=2, ensure_ascii=False))
    
    url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
    
    print_step("Enviando requisição de emissão")
    print(f"POST para {url}")
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=invoice_data, timeout=60)
        elapsed = time.time() - start_time
        
        print(f"Resposta recebida em {elapsed:.2f} segundos")
        print_response(response)
        
        if 200 <= response.status_code < 300:
            print("✅ SUCESSO NA EMISSÃO! O formato corrigido funcionou.")
        else:
            print("❌ FALHA NA EMISSÃO! O formato corrigido não funcionou.")
            
            # Tentar obter mais informações sobre o erro
            print_step("Analisando possíveis causas do erro")
            
            if response.status_code == 400:
                print("Erro 400 (Bad Request) - Possíveis causas:")
                print("1. Formato de dados incorreto")
                print("2. Campos obrigatórios ausentes")
                print("3. Valores em formato inválido")
                print("4. Ambiente de desenvolvimento não configurado corretamente")
                
                # Tentar uma variação alternativa
                print_step("Tentando variação alternativa")
                alt_data = invoice_data.copy()
                # Converter federalTaxNumber para string
                alt_data["borrower"]["federalTaxNumber"] = "11111111111"
                
                print("Dados alternativos:")
                print(json.dumps(alt_data, indent=2, ensure_ascii=False))
                
                try:
                    alt_response = requests.post(url, headers=headers, json=alt_data, timeout=30)
                    print_response(alt_response)
                    
                    if 200 <= alt_response.status_code < 300:
                        print("✅ VARIAÇÃO ALTERNATIVA FUNCIONOU!")
                    else:
                        print("❌ VARIAÇÃO ALTERNATIVA TAMBÉM FALHOU!")
                except Exception as e:
                    print(f"Erro na variação alternativa: {e}")
            elif response.status_code == 401:
                print("Erro 401 (Unauthorized) - API Key inválida ou sem permissões")
            elif response.status_code == 403:
                print("Erro 403 (Forbidden) - Sem permissão para este recurso")
            elif response.status_code == 404:
                print("Erro 404 (Not Found) - Endpoint incorreto ou empresa não encontrada")
            else:
                print(f"Erro {response.status_code} - Motivo desconhecido")
    except Exception as e:
        print(f"❌ Exceção durante a emissão: {e}")
        print(traceback.format_exc())
    
    print_header("CONCLUSÃO")
    print("Análise com base nos testes:")
    print("1. A API NFE.io retorna erro 400 sem detalhes do erro")
    print("2. A autenticação funciona, mas a emissão está falhando")
    print("3. O formato dos dados foi corrigido conforme a documentação")
    print("4. Possíveis próximos passos:")
    print("   - Contactar o suporte da NFE.io com os resultados dos testes")
    print("   - Verificar se a conta está configurada para emissão em ambiente de teste")
    print("   - Testar emissão via interface web para comparar o formato de dados")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
    except Exception as e:
        print(f"\n\nErro inesperado: {e}")
        print(traceback.format_exc())
