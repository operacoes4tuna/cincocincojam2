#!/usr/bin/env python
"""
Script para verificar matrículas e transações existentes e criar uma simulação
de transação para o teste de emissão de nota fiscal.
"""
import os
import sys
import django
from datetime import datetime

# Configurar ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Agora podemos importar os modelos
from django.contrib.auth import get_user_model
from courses.models import Course, Enrollment
from payments.models import PaymentTransaction
from invoices.models import Invoice

User = get_user_model()

def main():
    # Obter usuários de teste
    print("\n=== Usuários ===")
    professor = User.objects.get(email='professor@example.com')
    print(f"Professor: {professor.get_full_name() or professor.email} (ID: {professor.id})")
    
    try:
        student = User.objects.get(email='aluno@example.com')
        print(f"Aluno: {student.get_full_name() or student.email} (ID: {student.id})")
    except User.DoesNotExist:
        print("Aluno de teste não encontrado (aluno@example.com)")
        return
    
    # Verificar cursos do professor
    print("\n=== Cursos do Professor ===")
    courses = Course.objects.filter(professor=professor)
    print(f"Total de cursos: {courses.count()}")
    
    for course in courses:
        print(f"\nCurso: {course.title} (ID: {course.id})")
        print(f"Preço: R$ {course.price}")
        print(f"Status: {course.status}")
        
        # Verificar matrículas para este curso
        enrollments = Enrollment.objects.filter(course=course)
        print(f"Matrículas: {enrollments.count()}")
        
        for enrollment in enrollments:
            print(f"  - Aluno: {enrollment.student.email}")
            print(f"    Status: {enrollment.status}")
            print(f"    Data: {enrollment.enrolled_at}")
            
            # Verificar transações para esta matrícula
            transactions = PaymentTransaction.objects.filter(enrollment=enrollment)
            print(f"    Transações: {transactions.count()}")
            
            for tx in transactions:
                print(f"      * ID: {tx.id}, Valor: R$ {tx.amount}, Status: {tx.status}")
                
                # Verificar se há notas fiscais para esta transação
                invoices = Invoice.objects.filter(transaction=tx)
                print(f"        Notas Fiscais: {invoices.count()}")
                for invoice in invoices:
                    print(f"        > ID: {invoice.id}, Status: {invoice.status}, Focus Status: {invoice.focus_status}")
    
    # Verificar se precisamos criar uma transação de teste
    print("\n=== Verificando necessidade de dados para teste ===")
    
    # Verificar se existe pelo menos uma matrícula ativa
    enrollments = Enrollment.objects.filter(course__professor=professor, status='active')
    if not enrollments.exists():
        print("Não existem matrículas ativas. Criando uma matrícula de teste...")
        
        # Selecionar o primeiro curso disponível
        course = courses.filter(status='published').first()
        if not course:
            print("Não há cursos publicados disponíveis para criar matrícula.")
            return
        
        # Criar matrícula
        enrollment = Enrollment.objects.create(
            course=course,
            student=student,
            status='active',
            enrolled_at=datetime.now()
        )
        print(f"Matrícula criada: ID={enrollment.id}, Curso={course.title}")
        enrollments = [enrollment]
    else:
        print(f"Existem {enrollments.count()} matrículas ativas.")
    
    # Verificar se existe pelo menos uma transação aprovada
    transactions = PaymentTransaction.objects.filter(
        enrollment__in=enrollments,
        status='approved'
    )
    
    if not transactions.exists():
        print("Não existem transações aprovadas. Criando uma transação de teste...")
        
        # Usar a primeira matrícula encontrada
        enrollment = enrollments.first()
        
        # Criar transação
        transaction = PaymentTransaction.objects.create(
            enrollment=enrollment,
            amount=enrollment.course.price,
            status='approved',
            payment_method='credit_card',
            payment_date=datetime.now()
        )
        print(f"Transação criada: ID={transaction.id}, Valor=R${transaction.amount}")
    else:
        print(f"Existem {transactions.count()} transações aprovadas.")
        transaction = transactions.first()
        print(f"Primeira transação: ID={transaction.id}, Valor=R${transaction.amount}")
    
    # Verificar se já existe nota fiscal para esta transação
    invoices = Invoice.objects.filter(transaction=transaction)
    if invoices.exists():
        print(f"Já existem {invoices.count()} notas fiscais para a transação {transaction.id}.")
        for invoice in invoices:
            print(f"  > ID: {invoice.id}, Status: {invoice.status}, Focus Status: {invoice.focus_status}")
    else:
        print(f"Não existem notas fiscais para a transação {transaction.id}.")
    
    print("\n=== RESUMO PARA TESTE DE EMISSÃO ===")
    print(f"Transação para usar no teste: ID={transaction.id}")
    print(f"Execute: python test_nfe_emission.py --transaction-id {transaction.id}")

if __name__ == "__main__":
    main()
