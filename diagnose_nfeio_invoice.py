#!/usr/bin/env python
"""
Script para diagnosticar problemas na emissão de notas fiscais via API NFE.io
"""

import os
import json
import requests
import logging
import sys
from datetime import datetime

# Configurar logging detalhado para o console
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("nfe_io_diagnostic")

# Carregar variáveis de ambiente do arquivo .env
def load_env(env_file='.env'):
    env_vars = {}
    try:
        with open(env_file, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value.strip('"\'')
        return env_vars
    except Exception as e:
        logger.error(f"Erro ao carregar arquivo .env: {str(e)}")
        return {}

def test_emit_invoice():
    logger.info("\n===== DIAGNÓSTICO DE EMISSÃO DE NOTA FISCAL =====\n")
    
    # Carregar configurações do .env
    env_vars = load_env()
    
    api_key = env_vars.get("NFEIO_API_KEY")
    company_id = env_vars.get("NFEIO_COMPANY_ID")
    environment = env_vars.get("NFEIO_ENVIRONMENT", "Development")
    
    if not api_key or not company_id:
        logger.error("Credenciais não encontradas no arquivo .env")
        return False
    
    logger.info(f"API Key: {api_key[:5]}...{api_key[-5:]} (tamanho: {len(api_key)})")
    logger.info(f"Company ID: {company_id}")
    logger.info(f"Environment: {environment}")
    
    # Configurar a API
    api_url_base = "https://api.nfe.io"
    api_version = "v1"
    base_url = f"{api_url_base}/{api_version}"
    
    # Dados para uma nota fiscal de teste
    # Usando dados mais completos e verificando formato
    invoice_data = {
        "borrower": {
            "name": "Cliente Teste NFE.io",
            "email": "cliente@teste.com",
            "document": "00000000000",  # CPF sem formatação
            "type": "NaturalPerson",    # Pessoa Física
            "address": {
                "country": "Brasil",
                "postalCode": "01001000",  # CEP sem hífen
                "state": "SP", 
                "city": "São Paulo",
                "district": "Centro",
                "street": "Rua Teste",
                "number": "123"
            }
        },
        "cityServiceCode": "0107",  # Código para serviços educacionais
        "description": "Serviço de teste para API NFE.io",
        "servicesAmount": 10.00,
        "environment": environment,
        "reference": f"TESTE_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }
    
    # Endpoint para emissão de nota fiscal
    endpoint = f"companies/{company_id}/serviceinvoices"
    url = f"{base_url}/{endpoint}"
    
    logger.info(f"Fazendo requisição POST para {url}")
    logger.info(f"Dados enviados (formatados): \n{json.dumps(invoice_data, indent=2, ensure_ascii=False)}")
    
    # Verificar formato dos dados
    logger.info("\n----- VERIFICAÇÃO DE FORMATO DE DADOS -----")
    for field, value in invoice_data.items():
        if isinstance(value, dict):
            logger.info(f"Campo '{field}' é um objeto")
            for subfield, subvalue in value.items():
                logger.info(f"  Subcampo '{subfield}' = {type(subvalue).__name__}: {subvalue}")
        else:
            logger.info(f"Campo '{field}' = {type(value).__name__}: {value}")
    
    # Preparar headers para autenticação
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    logger.info("\n----- ENVIANDO REQUISIÇÃO -----")
    try:
        # Converter para JSON e verificar
        request_json = json.dumps(invoice_data)
        logger.info(f"JSON válido: {len(request_json)} bytes")
        
        # Fazer a requisição com timeout explícito
        logger.debug("Enviando requisição...")
        start_time = datetime.now()
        response = requests.post(url, headers=headers, json=invoice_data, timeout=30)
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        logger.info(f"Resposta recebida em {elapsed:.2f} segundos")
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Headers da resposta: {dict(response.headers)}")
        
        # Analisar a resposta
        logger.info("\n----- ANÁLISE DA RESPOSTA -----")
        logger.info(f"Conteúdo bruto da resposta: {response.text}")
        logger.info(f"Tamanho da resposta: {len(response.text)} bytes")
        
        if 200 <= response.status_code < 300:
            try:
                json_response = response.json()
                logger.info("Resposta JSON válida:")
                logger.info(json.dumps(json_response, indent=2, ensure_ascii=False))
                return True
            except ValueError as e:
                logger.error(f"Resposta não é um JSON válido: {str(e)}")
                return False
        else:
            logger.error(f"Erro HTTP {response.status_code}")
            try:
                error_json = response.json()
                logger.error(f"Detalhes do erro (JSON): {json.dumps(error_json, indent=2, ensure_ascii=False)}")
            except:
                logger.error(f"Resposta não é um JSON válido")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Timeout na requisição (30 segundos)")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erro de conexão: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Exceção não esperada: {str(e)}")
        return False
        
    return False

if __name__ == "__main__":
    try:
        test_emit_invoice()
    except Exception as e:
        logger.error(f"Erro fatal: {str(e)}")
    finally:
        logger.info("\n===== FIM DO DIAGNÓSTICO =====")
