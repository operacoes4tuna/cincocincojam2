#!/usr/bin/env python3
"""
Script para testar a leitura direta do arquivo .env
"""
import os
import re

def read_env_file(file_path='.env'):
    """Lê o arquivo .env diretamente"""
    env_vars = {}
    with open(file_path, 'r') as f:
        content = f.read()
        
    # Dividir por linhas
    lines = content.split('\n')
    
    # Processar cada linha
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key] = value
    
    return env_vars

# Ler as variáveis diretamente do arquivo .env
env_vars = read_env_file()

# Mostrar as variáveis relacionadas à OpenAI
print("=== Variáveis OpenAI encontradas no arquivo .env ===")
for key, value in env_vars.items():
    if key.startswith('OPENAI_'):
        # Truncar a chave API para não mostrar tudo
        if key == 'OPENAI_API_KEY':
            print(f"{key}: {value[:15]}...{value[-5:] if len(value) > 20 else ''}")
            print(f"Comprimento da chave: {len(value)} caracteres")
            
            # Verificar se a chave começa com sk-proj-
            if value.startswith('sk-proj-'):
                print("✅ Formato correto: A chave começa com 'sk-proj-'")
            else:
                print("❌ Formato incorreto: A chave não começa com 'sk-proj-'")
                
            # Verificar se a chave tem o formato esperado
            expected_key = "YOUR_OPENAI_API_KEY_GOES_HERE"
            if value == expected_key:
                print("✅ Chave correta: A chave API corresponde ao valor esperado")
            else:
                print("❌ Chave incorreta: A chave API não corresponde ao valor esperado")
        else:
            print(f"{key}: {value}")

# Teste com a API OpenAI
try:
    from openai import OpenAI
    import os
    
    # Definir a variável de ambiente diretamente
    os.environ['OPENAI_API_KEY'] = env_vars.get('OPENAI_API_KEY', '')
    
    # Testar com a chave definida no ambiente
    print("\n=== Testando a API OpenAI com a chave definida no ambiente ===")
    print(f"Chave utilizada: {os.environ['OPENAI_API_KEY'][:15]}...")
    
    client = OpenAI()  # Deve usar a chave do ambiente
    
    # Fazer a requisição de teste
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {"role": "user", "content": "Diga olá em português"}
        ]
    )
    
    print("✅ Requisição bem-sucedida!")
    print(f"Resposta: {completion.choices[0].message.content}")
    
except Exception as e:
    print(f"❌ Erro: {str(e)}")
    
    # Tentar com a chave fixa conhecida
    print("\n=== Testando com a chave fixa conhecida ===")
    
    try:
        # Chave API que sabemos que funciona
        fixed_key = "YOUR_OPENAI_API_KEY_GOES_HERE"
        
        client_fixed = OpenAI(api_key=fixed_key)
        
        completion = client_fixed.chat.completions.create(
            model="gpt-4o-mini",
            store=True,
            messages=[
                {"role": "user", "content": "Diga olá em português"}
            ]
        )
        
        print("✅ Teste com chave fixa funcionou!")
        print(f"Resposta: {completion.choices[0].message.content}")
        
    except Exception as e2:
        print(f"❌ Erro também com chave fixa: {str(e2)}") 