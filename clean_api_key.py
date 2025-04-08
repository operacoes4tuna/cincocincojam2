#!/usr/bin/env python3
# coding: utf-8
"""
Script para substituir chaves de API OpenAI por placeholders nos arquivos de configuração.

Este script:
1. Procura por arquivos que podem conter chaves de API
2. Substitui as chaves reais por placeholders antes de fazer commits
3. Ajuda a prevenir o vazamento de chaves sensíveis no histórico do Git

Uso:
  python3 clean_api_key.py [--files ARQUIVO1 ARQUIVO2 ...] [--dry-run]
"""

import os
import re
import shutil
import argparse
from typing import List, Tuple


def replace_api_key(file_path: str, dry_run: bool = False) -> Tuple[bool, int]:
    """
    Substitui chaves de API OpenAI por placeholders em um arquivo.
    
    Args:
        file_path: Caminho para o arquivo a ser processado
        dry_run: Se True, apenas mostra o que seria alterado sem fazer mudanças
        
    Returns:
        Tupla (sucesso, contador) onde:
        - sucesso: True se o arquivo foi processado com sucesso
        - contador: Número de substituições feitas
    """
    if not os.path.exists(file_path):
        print(f"Arquivo não encontrado: {file_path}")
        return False, 0
    
    try:
        # Lê o conteúdo original do arquivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cria backup do arquivo se não for dry run
        if not dry_run:
            backup_path = f"{file_path}.bak"
            shutil.copy2(file_path, backup_path)
            print(f"Backup criado: {backup_path}")
        
        # Padrões para encontrar chaves de API OpenAI
        patterns = [
            # Formato antigo: sk-seguido por 32+ caracteres alfanuméricos
            r'sk-[a-zA-Z0-9]{32,}',
            # Formato novo: sk-proj-seguido por 100+ caracteres
            r'sk-proj-[a-zA-Z0-9_-]{100,}'
        ]
        
        # Placeholder para substituir a chave
        placeholder = "YOUR_OPENAI_API_KEY_GOES_HERE"
        
        # Conta substituições
        count = 0
        new_content = content
        
        # Aplica cada padrão
        for pattern in patterns:
            # Encontra todas as ocorrências
            matches = re.findall(pattern, content)
            count += len(matches)
            
            # Substitui todas as ocorrências pelo placeholder
            new_content = re.sub(pattern, placeholder, new_content)
        
        # Se encontrou chaves para substituir
        if count > 0:
            if dry_run:
                print(f"[SIMULAÇÃO] Encontradas {count} chaves em {file_path}")
            else:
                # Escreve o conteúdo modificado de volta no arquivo
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Substituídas {count} chaves em {file_path}")
        else:
            print(f"Nenhuma chave encontrada em {file_path}")
        
        return True, count
        
    except Exception as e:
        print(f"❌ Erro ao processar {file_path}: {str(e)}")
        return False, 0


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(description='Substitui chaves de API OpenAI por placeholders')
    parser.add_argument('--files', nargs='+', help='Arquivos específicos para processar')
    parser.add_argument('--dry-run', action='store_true', help='Simula a execução sem fazer alterações')
    args = parser.parse_args()
    
    # Lista padrão de arquivos para verificar
    default_files = [
        '.env',
        '.env.backup',
        '.env.example',
        'test_openai.py',
        'test_direct_env.py',
        'fix_env_file.py',
        'assistant/openai_manager.py',
        'config/settings.py'
    ]
    
    # Usa os arquivos especificados ou a lista padrão
    files_to_check = args.files if args.files else default_files
    
    print("=" * 60)
    print(f"{'SIMULAÇÃO - ' if args.dry_run else ''}Substituindo chaves de API OpenAI")
    print("=" * 60)
    
    total_replaced = 0
    files_modified = 0
    
    # Processa cada arquivo
    for file_path in files_to_check:
        success, count = replace_api_key(file_path, args.dry_run)
        if success and count > 0:
            total_replaced += count
            files_modified += 1
    
    # Exibe resumo
    print("\nResumo da operação:")
    print(f"{'SIMULAÇÃO - ' if args.dry_run else ''}{total_replaced} chaves substituídas em {files_modified} arquivos")
    
    if total_replaced > 0 and not args.dry_run:
        print("\n⚠️ IMPORTANTE: Teste a aplicação antes de fazer commit!")
        print("As chaves foram substituídas por placeholders e podem causar falhas.")


if __name__ == "__main__":
    main() 