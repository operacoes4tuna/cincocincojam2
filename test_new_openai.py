"""
Script para testar a nova integração com a API OpenAI
usando chaves de projeto no formato sk-proj-...
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

def test_openai_connection():
    """Testa a conexão com a API OpenAI usando a nova chave de projeto"""
    
    # Obter a chave da API
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("Chave API não encontrada no arquivo .env")
        return False
    
    logger.info(f"Chave API encontrada: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else ''}")
    logger.info(f"Formato da chave: {'sk-proj-...' if api_key.startswith('sk-proj-') else 'sk-...' if api_key.startswith('sk-') else 'Desconhecido'}")
    
    try:
        # Inicializar o cliente OpenAI
        client = OpenAI(api_key=api_key)
        logger.info("Cliente OpenAI inicializado")
        
        # Fazer uma chamada simples para testar
        logger.info("Enviando requisição para OpenAI...")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            store=True,
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": "Olá, pode me ajudar com uma dúvida sobre música?"}
            ],
            max_tokens=50
        )
        
        # Verificar a resposta
        response = completion.choices[0].message.content
        logger.info("Resposta recebida com sucesso!")
        logger.info(f"Resposta da OpenAI: {response}")
        
        return True
    
    except Exception as e:
        logger.error(f"Erro ao conectar com a OpenAI: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Iniciando teste de conexão com a OpenAI")
    success = test_openai_connection()
    
    if success:
        logger.info("✅ Teste concluído com sucesso! A integração com a OpenAI está funcionando corretamente.")
    else:
        logger.error("❌ Teste falhou! Verifique os erros acima para mais informações.") 