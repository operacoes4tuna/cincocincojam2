from openai import OpenAI
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Obter a chave da API do arquivo .env
api_key = os.getenv("OPENAI_API_KEY")
print(f"API key do .env: {api_key[:15]}...{api_key[-5:] if api_key and len(api_key) > 10 else ''}")
print(f"Comprimento da chave: {len(api_key) if api_key else 0} caracteres")

# Verificar se contém quebras de linha ou espaços extras
if api_key:
    has_newline = '\n' in api_key
    has_spaces = ' ' in api_key
    print(f"Contém quebras de linha: {has_newline}")
    print(f"Contém espaços: {has_spaces}")
    
    # Limpar a chave
    cleaned_key = api_key.strip()
    if cleaned_key != api_key:
        print("A chave API contém espaços no início ou final que foram removidos.")
        api_key = cleaned_key

try:
    # Tenta usar o modelo 'gpt-3.5-turbo' em vez de gpt-4
    print("\nTentando com o modelo gpt-3.5-turbo...")
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é um assistente útil."},
            {"role": "user", "content": "Olá, tudo bem?"}
        ],
        max_tokens=50
    )
    
    print("Resposta recebida com sucesso!")
    print(response.choices[0].message.content)
    
except Exception as e:
    print(f"Erro ao chamar a API: {str(e)}")
    
    # Se ainda estiver com erro, tente uma chave de exemplo para ver se o formato está correto
    print("\nA chave API parece estar no formato incorreto.")
    print("As chaves OpenAI válidas geralmente começam com 'sk-' seguido de caracteres alfanuméricos.")
    print("Exemplo de formato correto: YOUR_OPENAI_API_KEY_GOES_HERE")
    print("\nVerifique se você obteve sua chave da página: https://platform.openai.com/api-keys") 