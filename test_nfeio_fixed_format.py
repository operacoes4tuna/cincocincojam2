#!/usr/bin/env python
"""
Script para teste com formato corrigido conforme documentação da NFE.io
"""
import os
import json
import requests
from datetime import datetime

# Criar diretório para resultados se não existir
if not os.path.exists("test_results"):
    os.makedirs("test_results")

# Nome do arquivo de resultado
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result_file = f"test_results/nfeio_fixed_{timestamp}.txt"

# Função para escrever no arquivo de resultados
def log(message):
    with open(result_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
    print(f"LOG: {message[:60]}{'...' if len(message) > 60 else ''}")

# Carregar variáveis do .env
def load_env():
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
        log(f"Erro ao carregar .env: {e}")
        return {}

def test_fixed_format():
    # Carregar credenciais
    env_vars = load_env()
    api_key = env_vars.get("NFEIO_API_KEY")
    company_id = env_vars.get("NFEIO_COMPANY_ID")
    environment = env_vars.get("NFEIO_ENVIRONMENT", "Development")
    
    if not api_key or not company_id:
        log("API Key ou Company ID não encontrados")
        return
    
    log(f"API Key: {api_key[:5]}...{api_key[-5:]} ({len(api_key)} caracteres)")
    log(f"Company ID: {company_id}")
    log(f"Environment: {environment}")
    
    # Verificar conexão básica
    url = f"https://api.nfe.io/v1/companies/{company_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        log(f"Teste de conexão - Status: {response.status_code}")
        
        if response.status_code != 200:
            log("Falha na conexão - verifique credenciais")
            return
    except Exception as e:
        log(f"Erro na conexão: {e}")
        return
    
    # Testar emissão com formato corrigido
    log("\n=== TESTE COM FORMATO CORRIGIDO ===")
    
    # Formato corrigido conforme documentação
    invoice_data = {
        "borrower": {
            "name": "Cliente Teste NFE.io",
            "email": "cliente@teste.com",
            "federalTaxNumber": 11111111111,  # Alterado de "document" para "federalTaxNumber" como número
            "address": {
                "country": "BRA",  # Alterado de "Brasil" para "BRA" conforme padrão ISO
                "postalCode": "01001000", 
                "street": "Rua de Teste",
                "number": "100",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP"
            }
        },
        "serviceCode": "01.07",  # Alterado de "cityServiceCode" para "serviceCode"
        "description": "Teste de emissão com formato corrigido",
        "servicesAmount": 10.00,
        "environment": environment
    }
    
    log(f"Dados para emissão: {json.dumps(invoice_data, indent=2, ensure_ascii=False)}")
    
    url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
    
    try:
        log("Enviando requisição...")
        response = requests.post(url, headers=headers, json=invoice_data, timeout=30)
        
        log(f"Status: {response.status_code}")
        log(f"Headers: {dict(response.headers)}")
        
        content = response.text
        log(f"Conteúdo da resposta ({len(content)} bytes): {content}")
        
        if 200 <= response.status_code < 300:
            log("✅ SUCESSO! Formato corrigido funcionou")
            try:
                json_response = response.json()
                log(f"Resposta JSON: {json.dumps(json_response, indent=2, ensure_ascii=False)}")
            except:
                log("Resposta não é um JSON válido")
        else:
            log("❌ Formato corrigido falhou")
    except Exception as e:
        log(f"Erro na requisição: {e}")
    
    # Modificações recomendadas para o código atual
    log("\n=== MODIFICAÇÕES RECOMENDADAS PARA O CÓDIGO ===")
    log("1. Alterar 'document' para 'federalTaxNumber' - e usar número ao invés de string")
    log("2. Alterar 'cityServiceCode' para 'serviceCode'")
    log("3. Alterar 'country': 'Brasil' para 'country': 'BRA'")
    log("4. Verifique se todos os campos de endereço obrigatórios estão presentes")
    
    log("\n=== TESTE CONCLUÍDO ===")
    log(f"Resultados completos disponíveis em: {result_file}")

if __name__ == "__main__":
    try:
        test_fixed_format()
    except Exception as e:
        print(f"Erro fatal: {e}")
        with open(result_file, "a", encoding="utf-8") as f:
            f.write(f"ERRO FATAL: {e}\n")
            import traceback
            f.write(traceback.format_exc())
