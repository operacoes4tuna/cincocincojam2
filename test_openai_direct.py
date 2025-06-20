"""
Script para testar diretamente a API OpenAI usando o código de exemplo fornecido pelo usuário.
"""
from openai import OpenAI

# Usar exatamente a chave e configuração fornecida pelo usuário
client = OpenAI(
  api_key="YOUR_OPENAI_API_KEY_GOES_HERE"
)

try:
    print("Enviando requisição para a API OpenAI...")
    completion = client.chat.completions.create(
      model="gpt-4o-mini",
      store=True,
      messages=[
        {"role": "user", "content": "Escreva um haiku sobre IA"}
      ]
    )
    
    print("\nResposta recebida com sucesso!")
    print("---")
    print(completion.choices[0].message.content)
    print("---")
    
    # Informações adicionais da resposta
    print("\nModelo usado:", completion.model)
    print("ID da completação:", completion.id)
    print("Tokens de entrada:", completion.usage.prompt_tokens)
    print("Tokens de saída:", completion.usage.completion_tokens)
    print("Total de tokens:", completion.usage.total_tokens)
    
except Exception as e:
    print(f"Erro ao chamar a API OpenAI: {str(e)}") 