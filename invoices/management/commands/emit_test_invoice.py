import time
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from invoices.models import CompanyConfig, Invoice
from invoices.services import NFEioService
from payments.models import PaymentTransaction
from courses.models import Enrollment

User = get_user_model()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Emite uma nota fiscal de teste para um professor específico e acompanha todo o processo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='professor@example.com',
            help='Email do professor que emitirá a nota fiscal'
        )
        parser.add_argument(
            '--transaction-id',
            type=int,
            default=None,
            help='ID da transação a ser usada (caso não seja informado, será buscada automaticamente)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Intervalo em segundos para verificação do status da nota'
        )
        parser.add_argument(
            '--max-checks',
            type=int,
            default=12,
            help='Número máximo de verificações de status'
        )

    def handle(self, *args, **options):
        email = options['email']
        transaction_id = options['transaction_id']
        interval = options['interval']
        max_checks = options['max_checks']

        try:
            # 1. Obter o professor
            self.stdout.write(self.style.NOTICE(f"Buscando professor com email {email}..."))
            professor = User.objects.get(email=email)
            self.stdout.write(self.style.SUCCESS(f"Professor encontrado: {professor.get_full_name() or professor.email} (ID: {professor.id})"))

            # 2. Verificar se o professor possui configuração fiscal
            self.stdout.write(self.style.NOTICE("Verificando configuração fiscal..."))
            try:
                company_config = CompanyConfig.objects.get(user=professor)
                
                if not company_config.is_complete():
                    self.stdout.write(self.style.ERROR("Configuração fiscal incompleta. Verifique os dados do professor."))
                    return
                
                self.stdout.write(self.style.SUCCESS(f"Configuração fiscal encontrada e válida:\n"
                                                    f"  CNPJ: {company_config.cnpj}\n"
                                                    f"  Razão Social: {company_config.razao_social}\n"
                                                    f"  Nome Fantasia: {company_config.nome_fantasia}\n"
                                                    f"  Regime Tributário: {company_config.regime_tributario}"))
            except CompanyConfig.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Professor {email} não possui configuração fiscal."))
                return

            # 3. Buscar ou selecionar uma transação de pagamento
            if transaction_id:
                self.stdout.write(self.style.NOTICE(f"Buscando transação com ID {transaction_id}..."))
                try:
                    transaction = PaymentTransaction.objects.get(id=transaction_id)
                except PaymentTransaction.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Transação com ID {transaction_id} não encontrada."))
                    return
            else:
                self.stdout.write(self.style.NOTICE("Buscando transações disponíveis do professor..."))
                # Buscar matrículas em cursos do professor que tenham transações pagas
                enrollments = Enrollment.objects.filter(
                    course__professor=professor,
                    status=Enrollment.Status.ACTIVE
                ).select_related('course', 'student')
                
                if not enrollments.exists():
                    self.stdout.write(self.style.ERROR("Nenhuma matrícula ativa encontrada para o professor."))
                    return
                
                # Buscar transações das matrículas
                transactions = PaymentTransaction.objects.filter(
                    enrollment__in=enrollments,
                    status=PaymentTransaction.Status.PAID
                ).order_by('-created_at')
                
                if not transactions.exists():
                    self.stdout.write(self.style.ERROR("Nenhuma transação aprovada encontrada para o professor."))
                    return
                
                # Selecionar a transação mais recente que ainda não tem nota fiscal
                transaction = None
                for tx in transactions:
                    if not Invoice.objects.filter(transaction=tx).exists():
                        transaction = tx
                        break
                
                if not transaction:
                    transaction = transactions.first()
                    self.stdout.write(self.style.WARNING("Todas as transações já possuem notas fiscais. Usando a mais recente."))
            
            # Mostrar detalhes da transação
            self.stdout.write(self.style.SUCCESS(f"Transação selecionada:\n"
                                               f"  ID: {transaction.id}\n"
                                               f"  Valor: R$ {transaction.amount:.2f}\n"
                                               f"  Data: {transaction.created_at}\n"
                                               f"  Curso: {transaction.enrollment.course.title}\n"
                                               f"  Aluno: {transaction.enrollment.student.get_full_name() or transaction.enrollment.student.email}"))

            # 4. Criar objeto Invoice
            self.stdout.write(self.style.NOTICE("Criando registro de nota fiscal..."))
            
            # Verificar se já existe uma nota para esta transação
            existing_invoice = Invoice.objects.filter(transaction=transaction).first()
            if existing_invoice:
                self.stdout.write(self.style.WARNING(f"Já existe uma nota fiscal para esta transação (ID: {existing_invoice.id}, Status: {existing_invoice.status})."))
                invoice = existing_invoice
                if invoice.status in ['approved', 'cancelled']:
                    self.stdout.write(self.style.NOTICE("A nota fiscal existente já está finalizada. Criando uma nova..."))
                    # Criar nova nota para a mesma transação para fins de teste
                    invoice = Invoice.objects.create(
                        transaction=transaction,
                        status='pending'
                    )
            else:
                invoice = Invoice.objects.create(
                    transaction=transaction,
                    status='pending'
                )
            
            self.stdout.write(self.style.SUCCESS(f"Nota fiscal criada/selecionada com ID: {invoice.id}"))

            # 5. Iniciar processo de emissão da nota fiscal
            self.stdout.write(self.style.NOTICE("Iniciando processo de emissão..."))
            service = NFEioService()
            
            # Emitir a nota
            self.stdout.write(self.style.WARNING("EMITINDO NOTA FISCAL..."))
            emission_result = service.emit_invoice(invoice)
            
            if emission_result.get('error'):
                self.stdout.write(self.style.ERROR(f"Erro na emissão: {emission_result.get('message')}"))
                return
            
            self.stdout.write(self.style.SUCCESS("Nota fiscal enviada para processamento!"))
            self.stdout.write(f"  ID Externo: {invoice.external_id}")
            self.stdout.write(f"  Status: {invoice.status}")
            self.stdout.write(f"  Status API: {invoice.focus_status}")
            
            # 6. Acompanhar o status até finalizar ou atingir o limite de verificações
            self.stdout.write(self.style.NOTICE(f"Acompanhando status da nota fiscal a cada {interval} segundos..."))
            
            check_count = 0
            while check_count < max_checks:
                check_count += 1
                self.stdout.write(f"Verificação {check_count}/{max_checks}...")
                
                # Esperar pelo intervalo configurado
                time.sleep(interval)
                
                # Verificar status
                self.stdout.write("Verificando status atual...")
                status_result = service.check_invoice_status(invoice)
                
                # Recarregar o objeto invoice para ter os dados mais atualizados
                invoice.refresh_from_db()
                
                # Mostrar status atual
                self.stdout.write(f"  Status atual: {invoice.status}")
                self.stdout.write(f"  Status API: {invoice.focus_status}")
                
                # Verificar se já finalizou o processamento
                if invoice.status in ['approved', 'cancelled', 'error']:
                    break
            
            # 7. Exibir resultado final
            self.stdout.write("\n" + "="*80)
            self.stdout.write(self.style.NOTICE("RESULTADO FINAL DA EMISSÃO:"))
            self.stdout.write("="*80)
            invoice.refresh_from_db()
            
            if invoice.status == 'approved':
                self.stdout.write(self.style.SUCCESS("✅ NOTA FISCAL EMITIDA COM SUCESSO!"))
            elif invoice.status == 'error':
                self.stdout.write(self.style.ERROR(f"❌ ERRO NA EMISSÃO: {invoice.error_message}"))
            elif invoice.status == 'cancelled':
                self.stdout.write(self.style.WARNING("🚫 NOTA FISCAL CANCELADA"))
            else:
                self.stdout.write(self.style.WARNING(f"⏳ NOTA FISCAL AINDA EM PROCESSAMENTO (Status: {invoice.status}, API Status: {invoice.focus_status})"))
            
            self.stdout.write("\nDetalhes da nota fiscal:")
            self.stdout.write(f"  ID: {invoice.id}")
            self.stdout.write(f"  ID Externo (NFE.io): {invoice.external_id}")
            self.stdout.write(f"  Status interno: {invoice.status}")
            self.stdout.write(f"  Status API: {invoice.focus_status}")
            self.stdout.write(f"  Criada em: {invoice.created_at}")
            self.stdout.write(f"  Atualizada em: {invoice.updated_at}")
            
            if invoice.focus_pdf_url:
                self.stdout.write(f"  PDF: {invoice.focus_pdf_url}")
            if invoice.focus_xml_url:
                self.stdout.write(f"  XML: {invoice.focus_xml_url}")
            
            if invoice.error_message:
                self.stdout.write(f"\nMensagem de erro: {invoice.error_message}")
            
            self.stdout.write("\n" + "="*80)
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Professor com email {email} não encontrado."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro inesperado: {str(e)}"))
            import traceback
            traceback.print_exc()
