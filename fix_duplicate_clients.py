#!/usr/bin/env python
import os
import sys
import django
from collections import defaultdict

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cincocincojam2.settings')
django.setup()

from django.db import transaction
from clients.models import Client, CompanyClient

def fix_duplicate_cnpj():
    """
    Identifica e remove clientes duplicados com o mesmo CNPJ,
    mantendo apenas o registro mais recente.
    """
    print("Iniciando a verificação de CNPJs duplicados...")
    
    # Agrupar clientes por CNPJ
    cnpj_map = defaultdict(list)
    for company in CompanyClient.objects.all():
        cnpj_map[company.cnpj].append(company)
    
    # Encontrar CNPJs duplicados
    duplicates = {cnpj: companies for cnpj, companies in cnpj_map.items() if len(companies) > 1}
    
    if not duplicates:
        print("Não foram encontrados CNPJs duplicados.")
        return
    
    print(f"Foram encontrados {len(duplicates)} CNPJs duplicados.")
    
    # Processar cada conjunto de duplicados
    with transaction.atomic():
        for cnpj, companies in duplicates.items():
            print(f"\nProcessando CNPJ duplicado: {cnpj}")
            print(f"Total de registros duplicados: {len(companies)}")
            
            # Ordenar por data de criação do cliente base (mais recente primeiro)
            companies.sort(key=lambda x: x.client.created_at, reverse=True)
            
            # Manter o primeiro (mais recente) e remover os outros
            keep = companies[0]
            remove = companies[1:]
            
            print(f"Mantendo: ID: {keep.id}, Nome: {keep.company_name}, "
                  f"Cliente ID: {keep.client_id}, Data: {keep.client.created_at}")
            
            # Remover duplicados
            for company in remove:
                print(f"Removendo: ID: {company.id}, Nome: {company.company_name}, "
                      f"Cliente ID: {company.client_id}, Data: {company.client.created_at}")
                
                # Remover o client base também (CASCADE vai remover company)
                client = company.client
                client.delete()
                
    print("\nProcessamento concluído.")
    
if __name__ == "__main__":
    fix_duplicate_cnpj() 