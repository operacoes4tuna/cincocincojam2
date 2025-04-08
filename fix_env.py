#!/usr/bin/env python3
"""
Script para corrigir o arquivo .env, garantindo que a chave da API OpenAI 
esteja em uma única linha.
"""
import sys

# Chave API correta (em uma única linha)
correct_api_key = "YOUR_OPENAI_API_KEY_GOES_HERE"

def fix_env_file():
    # Ler o arquivo .env
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    # Criar um backup do arquivo original
    with open('.env.bak', 'w') as f:
        f.writelines(lines)
    
    # Verificar se há linhas que começam com OPENAI_API_KEY
    new_lines = []
    skip_next = False
    
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
            
        if line.startswith('OPENAI_API_KEY='):
            # Substituir pela linha correta
            new_lines.append(f'OPENAI_API_KEY={correct_api_key}\n')
            
            # Verificar se a chave continua na próxima linha
            if i+1 < len(lines) and not lines[i+1].startswith('#') and not '=' in lines[i+1]:
                skip_next = True
        else:
            new_lines.append(line)
    
    # Escrever o arquivo corrigido
    with open('.env', 'w') as f:
        f.writelines(new_lines)
    
    print("Arquivo .env corrigido com sucesso!")
    print("Um backup do arquivo original foi criado como .env.bak")

if __name__ == "__main__":
    fix_env_file() 