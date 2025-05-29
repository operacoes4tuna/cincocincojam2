import os
import sys
import django
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from payments.models import PaymentTransaction
from invoices.models import Invoice, CompanyConfig
from invoices.services import NFEioService

class Command(BaseCommand):
    help = 'Diagnostica problemas na emissão de notas fiscais'

    def add_arguments(self, parser):
        parser.add_argument(
            '--transaction-id',
            type=int,
            help='ID da transação para diagnosticar'
        )
        parser.add_argument(
            '--professor-id',
            type=int,
            help='ID do professor para verificar configuração'
        )

    def print_header(self, text):
        """Imprime um cabeçalho formatado"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(f" {text} ".center(80, "="))
        self.stdout.write("="*80 + "\n")

    def print_step(self, text):
        """Imprime um passo do processo"""
        self.stdout.write(f"\n>>> {text}")

    def print_success(self, text):
        """Imprime uma mensagem de sucesso"""
        self.stdout.write(self.style.SUCCESS(f"\n✅ {text}"))

    def print_error(self, text):
        """Imprime uma mensagem de erro"""
        self.stdout.write(self.style.ERROR(f"\n❌ {text}"))

    def print_warning(self, text):
        """Imprime uma mensagem de aviso"""
        self.stdout.write(self.style.WARNING(f"\n⚠️ {text}"))

    def print_info(self, text):
        """Imprime uma mensagem informativa"""
        self.stdout.write(f"\nℹ️ {text}")

    def check_api_config(self):
        """Verifica a configuração da API NFE.io"""
        self.print_step("Verificando configuração da API NFE.io...")
        
        if not settings.NFEIO_API_KEY:
            self.print_error("API Key não configurada")
            return False
            
        if not settings.NFEIO_COMPANY_ID:
            self.print_error("Company ID não configurado")
            return False
            
        if not settings.NFEIO_ENVIRONMENT:
            self.print_error("Ambiente não configurado")
            return False
            
        self.print_success("Configuração da API OK")
        return True

    def check_professor_config(self, professor):
        """Verifica a configuração do professor"""
        self.print_step(f"Verificando configuração do professor {professor.username}...")
        
        try:
            company_config = CompanyConfig.objects.get(user=professor)
            
            if not company_config.enabled:
                self.print_error("Emissão de notas fiscais desabilitada")
                return False
                
            if not company_config.is_complete():
                self.print_error("Configuração incompleta")
                missing_fields = []
                
                if not company_config.cnpj:
                    missing_fields.append("CNPJ")
                if not company_config.razao_social:
                    missing_fields.append("Razão Social")
                if not company_config.nome_fantasia:
                    missing_fields.append("Nome Fantasia")
                if not company_config.regime_tributario:
                    missing_fields.append("Regime Tributário")
                if not company_config.endereco:
                    missing_fields.append("Endereço")
                if not company_config.numero:
                    missing_fields.append("Número")
                if not company_config.bairro:
                    missing_fields.append("Bairro")
                if not company_config.municipio:
                    missing_fields.append("Município")
                if not company_config.uf:
                    missing_fields.append("UF")
                if not company_config.cep:
                    missing_fields.append("CEP")
                if not company_config.inscricao_municipal:
                    missing_fields.append("Inscrição Municipal")
                    
                self.print_error(f"Campos faltando: {', '.join(missing_fields)}")
                return False
                
            self.print_success("Configuração do professor OK")
            return True
            
        except CompanyConfig.DoesNotExist:
            self.print_error("Professor não possui configuração de empresa")
            return False

    def check_student_data(self, student):
        """Verifica os dados do aluno"""
        self.print_step(f"Verificando dados do aluno {student.username}...")
        
        missing_fields = []
        
        if not student.cpf:
            missing_fields.append("CPF")
        if not student.get_full_name():
            missing_fields.append("Nome completo")
        if not student.email:
            missing_fields.append("Email")
        if not student.address_line:
            missing_fields.append("Endereço")
        if not student.address_number:
            missing_fields.append("Número")
        if not student.neighborhood:
            missing_fields.append("Bairro")
        if not student.city:
            missing_fields.append("Cidade")
        if not student.state:
            missing_fields.append("Estado")
        if not student.zipcode:
            missing_fields.append("CEP")
            
        if missing_fields:
            self.print_error(f"Campos faltando: {', '.join(missing_fields)}")
            return False
            
        self.print_success("Dados do aluno OK")
        return True

    def check_transaction(self, transaction):
        """Verifica a transação"""
        self.print_step(f"Verificando transação {transaction.id}...")
        
        if transaction.status != 'approved':
            self.print_error(f"Transação não está aprovada (status: {transaction.status})")
            return False
            
        if not transaction.amount:
            self.print_error("Transação sem valor")
            return False
            
        self.print_success("Transação OK")
        return True

    def check_invoice(self, invoice):
        """Verifica a nota fiscal"""
        self.print_step(f"Verificando nota fiscal {invoice.id}...")
        
        if invoice.status == 'error':
            self.print_error(f"Nota fiscal com erro: {invoice.error_message}")
            return False
            
        if not invoice.rps_numero:
            self.print_error("Nota fiscal sem número RPS")
            return False
            
        self.print_success("Nota fiscal OK")
        return True

    def check_connectivity(self):
        """Verifica a conectividade com a API"""
        self.print_step("Verificando conectividade com NFE.io...")
        
        service = NFEioService()
        if not service.check_connectivity():
            self.print_error("Não foi possível conectar ao serviço NFE.io")
            return False
            
        self.print_success("Conectividade OK")
        return True

    def handle(self, *args, **options):
        self.print_header("DIAGNÓSTICO DE EMISSÃO DE NOTAS FISCAIS")
        
        # 1. Verificar configuração da API
        if not self.check_api_config():
            return
            
        # 2. Verificar conectividade
        if not self.check_connectivity():
            return
            
        # 3. Verificar transação específica se informada
        if options['transaction_id']:
            try:
                transaction = PaymentTransaction.objects.get(id=options['transaction_id'])
                
                if not self.check_transaction(transaction):
                    return
                    
                if not self.check_student_data(transaction.enrollment.student):
                    return
                    
                if not self.check_professor_config(transaction.enrollment.course.professor):
                    return
                    
                # Verificar nota fiscal existente
                invoice = Invoice.objects.filter(transaction=transaction).first()
                if invoice:
                    if not self.check_invoice(invoice):
                        return
                        
            except PaymentTransaction.DoesNotExist:
                self.print_error(f"Transação {options['transaction_id']} não encontrada")
                return
                
        # 4. Verificar professor específico se informado
        elif options['professor_id']:
            try:
                professor = User.objects.get(id=options['professor_id'])
                if not self.check_professor_config(professor):
                    return
            except User.DoesNotExist:
                self.print_error(f"Professor {options['professor_id']} não encontrado")
                return
                
        # 5. Verificar todas as transações aprovadas sem nota fiscal
        else:
            self.print_step("Verificando transações aprovadas sem nota fiscal...")
            
            transactions = PaymentTransaction.objects.filter(
                status='approved'
            ).exclude(
                invoices__isnull=False
            )
            
            if not transactions.exists():
                self.print_success("Não há transações aprovadas sem nota fiscal")
                return
                
            self.print_info(f"Encontradas {transactions.count()} transações aprovadas sem nota fiscal")
            
            for transaction in transactions:
                self.print_step(f"\nVerificando transação {transaction.id}...")
                
                if not self.check_transaction(transaction):
                    continue
                    
                if not self.check_student_data(transaction.enrollment.student):
                    continue
                    
                if not self.check_professor_config(transaction.enrollment.course.professor):
                    continue
                    
                self.print_success(f"Transação {transaction.id} pronta para emissão de nota fiscal") 