#!/usr/bin/env python3
"""
Script para criar um novo arquivo .env com a chave API em uma única linha.
"""
import os
import re
from dotenv import dotenv_values

# Chave API correta (em uma única linha)
API_KEY = "YOUR_OPENAI_API_KEY_GOES_HERE"

# Ler todas as variáveis do arquivo .env usando dotenv
config = dotenv_values(".env")

# Fazer backup do arquivo .env original
os.system("cp .env .env.backup")

# Criar um novo arquivo .env a partir do zero
with open(".env.new", "w") as f:
    # Escrever todas as variáveis, substituindo a chave API
    for key, value in config.items():
        if key != "OPENAI_API_KEY":
            f.write(f"{key}={value}\n")
    
    # Adicionar a chave API como uma nova linha
    f.write(f"OPENAI_API_KEY={API_KEY}\n")
    
    # Adicionar também as configurações relacionadas à OpenAI que podem estar faltando
    if "OPENAI_MODEL" not in config:
        f.write("OPENAI_MODEL=gpt-4o-mini\n")
    if "OPENAI_MAX_TOKENS" not in config:
        f.write("OPENAI_MAX_TOKENS=150\n")
    if "OPENAI_TEMPERATURE" not in config:
        f.write("OPENAI_TEMPERATURE=0.7\n")
    if "OPENAI_STORE" not in config:
        f.write("OPENAI_STORE=true\n")

# Substituir o arquivo .env original pelo novo
os.system("mv .env.new .env")

print("Arquivo .env corrigido com sucesso!")
print("Uma cópia de backup do arquivo original foi criada como .env.backup")

# Verificar se a chave API está correta
with open(".env", "r") as f:
    for line in f:
        if line.startswith("OPENAI_API_KEY="):
            api_key_line = line.strip()
            if API_KEY in api_key_line:
                print("✅ Confirmado: A chave API está corretamente configurada em uma única linha.")
            else:
                print("❌ Erro: A chave API não está configurada corretamente.")
            break 