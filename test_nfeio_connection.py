#!/usr/bin/env python
"""
Script para testar a conexão com a API NFE.io
Este script faz uma requisição básica para a API NFE.io para verificar se as credenciais
estão corretas e se a conexão está funcionando.
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

logger = logging.getLogger("nfe_io_test")

# Carregar variáveis de ambiente do arquivo .env
def load_env(env_file='.env'):
    env_vars = {}
    try:
        with open(env_file, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                env_vars[key] = value.strip('"\'')
        return env_vars
    except Exception as e:
        logger.error(f"Erro ao carregar arquivo .env: {str(e)}")
        return {}

# Função principal de teste
def test_nfeio_connection():
    logger.info("Iniciando teste de conexão com a API NFE.io")
    
    # Carregar configurações do .env
    env_vars = load_env()
    
    api_key = env_vars.get("NFEIO_API_KEY")
    company_id = env_vars.get("NFEIO_COMPANY_ID")
    environment = env_vars.get("NFEIO_ENVIRONMENT", "Development")
    
    if not api_key or not company_id:
        logger.error("Credenciais não encontradas no arquivo .env")
        logger.error(f"API Key: {'*' * 5 if api_key else 'Não encontrada'}")
        logger.error(f"Company ID: {company_id if company_id else 'Não encontrado'}")
        return False
    
    logger.info(f"API Key carregada: {api_key[:5]}...{api_key[-5:]} (tamanho: {len(api_key)})")
    logger.info(f"Company ID: {company_id}")
    logger.info(f"Environment: {environment}")
    
    # Configurar a API
    api_url_base = "https://api.nfe.io"
    api_version = "v1"
    base_url = f"{api_url_base}/{api_version}"
    
    # Tentar obter informações da empresa
    endpoint = f"companies/{company_id}"
    url = f"{base_url}/{endpoint}"
    
    logger.info(f"Fazendo requisição GET para {url}")
    
    # Preparar headers para autenticação
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    try:
        # Fazer a requisição
        logger.debug("Enviando requisição...")
        start_time = datetime.now()
        response = requests.get(url, headers=headers)
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        logger.info(f"Resposta recebida em {elapsed:.2f} segundos")
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Headers da resposta: {dict(response.headers)}")
        
        # Analisar a resposta
        if 200 <= response.status_code < 300:
            try:
                json_response = response.json()
                logger.info("Resposta válida recebida:")
                logger.info(json.dumps(json_response, indent=2))
                return True
            except ValueError:
                logger.error(f"Resposta não é um JSON válido: {response.text}")
                return False
        else:
            logger.error(f"Erro na requisição: {response.status_code}")
            logger.error(f"Conteúdo da resposta: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exceção ao fazer requisição: {str(e)}")
        return False
        
    return False

# Testar emissão de nota fiscal com dados mínimos
def test_emit_invoice():
    logger.info("\n\n===== TESTE DE EMISSÃO DE NOTA FISCAL =====\n")
    
    # Carregar configurações do .env
    env_vars = load_env()
    
    api_key = env_vars.get("NFEIO_API_KEY")
    company_id = env_vars.get("NFEIO_COMPANY_ID")
    environment = env_vars.get("NFEIO_ENVIRONMENT", "Development")
    
    if not api_key or not company_id:
        logger.error("Credenciais não encontradas no arquivo .env")
        return False
    
    # Configurar a API
    api_url_base = "https://api.nfe.io"
    api_version = "v1"
    base_url = f"{api_url_base}/{api_version}"
    
    # Dados mínimos para uma nota fiscal de teste
    invoice_data = {
        "borrower": {
            "name": "Cliente Teste",
            "email": "cliente@teste.com",
            "document": "00000000000",
            "address": {
                "country": "Brasil",
                "state": "SP",
                "city": "São Paulo",
                "district": "Centro",
                "street": "Rua Teste",
                "number": "123",
                "postalCode": "00000000"
            }
        },
        "cityServiceCode": "0107",  # Código para serviços educacionais
        "description": "Serviço de teste para API NFE.io",
        "servicesAmount": 10.00,
        "environment": environment,
        "reference": f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "additionalInformation": "Teste de emissão via script Python"
    }
    
    # Endpoint para emissão de nota fiscal
    endpoint = f"companies/{company_id}/serviceinvoices"
    url = f"{base_url}/{endpoint}"
    
    logger.info(f"Fazendo requisição POST para {url}")
    logger.info(f"Dados enviados: {json.dumps(invoice_data, indent=2)}")
    
    # Preparar headers para autenticação
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {api_key}"
    }
    
    try:
        # Fazer a requisição
        logger.debug("Enviando requisição...")
        start_time = datetime.now()
        response = requests.post(url, headers=headers, json=invoice_data)
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        logger.info(f"Resposta recebida em {elapsed:.2f} segundos")
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Headers da resposta: {dict(response.headers)}")
        
        # Analisar a resposta
        if 200 <= response.status_code < 300:
            try:
                json_response = response.json()
                logger.info("Nota fiscal emitida com sucesso:")
                logger.info(json.dumps(json_response, indent=2))
                return True
            except ValueError:
                logger.error(f"Resposta não é um JSON válido: {response.text}")
                return False
        else:
            logger.error(f"Erro na emissão: {response.status_code}")
            logger.error(f"Conteúdo da resposta: {response.text}")
            
            # Tentar decodificar o corpo da resposta se for JSON
            try:
                error_json = response.json()
                logger.error(f"Detalhes do erro: {json.dumps(error_json, indent=2)}")
            except:
                pass
                
            return False
            
    except Exception as e:
        logger.error(f"Exceção ao fazer requisição: {str(e)}")
        return False
        
    return False

if __name__ == "__main__":
    logger.info("====== TESTE DE CONEXÃO COM A API NFE.IO ======")
    
    # Testar conexão básica
    connection_success = test_nfeio_connection()
    logger.info(f"\nResultado do teste de conexão: {'SUCESSO' if connection_success else 'FALHA'}\n")
    
    # Se a conexão básica funcionar, tentar emitir uma nota fiscal de teste
    if connection_success:
        emission_success = test_emit_invoice()
        logger.info(f"\nResultado do teste de emissão: {'SUCESSO' if emission_success else 'FALHA'}\n")
    else:
        logger.warning("Ignorando teste de emissão devido a falha na conexão básica")
    
    logger.info("====== FIM DOS TESTES ======")
