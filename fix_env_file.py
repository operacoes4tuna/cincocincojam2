#!/usr/bin/env python3
"""
Script para corrigir o arquivo .env
"""

# Chave API correta
API_KEY = "YOUR_OPENAI_API_KEY_GOES_HERE"

# Ler o arquivo .env atual
with open('.env', 'r') as f:
    env_content = f.read()

# Fazer backup
with open('.env.bak2', 'w') as f:
    f.write(env_content)

# Remover linhas com OPENAI_API_KEY
import re
env_content = re.sub(r'OPENAI_API_KEY=.*(\n[^=\n#].*)*', '', env_content)

# Adicionar a nova chave API
env_content += f"\n# Chave API OpenAI (corrigida)\nOPENAI_API_KEY={API_KEY}\n"

# Escrever o novo arquivo
with open('.env', 'w') as f:
    f.write(env_content)

print("Arquivo .env corrigido com sucesso!") 