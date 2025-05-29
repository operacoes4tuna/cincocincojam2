"""
Script para testar a conexão com a API NFE.io
"""
import requests
import json
from datetime import datetime

# Configurações da API
API_KEY = "DSVnClRhik8BkPm69wBTSDAqyR9b3wrCKkyC7Wjk2JySrWXIOsNZBvLZYQxU8z6GUZB"
BASE_URL = "https://api.nfe.io"
API_VERSION = "v1"

# Referência única para testes
REFERENCE = f"teste_{datetime.now().strftime('%Y%m%d%H%M%S')}"

def test_nfeio_connection():
    """
    Testa a conexão com a API NFE.io
    """
    print(f"\n===== TESTE DE CONEXÃO NFE.IO =====")
    print(f"API Key: {API_KEY[:5]}...")
    
    # Testar a requisição para listagem de empresas
    companies_url = f"{BASE_URL}/{API_VERSION}/companies"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {API_KEY}"
    }
    
    print("\n1. Tentando listar empresas cadastradas...")
    try:
        response = requests.get(companies_url, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)[:1000]}")
        
        if response.status_code < 400:
            print("✅ SUCESSO! Conexão estabelecida.")
            
            # Se encontrar empresas, salva o ID da primeira para os testes de emissão
            if response.json() and response.json().get('companies'):
                company_id = response.json()['companies'][0]['id']
                print(f"\nID da primeira empresa encontrada: {company_id}")
                
                # Testar a emissão de uma nota fiscal de serviço
                print("\n2. Tentando simular emissão de NFSe...")
                
                invoice_data = {
                    "cityServiceCode": "2690",
                    "description": "TESTE EMISSAO VIA API",
                    "servicesAmount": 0.01,
                    "borrower": {
                        "type": "LegalEntity",
                        "name": "EMPRESA TESTE",
                        "email": "teste@teste.com.br",
                        "address": {
                            "country": "BRA",
                            "postalCode": "01310100",
                            "street": "Av. Paulista",
                            "number": "1000",
                            "district": "Bela Vista",
                            "city": {
                                "code": "3550308",
                                "name": "São Paulo"
                            },
                            "state": "SP"
                        }
                    }
                }
                
                invoice_url = f"{BASE_URL}/{API_VERSION}/companies/{company_id}/serviceinvoices"
                response = requests.post(invoice_url, headers=headers, json=invoice_data)
                print(f"Status: {response.status_code}")
                print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)[:1000]}")
                
                if response.status_code < 400:
                    print("✅ SUCESSO! Simulação de emissão realizada.")
                else:
                    print("❌ FALHA! Não foi possível simular a emissão.")
            else:
                print("\n⚠️ Nenhuma empresa encontrada para testar emissão de notas.")
        else:
            print("❌ FALHA! Não foi possível conectar à API.")
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
    
    print("\n===== FIM DOS TESTES =====\n")

if __name__ == "__main__":
    test_nfeio_connection()
