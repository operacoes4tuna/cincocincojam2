"""
Script para verificar a configuração de RPS na plataforma NFE.io e testar diferentes formatos de RPS.
"""
import os
import sys
import json
import requests
import django
from decimal import Decimal

# Configurar ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings

# Classe para testes da API NFE.io
class NFEioTester:
    API_URL_BASE = "https://api.nfe.io"
    API_VERSION = "v1"
    
    def __init__(self):
        self.api_key = settings.NFEIO_API_KEY
        self.company_id = settings.NFEIO_COMPANY_ID
        self.environment = settings.NFEIO_ENVIRONMENT
        self.base_url = f"{self.API_URL_BASE}/{self.API_VERSION}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.api_key}"
        }
        print(f"API Key: {self.api_key[:5]}...{self.api_key[-5:]} (tamanho: {len(self.api_key)})")
        print(f"Company ID: {self.company_id}")
        print(f"Environment: {self.environment}")
        print(f"Base URL: {self.base_url}")
    
    def make_request(self, method, endpoint, data=None):
        """
        Faz uma requisição para a API NFE.io.
        """
        url = f"{self.base_url}/{endpoint}"
        print(f"\n=== Fazendo requisição {method} para {url} ===")
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            else:
                print(f"Método não suportado: {method}")
                return None
            
            print(f"Status: {response.status_code}")
            if 200 <= response.status_code < 300:
                try:
                    return response.json()
                except:
                    print(f"Resposta não é um JSON válido: {response.text}")
                    return response.text
            else:
                print(f"Erro na API: {response.status_code}")
                print(f"Resposta: {response.text}")
                return None
                
        except Exception as e:
            print(f"Erro na requisição: {str(e)}")
            return None
    
    def get_company_info(self):
        """
        Obtém informações da empresa na NFE.io.
        """
        print("\n=== Obtendo informações da empresa ===")
        endpoint = f"companies/{self.company_id}"
        return self.make_request('GET', endpoint)
    
    def get_rps_configuration(self):
        """
        Tenta obter configuração de RPS da empresa.
        """
        print("\n=== Tentando obter configuração de RPS ===")
        # Tentar encontrar endpoints relacionados a RPS na documentação
        # Testar alguns endpoints que possam conter essa informação
        
        # Verificar empresa
        company_info = self.get_company_info()
        if company_info:
            print(json.dumps(company_info, indent=2))
            # Verificar se há informações de RPS nos dados da empresa
            if 'settings' in company_info:
                print("\nVerificando configurações da empresa:")
                settings_data = company_info.get('settings', {})
                print(json.dumps(settings_data, indent=2))
                
                # Procurar por configurações de RPS
                rps_configs = {}
                for key, value in settings_data.items():
                    if 'rps' in key.lower():
                        rps_configs[key] = value
                
                if rps_configs:
                    print("\nConfigurações de RPS encontradas:")
                    print(json.dumps(rps_configs, indent=2))
                else:
                    print("\nNenhuma configuração de RPS encontrada nas configurações da empresa.")
        
        # Verificar se há endpoints específicos para RPS
        print("\n=== Tentando acessar endpoints específicos para RPS ===")
        endpoints = [
            f"companies/{self.company_id}/rps",
            f"companies/{self.company_id}/settings/rps",
            f"companies/{self.company_id}/serviceinvoices/settings"
        ]
        
        for endpoint in endpoints:
            print(f"\nTentando endpoint: {endpoint}")
            result = self.make_request('GET', endpoint)
            if result:
                print("Endpoint válido encontrado!")
                print(json.dumps(result, indent=2))
    
    def test_rps_formats(self):
        """
        Testa diferentes formatos de RPS para verificar qual é aceito pela API.
        """
        print("\n=== Testando diferentes formatos de RPS ===")
        
        # Criar um payload básico para teste
        base_payload = {
            "borrower": {
                "type": "NaturalPerson",
                "name": "Cliente de Teste",
                "email": "teste@example.com",
                "federalTaxNumber": 11111111111,
                "address": {
                    "country": "BRA",
                    "state": "SP",
                    "city": {
                        "code": "3550308",
                        "name": "São Paulo"
                    },
                    "district": "Centro",
                    "street": "Rua de Teste",
                    "number": "123",
                    "postalCode": "01001000",
                    "additionalInformation": ""
                }
            },
            "cityServiceCode": "0107",
            "description": "Serviço de teste para verificar formato RPS",
            "servicesAmount": 1.00,
            "environment": self.environment,
            "reference": "TESTE_RPS_FORMAT",
            "additionalInformation": "Teste de formato RPS"
        }
        
        # Lista de formatos de RPS a serem testados
        rps_formats = [
            {"rpsSerialNumber": "9", "rpsNumber": 2},
            {"rpsSerialNumber": "9", "rpsNumber": "2"},
            {"rpsSerialNumber": "9", "rpsNumber": "002"},
            {"rpsSerialNumber": 9, "rpsNumber": 2},
            {"rpsSerialNumber": "IO", "rpsNumber": 2},
            {"rpsSerialNumber": "IO", "rpsNumber": "002"},
            {"rpsNumber": 2}  # Sem série
        ]
        
        endpoint = f"companies/{self.company_id}/serviceinvoices"
        
        for i, rps_format in enumerate(rps_formats):
            print(f"\n--- Teste {i+1}: {rps_format} ---")
            payload = base_payload.copy()
            for key, value in rps_format.items():
                payload[key] = value
            
            print(f"Enviando payload com RPS: {rps_format}")
            # Não enviamos realmente para não criar múltiplas notas
            # Descomente a linha abaixo se quiser testar com envios reais
            # result = self.make_request('POST', endpoint, payload)
            print("Simulação apenas. Para testar com envio real, descomente a linha de requisição.")

    def check_api_documentation(self):
        """
        Verifica na documentação da API se há informações sobre o formato RPS.
        """
        print("\n=== Verificando documentação da API ===")
        print("A documentação oficial da NFE.io está disponível em: https://nfe.io/docs/")
        print("Para obter informações específicas sobre RPS, acesse:")
        print("https://nfe.io/docs/nota-fiscal-servico-eletronica/duvidas/campos-para-autorizacao-de-nfse/")
        
        print("\nDe acordo com a documentação, o RPS geralmente precisa estar:")
        print("1. Pré-cadastrado na prefeitura ou na plataforma NFE.io")
        print("2. Seguir o formato específico do município")
        print("3. Ser único para cada nota fiscal")
        print("4. Algumas prefeituras requerem séries numéricas, outras alfanuméricas")

def main():
    print("=== Verificador de Configuração e Formato RPS NFE.io ===")
    
    # Criar instância do testador
    tester = NFEioTester()
    
    # Verificar informações da empresa
    tester.get_company_info()
    
    # Tentar obter configuração de RPS
    tester.get_rps_configuration()
    
    # Verificar documentação
    tester.check_api_documentation()
    
    # Testar formatos de RPS
    tester.test_rps_formats()
    
    print("\n=== Verificação concluída ===")
    print("\nRecomendações:")
    print("1. Verifique no portal NFE.io se há uma seção para configurar RPS")
    print("2. Entre em contato com o suporte da NFE.io informando o erro específico")
    print("3. Verifique as regras de RPS da prefeitura de São Paulo")

if __name__ == "__main__":
    main()
