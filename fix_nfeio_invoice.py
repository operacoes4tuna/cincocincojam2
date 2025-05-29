#!/usr/bin/env python
"""
Script para solucionar problemas de emissão de notas fiscais via API NFE.io
Este script isola completamente o problema da aplicação principal e testa
várias configurações possíveis para identificar o formato correto aceito pela API.
"""

import os
import json
import requests
import logging
import sys
import base64
from datetime import datetime

# Configurar logging mais limpo para o console
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("nfe_io_fix")

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

def diagnose_credentials():
    """Verifica formato das credenciais"""
    env_vars = load_env()
    
    api_key = env_vars.get("NFEIO_API_KEY", "")
    logger.info(f"API Key encontrada: {len(api_key)} caracteres")
    
    if len(api_key) < 30:
        logger.error("API Key parece inválida ou muito curta")
    
    # Verificar se é um token Base64 válido
    try:
        # Tentar decodificar o token como base64
        base64.b64decode(api_key)
        logger.info("API Key parece ser um token base64 válido")
    except:
        logger.warning("API Key não é um token base64 válido - isso pode estar OK dependendo do formato esperado pela API")
    
    # Resultado
    return api_key, env_vars.get("NFEIO_COMPANY_ID", ""), env_vars.get("NFEIO_ENVIRONMENT", "Development")

def test_auth_formats(api_key, company_id):
    """Testa diferentes formatos de autenticação"""
    logger.info("\n===== TESTANDO FORMATOS DE AUTENTICAÇÃO =====")
    
    api_url_base = "https://api.nfe.io"
    api_version = "v1"
    base_url = f"{api_url_base}/{api_version}"
    endpoint = f"companies/{company_id}"
    url = f"{base_url}/{endpoint}"
    
    auth_formats = [
        {
            "name": "Basic com token simples",
            "header": {"Authorization": f"Basic {api_key}"}
        },
        {
            "name": "Bearer token",
            "header": {"Authorization": f"Bearer {api_key}"}
        },
        {
            "name": "Token simples",
            "header": {"Authorization": api_key}
        },
        {
            "name": "API Key no header X-API-KEY",
            "header": {"X-API-KEY": api_key}
        }
    ]
    
    success_format = None
    
    for auth in auth_formats:
        logger.info(f"\nTestando formato: {auth['name']}")
        headers = {
            "Content-Type": "application/json",
            **auth['header']
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            logger.info(f"Status: {response.status_code}")
            
            if 200 <= response.status_code < 300:
                logger.info("✅ SUCESSO!")
                success_format = auth
                break
            else:
                logger.info("❌ Falha")
        except Exception as e:
            logger.error(f"Erro: {str(e)}")
    
    if success_format:
        logger.info(f"\n✅ Formato de autenticação correto: {success_format['name']}")
        return success_format['header']
    else:
        logger.error("❌ Nenhum formato de autenticação funcionou")
        return {"Authorization": f"Basic {api_key}"}  # Formato padrão como fallback

def test_minimal_invoice(auth_header, company_id, environment):
    """Testa emissão com payload mínimo"""
    logger.info("\n===== TESTANDO EMISSÃO COM PAYLOAD MÍNIMO =====")
    
    api_url_base = "https://api.nfe.io"
    api_version = "v1"
    base_url = f"{api_url_base}/{api_version}"
    
    # Dados mínimos absolutos para uma nota fiscal
    invoice_data = {
        "borrower": {
            "name": "Cliente Teste",
            "federalTaxNumber": "00000000000",
            "email": "teste@teste.com",
            "address": {
                "postalCode": "01001000",
                "street": "Rua Teste",
                "number": "123",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP"
            }
        },
        "serviceCode": "0107",
        "description": "Teste de emissão de nota fiscal",
        "servicesAmount": 10.00
    }
    
    # Endpoint para emissão de nota fiscal
    endpoint = f"companies/{company_id}/serviceinvoices"
    url = f"{base_url}/{endpoint}"
    
    headers = {
        "Content-Type": "application/json",
        **auth_header
    }
    
    logger.info(f"Enviando dados mínimos: {json.dumps(invoice_data, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, headers=headers, json=invoice_data, timeout=30)
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Resposta: {response.text[:1000]}")
        
        if 200 <= response.status_code < 300:
            logger.info("✅ SUCESSO! Emissão com dados mínimos funcionou")
            return True
        else:
            logger.info("❌ Falha na emissão com dados mínimos")
            
            # Tentar extrair mensagem de erro
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    error_msg = error_data.get('message', str(error_data))
                    logger.error(f"Mensagem de erro: {error_msg}")
            except:
                pass
                
            return False
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return False

def test_different_environments(auth_header, company_id):
    """Testa emissão em diferentes ambientes"""
    logger.info("\n===== TESTANDO DIFERENTES AMBIENTES =====")
    
    environments = ["Development", "Sandbox", "Production"]
    
    for env in environments:
        logger.info(f"\nTestando ambiente: {env}")
        
        api_url_base = "https://api.nfe.io"
        api_version = "v1"
        base_url = f"{api_url_base}/{api_version}"
        
        # Dados mínimos com ambiente específico
        invoice_data = {
            "borrower": {
                "name": "Cliente Teste",
                "federalTaxNumber": "00000000000",
                "email": "teste@teste.com",
                "address": {
                    "postalCode": "01001000",
                    "street": "Rua Teste",
                    "number": "123",
                    "district": "Centro",
                    "city": "São Paulo",
                    "state": "SP"
                }
            },
            "serviceCode": "0107",
            "description": f"Teste em ambiente {env}",
            "servicesAmount": 10.00,
            "environment": env
        }
        
        # Endpoint para emissão de nota fiscal
        endpoint = f"companies/{company_id}/serviceinvoices"
        url = f"{base_url}/{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            **auth_header
        }
        
        try:
            response = requests.post(url, headers=headers, json=invoice_data, timeout=10)
            logger.info(f"Status: {response.status_code}")
            
            # Resumo da resposta
            if len(response.text) > 100:
                logger.info(f"Resposta: {response.text[:100]}...")
            else:
                logger.info(f"Resposta: {response.text}")
            
            if 200 <= response.status_code < 300:
                logger.info(f"✅ SUCESSO no ambiente {env}")
                return env
            else:
                logger.info(f"❌ Falha no ambiente {env}")
        except Exception as e:
            logger.error(f"Erro: {str(e)}")
    
    return None

def check_api_documentation():
    """Verifica documentação da API"""
    logger.info("\n===== VERIFICANDO DOCUMENTAÇÃO DA API =====")
    logger.info("Buscando informações sobre a API NFE.io...")
    
    try:
        response = requests.get("https://nfe.io/docs/api/")
        if response.status_code == 200:
            logger.info("✅ Documentação disponível em: https://nfe.io/docs/api/")
        else:
            logger.info("❌ Documentação não disponível")
    except:
        logger.info("❌ Não foi possível verificar a documentação")
    
    logger.info("\nRecomendação: Verifique a documentação oficial em https://nfe.io/docs/api/ para o formato correto")
    logger.info("Campos obrigatórios e opcionais podem variar conforme a versão da API")

def modify_application_code():
    """Gera recomendações para correção no código da aplicação"""
    logger.info("\n===== RECOMENDAÇÕES PARA CORREÇÃO =====")
    
    recommendations = [
        "1. Verifique se a API key no .env está correta e no formato esperado",
        "2. Certifique-se que o company_id está correto",
        "3. Altere o formato da requisição para o mínimo possível (conforme testado)",
        "4. Verifique se o campo 'serviceCode' está sendo utilizado ao invés de 'cityServiceCode'",
        "5. Remova campos opcionais que possam estar causando problemas",
        "6. Atualize as bibliotecas requests e json para as versões mais recentes",
        "7. Verifique se há caracteres especiais nos campos que possam estar causando problemas",
        "8. Implemente logs mais detalhados para acompanhar cada etapa",
        "9. Se possível, use o módulo oficial da NFE.io se disponível"
    ]
    
    for rec in recommendations:
        logger.info(rec)

def main():
    """Função principal que executa todos os testes"""
    logger.info("===== INICIANDO DIAGNÓSTICO DE EMISSÃO DE NOTAS FISCAIS =====")
    
    # Passo 1: Verificar credenciais
    api_key, company_id, environment = diagnose_credentials()
    
    # Passo 2: Testar formatos de autenticação
    auth_header = test_auth_formats(api_key, company_id)
    
    # Passo 3: Testar emissão mínima
    minimal_success = test_minimal_invoice(auth_header, company_id, environment)
    
    # Passo 4: Se falhar, testar diferentes ambientes
    if not minimal_success:
        working_env = test_different_environments(auth_header, company_id)
        if working_env:
            logger.info(f"\n✅ Ambiente {working_env} funciona para emissão!")
        else:
            logger.info("\n❌ Nenhum ambiente funcionou para emissão")
    
    # Passo 5: Verificar documentação
    check_api_documentation()
    
    # Passo 6: Sugerir correções
    modify_application_code()
    
    # Conclusão
    logger.info("\n===== DIAGNÓSTICO CONCLUÍDO =====")
    logger.info("Execute este script após cada alteração para verificar se o problema foi resolvido")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Erro fatal: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
