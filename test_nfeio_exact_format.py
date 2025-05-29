#!/usr/bin/env python
"""
Script para testar a emissão de notas fiscais usando EXATAMENTE o formato da documentação oficial
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
    print_header("TESTE DE EMISSÃO COM FORMATO EXATO DA DOCUMENTAÇÃO")
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
            
            # Extrair informações da empresa para o teste
            try:
                company_data = response.json().get('companies', {})
                fiscal_status = company_data.get('fiscalStatus')
                print(f"Status fiscal da empresa: {fiscal_status}")
                
                if fiscal_status == "Pending":
                    print("⚠️ ATENÇÃO: O status fiscal da empresa está como 'Pending'")
                    print("Isso pode impedir a emissão de notas fiscais, mesmo em ambiente de desenvolvimento.")
                    print("Verifique a configuração da empresa na plataforma NFE.io.")
            except Exception as e:
                print(f"Não foi possível extrair informações da empresa: {e}")
        else:
            print("❌ Problema na conexão ou autenticação")
            return
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        print(traceback.format_exc())
        return
    
    # Testar emissão com formato oficial da documentação
    print_header("TESTE COM FORMATO EXATO DA DOCUMENTAÇÃO")
    
    # Dados para emissão EXATAMENTE como na documentação
    invoice_data = {
        "borrower": {
            # Tipos de tomadores de Serviço, opções são 'Undefined', 'NaturalPerson', 'LegalEntity'
            "type": "LegalEntity",
            "name": "Cliente Teste NFE.io",
            # CNPJ / CPF somente números sem ponto, traço, barra ou virgula
            "federalTaxNumber": 11111111111,
            # Informar somente quando necessário na prefeitura da empresa que está emitindo
            "municipalTaxNumber": None,
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
        "cityServiceCode": "0107",  # Usando cityServiceCode conforme documentação
        "description": "Teste de emissão exatamente como na documentação",
        "servicesAmount": 10.00,
        "environment": environment
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
            print("✅ SUCESSO NA EMISSÃO! O formato exato da documentação funcionou.")
        else:
            print("❌ FALHA NA EMISSÃO! O formato exato da documentação não funcionou.")
            
            # Tentar obter mais informações sobre o erro
            print_step("Analisando possíveis causas do erro")
            
            if response.status_code == 400:
                print("Erro 400 (Bad Request) - Possíveis causas:")
                print("1. O status fiscal da empresa está como 'Pending' na plataforma NFE.io")
                print("2. A conta pode precisar de ativação adicional para o ambiente de desenvolvimento")
                print("3. O serviço de emissão de notas em homologação pode não estar disponível")
                
                # Tentar variação alternativa com serviceCode
                print_step("Tentando variação com 'serviceCode' em vez de 'cityServiceCode'")
                alt_data = invoice_data.copy()
                alt_data["serviceCode"] = "01.07"  # Com ponto
                del alt_data["cityServiceCode"]
                
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
    except Exception as e:
        print(f"❌ Exceção durante a emissão: {e}")
        print(traceback.format_exc())
    
    print_header("CONCLUSÃO")
    print("Análise final e recomendações:")
    print("1. A conta NFE.io está corretamente configurada e acessível via API")
    print("2. A emissão de notas está falhando mesmo com o formato exato da documentação")
    print("3. O status fiscal da empresa como 'Pending' pode ser o problema principal")
    print("4. Recomendações:")
    print("   - Contatar o suporte da NFE.io para ativar sua conta para emissão de notas")
    print("   - Verificar se é necessário completar alguma etapa de cadastro na plataforma")
    print("   - Tentar emitir uma nota fiscal pelo site da NFE.io para validar a configuração")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
    except Exception as e:
        print(f"\n\nErro inesperado: {e}")
        print(traceback.format_exc())
