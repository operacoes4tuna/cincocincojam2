#!/usr/bin/env python
"""
Script simples para testar a API NFE.io com saída para arquivo
"""
import os
import json
import requests
from datetime import datetime

# Criar diretório para logs se não existir
if not os.path.exists("test_results"):
    os.makedirs("test_results")

# Nome do arquivo de resultado baseado no timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result_file = f"test_results/nfeio_test_{timestamp}.txt"

# Função para escrever no arquivo de resultados
def log(message):
    with open(result_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
    # Também exibir no console uma versão simplificada
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

# Função principal
def main():
    log("=== INICIANDO TESTE SIMPLIFICADO NFE.IO ===")
    
    # Carregar credenciais
    env_vars = load_env()
    api_key = env_vars.get("NFEIO_API_KEY")
    company_id = env_vars.get("NFEIO_COMPANY_ID")
    
    if not api_key or not company_id:
        log("API Key ou Company ID não encontrados")
        return
    
    log(f"API Key: {api_key[:5]}...{api_key[-5:]} ({len(api_key)} caracteres)")
    log(f"Company ID: {company_id}")
    
    # Testar conexão básica
    log("\n--- TESTE DE CONEXÃO BÁSICA ---")
    
    url = f"https://api.nfe.io/v1/companies/{company_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        log(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            log("Conexão OK - Autenticação funciona")
        else:
            log(f"Erro na conexão: {response.text}")
            return
    except Exception as e:
        log(f"Exceção na conexão: {e}")
        return
    
    # Testar emissão básica
    log("\n--- TESTE DE EMISSÃO BÁSICA ---")
    
    # Criar dados conforme documentação
    invoice_data = {
        "borrower": {
            "name": "Cliente Teste NFE.io",
            "federalTaxNumber": 11111111111,  # Número, não string
            "address": {
                "street": "Rua de Teste",
                "number": "100",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP"
            }
        },
        "serviceCode": "01.07",  # Com ponto conforme documentação
        "description": "Teste de emissão via script",
        "servicesAmount": 10.00
    }
    
    url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
    
    log(f"Enviando dados: {json.dumps(invoice_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, headers=headers, json=invoice_data, timeout=30)
        
        log(f"Status: {response.status_code}")
        log(f"Headers: {response.headers}")
        
        # Tentar obter e salvar o corpo da resposta
        try:
            log(f"Conteúdo da resposta ({len(response.text)} bytes):")
            log(response.text)
            
            # Tentar decodificar como JSON se possível
            if response.text:
                try:
                    json_data = response.json()
                    log(f"JSON decodificado: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
                except:
                    log("A resposta não é um JSON válido")
        except Exception as e:
            log(f"Erro ao processar corpo da resposta: {e}")
        
        if 200 <= response.status_code < 300:
            log("SUCESSO NA EMISSÃO!")
        else:
            log("FALHA NA EMISSÃO")
            
            # Testar um formato alternativo
            log("\n--- TESTE COM FORMATO ALTERNATIVO ---")
            
            alt_invoice_data = {
                "borrower": {
                    "name": "Cliente Teste Alt",
                    "federalTaxNumber": "11111111111",  # String, não número
                    "address": {
                        "street": "Rua de Teste",
                        "number": "100",
                        "district": "Centro",
                        "city": "São Paulo",
                        "state": "SP"
                    }
                },
                "serviceCode": "0107",  # Sem ponto
                "description": "Teste de emissão formato alternativo",
                "servicesAmount": 10.00
            }
            
            log(f"Enviando dados alternativos: {json.dumps(alt_invoice_data, indent=2, ensure_ascii=False)}")
            
            try:
                alt_response = requests.post(url, headers=headers, json=alt_invoice_data, timeout=30)
                
                log(f"Status alt: {alt_response.status_code}")
                log(f"Headers alt: {alt_response.headers}")
                log(f"Conteúdo alt: {alt_response.text}")
                
                if 200 <= alt_response.status_code < 300:
                    log("SUCESSO COM FORMATO ALTERNATIVO!")
                else:
                    log("FALHA COM FORMATO ALTERNATIVO")
            except Exception as e:
                log(f"Exceção no teste alternativo: {e}")
    except Exception as e:
        log(f"Exceção na emissão: {e}")
    
    # Resultado final
    log("\n=== TESTE CONCLUÍDO ===")
    log(f"Resultados completos disponíveis em: {result_file}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erro fatal: {e}")
        with open(result_file, "a", encoding="utf-8") as f:
            f.write(f"ERRO FATAL: {e}\n")
            import traceback
            f.write(traceback.format_exc())
