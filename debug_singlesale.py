#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.append('/d/cincocincojam2')
django.setup()

from django.contrib.auth import get_user_model
from payments.models import SingleSale
from django.utils import timezone

User = get_user_model()

def debug_singlesale_issue():
    """Investiga o problema das notas avulsas não aparecendo na lista"""
    print("=== INVESTIGAÇÃO: NOTAS AVULSAS NÃO APARECEM NA LISTA ===\n")
    
    # 1. Verificar se existem notas avulsas no banco
    print("1. Verificando todas as notas avulsas no banco de dados:")
    all_sales = SingleSale.objects.all().order_by('-created_at')
    print(f"   Total de notas encontradas: {all_sales.count()}")
    
    if all_sales.exists():
        print("   Últimas 5 notas:")
        for sale in all_sales[:5]:
            print(f"   - ID: {sale.id}, Descrição: {sale.description}")
            print(f"     Vendedor: {sale.seller.email} (ID: {sale.seller.id})")
            print(f"     Status: {sale.status}")
            print(f"     Criado em: {sale.created_at}")
            print(f"     Cliente: {sale.customer_name}")
            print()
    else:
        print("   ❌ Nenhuma nota avulsa encontrada no banco!")
        return
    
    # 2. Verificar professores no sistema
    print("2. Verificando professores no sistema:")
    professors = User.objects.filter(user_type='PROFESSOR')
    print(f"   Total de professores: {professors.count()}")
    
    if professors.exists():
        print("   Professores encontrados:")
        for prof in professors[:3]:
            print(f"   - {prof.email} (ID: {prof.id})")
            # Verificar notas deste professor
            prof_sales = SingleSale.objects.filter(seller=prof)
            print(f"     Notas deste professor: {prof_sales.count()}")
            if prof_sales.exists():
                for sale in prof_sales[:2]:
                    print(f"       * {sale.description} - {sale.created_at}")
    
    # 3. Simular a query da SingleSaleListView
    print("\n3. Simulando a query da SingleSaleListView:")
    for prof in professors[:2]:  # Testar com os primeiros 2 professores
        print(f"\n   Para professor: {prof.email}")
        
        # Esta é a mesma query usada na SingleSaleListView
        queryset = SingleSale.objects.filter(seller=prof).order_by('-created_at')
        print(f"   Notas encontradas: {queryset.count()}")
        
        if queryset.exists():
            print("   Notas:")
            for sale in queryset:
                print(f"   - ID: {sale.id}, {sale.description}, {sale.created_at}")
        else:
            print("   ❌ Nenhuma nota encontrada para este professor!")
    
    # 4. Verificar notas criadas recentemente (últimas 24h)
    print("\n4. Verificando notas criadas nas últimas 24 horas:")
    yesterday = timezone.now() - timedelta(days=1)
    recent_sales = SingleSale.objects.filter(created_at__gte=yesterday).order_by('-created_at')
    print(f"   Notas criadas nas últimas 24h: {recent_sales.count()}")
    
    if recent_sales.exists():
        print("   Notas recentes:")
        for sale in recent_sales:
            print(f"   - ID: {sale.id}, {sale.description}")
            print(f"     Vendedor: {sale.seller.email}")
            print(f"     Criado: {sale.created_at}")
    
    # 5. Verificar se há problemas com o campo seller
    print("\n5. Verificando integridade do campo seller:")
    sales_with_null_seller = SingleSale.objects.filter(seller__isnull=True)
    print(f"   Notas com seller NULL: {sales_with_null_seller.count()}")
    
    if sales_with_null_seller.exists():
        print("   ❌ PROBLEMA: Existem notas com seller NULL!")
        for sale in sales_with_null_seller:
            print(f"   - ID: {sale.id}, {sale.description}")
    
    # 6. Verificar se há usuários órfãos
    print("\n6. Verificando usuários órfãos:")
    for sale in all_sales[:5]:
        try:
            seller = sale.seller
            print(f"   Nota {sale.id}: seller OK ({seller.email})")
        except User.DoesNotExist:
            print(f"   ❌ Nota {sale.id}: seller não existe!")
    
    print("\n=== FIM DA INVESTIGAÇÃO ===")

if __name__ == "__main__":
    debug_singlesale_issue() 