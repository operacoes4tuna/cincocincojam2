"""
Script para testar especificamente a emissão de NFSe na API FocusNFe
"""
import requests
import json
import base64
from datetime import datetime

# Token de API - deve ser um token válido de homologação
TOKEN = "YKCK2RcoYebXvtzucNnJ899VIFHNhzbq"

# URL da API de homologação
BASE_URL = "https://homologacao.focusnfe.com.br"

# Referência única para esta nota
REFERENCE = f"teste_{datetime.now().strftime('%Y%m%d%H%M%S')}"

def test_nfse_emission():
    """
    Testa a emissão de NFSe usando a API FocusNFe
    """
    print(f"\n===== TESTE DE EMISSÃO NFSE FOCUSNFE =====")
    print(f"Token: {TOKEN[:5]}...")
    print(f"Referência: {REFERENCE}")
    
    # Dados mínimos para emissão de NFSe
    nfse_data = {
        "data_emissao": datetime.now().strftime('%Y-%m-%d'),
        "cnpj_emitente": "12345678000199",
        "natureza_operacao": "Teste de emissão",
        "valor_servicos": 100.00,
        "servico": {
            "descricao": "Serviço de teste via API",
            "issqn": {
                "codigo_tributacao_municipio": "8.03"
            }
        },
        "consumidor": {
            "nome": "Cliente Teste API",
            "email": "cliente@teste.com"
        }
    }
    
    print("\n1. Tentando emissão com parâmetros na URL...")
    url = f"{BASE_URL}/v2/nfse?ref={REFERENCE}&token={TOKEN}"
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers, json=nfse_data)
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text}")
    except Exception as e:
        print(f"Erro: {str(e)}")
    
    print("\n2. Tentando emissão com Basic Auth...")
    url = f"{BASE_URL}/v2/nfse?ref={REFERENCE}"
    
    # Codificar o token no formato Basic Auth
    auth_string = f"{TOKEN}:"
    auth_bytes = auth_string.encode('utf-8')
    auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_b64}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=nfse_data)
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text}")
    except Exception as e:
        print(f"Erro: {str(e)}")
    
    print("\n===== FIM DO TESTE =====")

if __name__ == "__main__":
    test_nfse_emission()
