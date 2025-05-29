"""
Script para testar a conexão com a API FocusNFe
"""
import os
import json
import base64
import requests
from django.conf import settings

def test_focus_connection():
    """
    Testa diferentes formas de autenticação com a API FocusNFe
    """
    # Definir o token diretamente para garantir que seja usado
    token = "YKCK2RcoYebXvtzucNnJ899VIFHNhzbq"
    print(f"\n===== TESTE DE CONEXÃO FOCUSNFE =====")
    print(f"Token: {token[:5]}..." if token else "Token: Vazio")
    base_url = "https://homologacao.focusnfe.com.br"
    
    # Testes a realizar com endpoints corretos da documentação
    methods = [
        {
            "name": "Parâmetro na URL (Status NFSe)",
            "url": f"{base_url}/v2/nfse?ref=teste123&token={token}",
            "headers": {"Content-Type": "application/json"},
            "auth": None,
            "method": "GET"
        },
        {
            "name": "Basic Auth (Status NFSe)",
            "url": f"{base_url}/v2/nfse?ref=teste123",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Basic {base64.b64encode(f'{token}:'.encode('utf-8')).decode('utf-8')}"
            },
            "auth": None,
            "method": "GET"
        },
        {
            "name": "Basic Auth via Requests (Status NFSe)",
            "url": f"{base_url}/v2/nfse?ref=teste123",
            "headers": {"Content-Type": "application/json"},
            "auth": (token, ''),
            "method": "GET"
        },
        {
            "name": "POST dados mínimos de NFSe",
            "url": f"{base_url}/v2/nfse?ref=teste123",
            "headers": {"Content-Type": "application/json"},
            "auth": (token, ''),
            "method": "POST",
            "data": {
                "data_emissao": "2025-03-31",
                "cnpj_emitente": "12345678000199",
                "natureza_operacao": "Teste",
                "valor_servicos": 100.0,
                "servico": {
                    "descricao": "Serviço de teste",
                    "issqn": {"codigo_tributacao_municipio": "8.03"}
                },
                "consumidor": {
                    "nome": "Cliente Teste",
                    "email": "cliente@teste.com"
                }
            }
        }
    ]
    
    # Executar testes
    for method in methods:
        print(f"\n>>> Método: {method['name']}")
        print(f"URL: {method['url']}")
        print(f"Headers: {method['headers']}")
        
        try:
            if method['method'] == "GET":
                if method['auth']:
                    response = requests.get(method['url'], headers=method['headers'], auth=method['auth'])
                else:
                    response = requests.get(method['url'], headers=method['headers'])
            elif method['method'] == "POST":
                data = method.get('data', {})
                print(f"Data: {json.dumps(data, indent=2)}")
                if method['auth']:
                    response = requests.post(method['url'], headers=method['headers'], json=data, auth=method['auth'])
                else:
                    response = requests.post(method['url'], headers=method['headers'], json=data)
                
            print(f"Status: {response.status_code}")
            print(f"Resposta: {response.text[:1000]}")
            
            if response.status_code < 400:
                print("✅ SUCESSO! Método funcionou!")
            else:
                print("❌ FALHA! Método não funcionou.")
                
        except Exception as e:
            print(f"❌ ERRO: {str(e)}")
    
    print("\n===== FIM DOS TESTES =====\n")

if __name__ == "__main__":
    test_focus_connection()
