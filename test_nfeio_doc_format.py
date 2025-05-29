#!/usr/bin/env python
"""
Script de teste para emissão de nota fiscal seguindo exatamente a documentação da NFE.io.
Este script testa diferentes formatos de requisição baseados na documentação oficial.
"""

import os
import json
import requests
import logging
import sys
from datetime import datetime

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

log = logging.getLogger("nfeio_doc_test")

def carregar_env(env_file='.env'):
    """Carrega variáveis do arquivo .env"""
    env_vars = {}
    try:
        with open(env_file, 'r') as f:
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

def autenticacao_teste():
    """Testa diferentes métodos de autenticação"""
    env_vars = carregar_env()
    api_key = env_vars.get("NFEIO_API_KEY")
    company_id = env_vars.get("NFEIO_COMPANY_ID")
    
    if not api_key or not company_id:
        log.error("API Key ou Company ID não encontrados")
        return None, None, None
    
    log.info(f"API Key: {api_key[:5]}...{api_key[-5:]} ({len(api_key)} caracteres)")
    log.info(f"Company ID: {company_id}")
    
    # Testando diferentes formatos de autenticação
    auth_methods = [
        {"name": "Authorization: Basic", "header": {"Authorization": f"Basic {api_key}"}},
        {"name": "X-NFEIO-APIKEY", "header": {"X-NFEIO-APIKEY": api_key}},
        {"name": "Query String api_key", "query": {"api_key": api_key}}
    ]
    
    url = f"https://api.nfe.io/v1/companies/{company_id}"
    
    log.info("=== TESTANDO MÉTODOS DE AUTENTICAÇÃO ===")
    
    for method in auth_methods:
        log.info(f"Testando {method['name']}...")
        
        try:
            if "header" in method:
                headers = {"Content-Type": "application/json", **method["header"]}
                response = requests.get(url, headers=headers, timeout=10)
            else:
                headers = {"Content-Type": "application/json"}
                response = requests.get(url, headers=headers, params=method["query"], timeout=10)
            
            log.info(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                log.info(f"✅ {method['name']} funcionou!")
                return api_key, company_id, method
        except Exception as e:
            log.error(f"Erro com {method['name']}: {e}")
    
    log.error("❌ Nenhum método de autenticação funcionou")
    return api_key, company_id, None

def teste_emissao_formato_completo(api_key, company_id, auth_method):
    """Testa emissão de NFS-e com formato completo baseado na documentação"""
    log.info("\n=== TESTE DE EMISSÃO - FORMATO COMPLETO ===")
    
    url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
    
    # Construindo requisição conforme documentação
    invoice_data = {
        "borrower": {
            "name": "Cliente de Teste NFE.io",
            "email": "cliente.teste@teste.com",
            "federalTaxNumber": 11111111111,  # CPF como número, não string
            "type": "NaturalPerson",  # Pessoa Física
            "address": {
                "country": "BRA",  # ISO 3166-1 conforme documentação
                "postalCode": "01001000",  # CEP sem hífen
                "street": "Rua de Teste",
                "number": "100",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP"
            }
        },
        "serviceCode": "01.07",  # Código com ponto
        "cityServiceCode": "0107",  # Código sem ponto
        "description": "Teste de emissão seguindo documentação",
        "servicesAmount": 10.00,
        "issRate": 0.02,  # 2% de ISS
        "environment": "Development"
    }
    
    log.info(f"Dados: {json.dumps(invoice_data, indent=2, ensure_ascii=False)}")
    
    # Configurar autenticação conforme método que funcionou
    if "header" in auth_method:
        headers = {"Content-Type": "application/json", **auth_method["header"]}
        params = {}
    else:
        headers = {"Content-Type": "application/json"}
        params = auth_method["query"]
    
    try:
        log.info(f"Enviando requisição POST para {url}")
        response = requests.post(url, headers=headers, params=params, json=invoice_data, timeout=30)
        
        log.info(f"Status: {response.status_code}")
        log.info(f"Headers: {dict(response.headers)}")
        
        try:
            content = response.text
            log.info(f"Conteúdo da resposta ({len(content)} bytes):")
            log.info(content[:500] + "..." if len(content) > 500 else content)
            
            if 200 <= response.status_code < 300:
                try:
                    json_response = response.json()
                    log.info("Resposta JSON válida")
                    return True
                except:
                    log.error("Resposta não é um JSON válido")
            else:
                try:
                    error_data = response.json()
                    log.error(f"Detalhes do erro: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    log.error("Não foi possível decodificar detalhes do erro")
        except Exception as e:
            log.error(f"Erro ao processar resposta: {e}")
        
        return False
    except Exception as e:
        log.error(f"Erro na requisição: {e}")
        return False

def teste_emissao_formato_minimal(api_key, company_id, auth_method):
    """Testa emissão de NFS-e com formato mínimo possível"""
    log.info("\n=== TESTE DE EMISSÃO - FORMATO MÍNIMO ===")
    
    url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
    
    # Apenas os campos obrigatórios
    invoice_data = {
        "borrower": {
            "name": "Cliente Teste Mínimo",
            "federalTaxNumber": 11111111111,
            "address": {
                "street": "Rua de Teste",
                "number": "100",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP"
            }
        },
        "serviceCode": "01.07",
        "description": "Teste de emissão com campos mínimos",
        "servicesAmount": 10.00
    }
    
    log.info(f"Dados: {json.dumps(invoice_data, indent=2, ensure_ascii=False)}")
    
    # Configurar autenticação conforme método que funcionou
    if "header" in auth_method:
        headers = {"Content-Type": "application/json", **auth_method["header"]}
        params = {}
    else:
        headers = {"Content-Type": "application/json"}
        params = auth_method["query"]
    
    try:
        log.info(f"Enviando requisição POST para {url}")
        response = requests.post(url, headers=headers, params=params, json=invoice_data, timeout=30)
        
        log.info(f"Status: {response.status_code}")
        
        try:
            content = response.text
            log.info(f"Conteúdo da resposta ({len(content)} bytes):")
            log.info(content[:500] + "..." if len(content) > 500 else content)
            
            if 200 <= response.status_code < 300:
                log.info("✅ Emissão com formato mínimo funcionou!")
                return True
            else:
                log.error("❌ Emissão com formato mínimo falhou")
                try:
                    error_data = response.json()
                    log.error(f"Detalhes do erro: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                except:
                    pass
        except Exception as e:
            log.error(f"Erro ao processar resposta: {e}")
        
        return False
    except Exception as e:
        log.error(f"Erro na requisição: {e}")
        return False

def teste_variacao_campos(api_key, company_id, auth_method):
    """Testa variações específicas de campos problemáticos"""
    log.info("\n=== TESTE DE VARIAÇÕES DE CAMPOS ===")
    
    url = f"https://api.nfe.io/v1/companies/{company_id}/serviceinvoices"
    
    # Possíveis variações para os campos problemáticos
    variacoes = [
        {
            "descricao": "federalTaxNumber como string",
            "campo": "federalTaxNumber",
            "valor": "11111111111",
            "tipo": "string"
        },
        {
            "descricao": "serviceCode sem ponto",
            "campo": "serviceCode",
            "valor": "0107",
            "tipo": "string"
        },
        {
            "descricao": "apenas cityServiceCode (sem serviceCode)",
            "campo": "cityServiceCode",
            "valor": "0107",
            "tipo": "string",
            "remover": "serviceCode"
        },
        {
            "descricao": "address sem district (bairro)",
            "campo": "district",
            "remover": True,
            "caminho": ["borrower", "address"]
        }
    ]
    
    # Base de dados para testes
    base_data = {
        "borrower": {
            "name": "Cliente Teste Variações",
            "federalTaxNumber": 11111111111,
            "address": {
                "street": "Rua de Teste",
                "number": "100",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP"
            }
        },
        "serviceCode": "01.07",
        "description": "Teste de variações de campos",
        "servicesAmount": 10.00
    }
    
    # Configurar autenticação
    if "header" in auth_method:
        headers = {"Content-Type": "application/json", **auth_method["header"]}
        params = {}
    else:
        headers = {"Content-Type": "application/json"}
        params = auth_method["query"]
    
    for i, variacao in enumerate(variacoes):
        log.info(f"\nTeste {i+1}: {variacao['descricao']}")
        
        # Clonar dados base para este teste
        teste_data = json.loads(json.dumps(base_data))
        
        # Aplicar variação
        if variacao.get("remover") is True:
            # Remover campo aninhado
            caminho = variacao.get("caminho", [])
            atual = teste_data
            for parte in caminho[:-1]:
                atual = atual[parte]
            campo = variacao["campo"]
            if campo in atual:
                del atual[campo]
        elif "remover" in variacao:
            # Remover campo de primeiro nível
            campo = variacao["remover"]
            if campo in teste_data:
                del teste_data[campo]
                # Adicionar campo alternativo se necessário
                if "campo" in variacao:
                    teste_data[variacao["campo"]] = variacao["valor"]
        else:
            # Modificar valor do campo
            if "caminho" in variacao:
                # Modificar campo aninhado
                atual = teste_data
                for parte in variacao["caminho"]:
                    atual = atual[parte]
                atual[variacao["campo"]] = variacao["valor"]
            else:
                # Modificar campo de primeiro nível
                teste_data[variacao["campo"]] = variacao["valor"]
        
        log.info(f"Dados: {json.dumps(teste_data, indent=2, ensure_ascii=False)}")
        
        try:
            log.info(f"Enviando requisição POST")
            response = requests.post(url, headers=headers, params=params, json=teste_data, timeout=30)
            
            log.info(f"Status: {response.status_code}")
            
            try:
                content = response.text
                log.info(f"Conteúdo da resposta ({len(content)} bytes):")
                log.info(content[:500] + "..." if len(content) > 500 else content)
                
                if 200 <= response.status_code < 300:
                    log.info(f"✅ Teste {i+1} ({variacao['descricao']}) funcionou!")
                    return variacao
                else:
                    log.info(f"❌ Teste {i+1} falhou")
            except Exception as e:
                log.error(f"Erro ao processar resposta: {e}")
        except Exception as e:
            log.error(f"Erro na requisição: {e}")
    
    return None

def main():
    log.info("==== DIAGNÓSTICO DE EMISSÃO NFE.IO BASEADO NA DOCUMENTAÇÃO ====")
    
    # 1. Testar métodos de autenticação
    api_key, company_id, auth_method = autenticacao_teste()
    
    if not auth_method:
        log.error("Não foi possível autenticar - abortando testes")
        return
    
    # 2. Testar emissão com formato completo
    sucesso_completo = teste_emissao_formato_completo(api_key, company_id, auth_method)
    
    # 3. Testar emissão com formato mínimo
    sucesso_minimo = teste_emissao_formato_minimal(api_key, company_id, auth_method)
    
    # 4. Testar variações específicas para encontrar o problema
    if not sucesso_completo and not sucesso_minimo:
        variacao_sucesso = teste_variacao_campos(api_key, company_id, auth_method)
        if variacao_sucesso:
            log.info(f"\n✅ SOLUÇÃO ENCONTRADA: {variacao_sucesso['descricao']}")
        else:
            log.error("\n❌ Nenhuma variação testada funcionou")
    
    log.info("\n=== RECOMENDAÇÕES BASEADAS NOS TESTES ===")
    log.info("1. Verifique se os campos obrigatórios estão presentes")
    log.info("2. Certifique-se que federalTaxNumber está no formato correto (número, não string)")
    log.info("3. Utilize o campo serviceCode (não cityServiceCode) com formato XX.XX")
    log.info("4. Certifique-se que todos os campos de endereço obrigatórios estão presentes")
    log.info("5. Consulte a documentação atualizada em https://nfe.io/docs/desenvolvedores/rest-api/nota-fiscal-de-servico-v1/")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"Erro fatal: {str(e)}")
        import traceback
        log.error(traceback.format_exc())
