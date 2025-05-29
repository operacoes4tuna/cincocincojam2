"""
Script para testar a API OpenAI usando a configuração do .env
"""
import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Obter a chave da API
api_key = os.getenv("OPENAI_API_KEY")
logger.info(f"Utilizando chave API: {api_key[:15]}...{api_key[-5:] if api_key else ''}")

# Verificar se a chave é exatamente a mesma do teste bem-sucedido
direct_key = "YOUR_OPENAI_API_KEY_GOES_HERE"
logger.info(f"As chaves são idênticas? {api_key == direct_key}")

try:
    # Inicializar cliente OpenAI
    client = OpenAI(api_key=api_key)
    
    # Criar completação
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {"role": "system", "content": "Você é um assistente útil para a plataforma 55Jam."},
            {"role": "user", "content": "O que você pode me dizer sobre teoria musical?"}
        ],
        max_tokens=150
    )
    
    # Mostrar resultado
    logger.info("Resposta recebida com sucesso!")
    logger.info(f"Resposta: {completion.choices[0].message.content}")
    
except Exception as e:
    logger.error(f"Erro: {str(e)}")
    
    # Se houve erro, tentar com a chave direta para comparar
    logger.info("Tentando com a chave direta como fallback...")
    
    try:
        client_direct = OpenAI(api_key=direct_key)
        completion_direct = client_direct.chat.completions.create(
            model="gpt-4o-mini",
            store=True,
            messages=[
                {"role": "user", "content": "Teste de conexão"}
            ]
        )
        logger.info("Teste com chave direta funcionou! O problema está no carregamento da variável de ambiente.")
    except Exception as direct_error:
        logger.error(f"Erro também com chave direta: {str(direct_error)}") 