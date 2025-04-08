from openai import OpenAI
import os
from dotenv import load_dotenv

print("=== TESTE DE FORMATO DE CHAVE API OPENAI ===")
print("Este script NÃO se conecta à API real, apenas verifica o formato da chave")

# Carregar variáveis de ambiente (chave atual)
load_dotenv()
current_key = os.getenv("OPENAI_API_KEY")
print(f"\n1. Chave atual do .env: {current_key[:15]}...{current_key[-5:] if current_key and len(current_key) > 10 else ''}")
print(f"   Comprimento: {len(current_key) if current_key else 0} caracteres")
print(f"   Formato: {'sk-proj-...' if current_key and current_key.startswith('sk-proj-') else 'sk-...' if current_key and current_key.startswith('sk-') else 'Desconhecido'}")

# Exemplo de formato correto (chave fictícia)
correct_format = "sk-abcdefghijklmnopqrstuvwxyz123456"
print(f"\n2. Exemplo de formato correto: {correct_format[:15]}...")
print(f"   Comprimento: {len(correct_format)} caracteres")
print(f"   Formato: {'sk-...' if correct_format.startswith('sk-') else 'Desconhecido'}")

print("\n=== ANÁLISE ===")
print("OpenAI espera uma chave API no formato 'sk-' seguido por caracteres alfanuméricos.")
print("A chave no formato 'sk-proj-...' parece ser de um sistema diferente ou de outro provedor.")

print("\nOnde obter uma chave válida:")
print("1. Acesse https://platform.openai.com/api-keys")
print("2. Faça login na sua conta OpenAI")
print("3. Clique em 'Create new secret key'")
print("4. Copie a chave gerada e adicione ao seu arquivo .env")
print("\nFormato do arquivo .env:")
print("OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456")
print("OPENAI_MODEL=gpt-3.5-turbo")
print("OPENAI_MAX_TOKENS=150")
print("OPENAI_TEMPERATURE=0.7") 