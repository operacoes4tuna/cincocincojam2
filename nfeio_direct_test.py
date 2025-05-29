#!/usr/bin/env python
"""
Script para teste direto da API NFE.io com logging em arquivo
"""
import os
import json
import requests
import logging
from datetime import datetime

# Configurar logging para arquivo
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nfeio_test.log', mode='w'),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("nfeio_test")

# Carregar configurações do .env
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
        log.error(f"Erro ao carregar .env: {e}")
        return {}

# Função para testar conexão básica
def test_connection(api_key, company_id):
    log.info("=== TESTANDO CONEXÃO BÁSICA ===")
    
    url = f"https://api.nfe.io/v1/companies/{company_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        log.info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            log.info("✅ Conexão básica OK")
            return True
        else:
            log.error(f"❌ Falha na conexão básica: {response.text}")
            return False
    except Exception as e:
        log.error(f"❌ Erro na conexão: {e}")
        return False

# Função para testar emissão de nota fiscal
def test_invoice_emission(api_key, company_id):
    log.info("=== TESTANDO EMISSÃO DE NOTA FISCAL ===")
    
    url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    # Dados para emissão, formatados conforme a documentação da NFE.io
    invoice_data = {
        "borrower": {
            "name": "Cliente Teste NFE.io",
            "email": "cliente@teste.com",
            "federalTaxNumber": "00000000000",
            "address": {
                "country": "Brasil",
                "postalCode": "01001000",
                "state": "SP", 
                "city": "São Paulo",
                "district": "Centro",
                "street": "Rua Teste",
                "number": "123"
            }
        },
        "serviceCode": "01.07",
        "description": "Serviço de teste para API NFE.io",
        "servicesAmount": 10.00,
        "environment": "Development"
    }
    
    log.info(f"Dados para emissão: {json.dumps(invoice_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, headers=headers, json=invoice_data)
        log.info(f"Status: {response.status_code}")
        log.info(f"Cabeçalhos da resposta: {dict(response.headers)}")
        
        # Tentar extrair o corpo da resposta
        try:
            response_text = response.text
            log.info(f"Corpo da resposta: {response_text}")
            
            if response_text and len(response_text.strip()) > 0:
                try:
                    json_response = response.json()
                    log.info(f"Resposta JSON: {json.dumps(json_response, indent=2, ensure_ascii=False)}")
                except:
                    log.error("A resposta não é um JSON válido")
            else:
                log.warning("Resposta vazia ou quase vazia")
        except Exception as e:
            log.error(f"Erro ao ler resposta: {e}")
        
        if 200 <= response.status_code < 300:
            log.info("✅ Emissão OK")
            return True
        else:
            log.error(f"❌ Falha na emissão: {response.status_code}")
            return False
    except Exception as e:
        log.error(f"❌ Erro na emissão: {e}")
        return False

# Função para testar diferentes formatos de serviceCode
def test_service_code_formats(api_key, company_id):
    log.info("=== TESTANDO DIFERENTES FORMATOS DE CÓDIGO DE SERVIÇO ===")
    
    service_codes = [
        "01.07",  # Com ponto
        "0107",   # Sem ponto
        1.07,     # Número com ponto
        107       # Número inteiro
    ]
    
    for code in service_codes:
        log.info(f"\nTestando serviceCode = {code} ({type(code).__name__})")
        
        url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {api_key}"
        }
        
        invoice_data = {
            "borrower": {
                "name": "Cliente Teste NFE.io",
                "email": "cliente@teste.com",
                "federalTaxNumber": "00000000000",
                "address": {
                    "postalCode": "01001000",
                    "state": "SP", 
                    "city": "São Paulo",
                    "district": "Centro",
                    "street": "Rua Teste",
                    "number": "123"
                }
            },
            "serviceCode": code,
            "description": f"Teste serviceCode={code}",
            "servicesAmount": 10.00,
            "environment": "Development"
        }
        
        try:
            response = requests.post(url, headers=headers, json=invoice_data)
            log.info(f"Status: {response.status_code}")
            
            if 200 <= response.status_code < 300:
                log.info(f"✅ Formato {code} OK!")
                return code
            else:
                log.info(f"❌ Formato {code} falhou")
        except Exception as e:
            log.error(f"❌ Erro: {e}")
    
    return None

# Função para verificar possíveis problemas com nome de campos
def test_field_naming(api_key, company_id):
    log.info("=== TESTANDO DIFERENTES NOMES DE CAMPOS ===")
    
    field_variations = [
        {"original": "serviceCode", "alternative": "cityServiceCode"},
        {"original": "federalTaxNumber", "alternative": "document"}
    ]
    
    for variation in field_variations:
        original = variation["original"]
        alternative = variation["alternative"]
        
        log.info(f"\nTestando {original} vs {alternative}")
        
        # Dados base para o teste
        base_data = {
            "borrower": {
                "name": "Cliente Teste NFE.io",
                "email": "cliente@teste.com",
                "federalTaxNumber": "00000000000",
                "address": {
                    "postalCode": "01001000",
                    "state": "SP", 
                    "city": "São Paulo",
                    "district": "Centro",
                    "street": "Rua Teste",
                    "number": "123"
                }
            },
            "serviceCode": "01.07",
            "description": "Teste de campos",
            "servicesAmount": 10.00,
            "environment": "Development"
        }
        
        # Versão com campo alternativo
        alt_data = base_data.copy()
        
        # Modificar os campos conforme a variação atual
        if original == "serviceCode":
            del alt_data["serviceCode"]
            alt_data[alternative] = "01.07"
        elif original == "federalTaxNumber":
            del alt_data["borrower"]["federalTaxNumber"]
            alt_data["borrower"][alternative] = "00000000000"
        
        url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {api_key}"
        }
        
        try:
            log.info(f"Testando com campo {alternative}")
            response = requests.post(url, headers=headers, json=alt_data)
            log.info(f"Status: {response.status_code}")
            
            if 200 <= response.status_code < 300:
                log.info(f"✅ Campo {alternative} OK!")
                return alternative
            else:
                log.info(f"❌ Campo {alternative} falhou")
        except Exception as e:
            log.error(f"❌ Erro: {e}")
    
    return None

# Função principal
def main():
    log.info("===== INICIANDO TESTES DA API NFE.IO =====")
    
    # Carregar variáveis do .env
    env_vars = load_env()
    api_key = env_vars.get("NFEIO_API_KEY")
    company_id = env_vars.get("NFEIO_COMPANY_ID")
    
    if not api_key or not company_id:
        log.error("API Key ou Company ID não encontrados no .env")
        return
    
    log.info(f"API Key: {api_key[:5]}...{api_key[-5:]} ({len(api_key)} caracteres)")
    log.info(f"Company ID: {company_id}")
    
    # Testar conexão básica
    if not test_connection(api_key, company_id):
        log.error("❌ Conexão básica falhou. Verifique API Key e Company ID.")
        return
    
    # Testar emissão básica
    emission_result = test_invoice_emission(api_key, company_id)
    
    # Se a emissão falhar, testar diferentes formatos de serviceCode
    if not emission_result:
        log.info("Testando formatos alternativos...")
        
        working_service_code = test_service_code_formats(api_key, company_id)
        if working_service_code:
            log.info(f"✅ Formato de serviceCode encontrado: {working_service_code}")
        
        working_field = test_field_naming(api_key, company_id)
        if working_field:
            log.info(f"✅ Nome de campo alternativo encontrado: {working_field}")
    
    log.info("\n===== RECOMENDAÇÕES =====")
    log.info("1. Verifique o arquivo de log em logs/nfeio_test.log para detalhes completos")
    log.info("2. Consulte a documentação atualizada da API NFE.io")
    log.info("3. Corrija o formato de campos conforme os resultados acima")
    log.info("4. Se o problema persistir, entre em contato com o suporte da NFE.io")
    
    log.info("\n===== TESTES CONCLUÍDOS =====")
    log.info(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"Erro fatal: {e}")
        import traceback
        log.error(traceback.format_exc())
