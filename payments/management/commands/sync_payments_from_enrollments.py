import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from courses.models import Enrollment
from payments.models import PaymentTransaction

class Command(BaseCommand):
    help = 'Sincroniza pagamentos a partir de matrículas existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--paid-percentage',
            type=int,
            default=70,
            help='Percentual de matrículas que devem ter status pago'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Se especificado, cria transações mesmo para matrículas que já têm transações'
        )

    def handle(self, *args, **options):
        paid_percentage = options['paid_percentage']
        force = options['force']

        # Obter todas as matrículas ativas
        enrollments = Enrollment.objects.filter(status=Enrollment.Status.ACTIVE)
        
        # Contar as matrículas processadas
        enrollments_processed = 0
        transactions_created = 0
        transactions_paid = 0
        
        self.stdout.write(self.style.SUCCESS(f'Iniciando sincronização de pagamentos para {enrollments.count()} matrículas...'))
        
        # Para cada matrícula
        for enrollment in enrollments:
            # Verificar se já tem transação, a menos que force=True
            if not force and PaymentTransaction.objects.filter(enrollment=enrollment).exists():
                continue
                
            # Criar uma transação para a matrícula
            created_at = enrollment.enrolled_at
            transaction = PaymentTransaction.objects.create(
                enrollment=enrollment,
                amount=enrollment.course.price,
                status=PaymentTransaction.Status.PENDING,
                created_at=created_at
            )
            
            # Atualizar a data de criação manualmente
            transaction.created_at = created_at
            transaction.save(update_fields=['created_at'])
            
            transactions_created += 1
            enrollments_processed += 1
            
            # Definir uma porcentagem como pagas
            if random.randint(1, 100) <= paid_percentage:
                # Data de pagamento entre 0 e 5 dias após a matrícula
                payment_delay = random.randint(0, 5)
                payment_date = created_at + timedelta(days=payment_delay)
                if payment_date > timezone.now():
                    payment_date = timezone.now()
                
                transaction.status = PaymentTransaction.Status.PAID
                transaction.payment_date = payment_date
                transaction.payment_method = random.choice(['Cartão de Crédito', 'Boleto', 'Pix', 'Transferência'])
                transaction.transaction_id = f'TRX-{random.randint(100000, 999999)}'
                transaction.save()
                
                transactions_paid += 1
        
        self.stdout.write(self.style.SUCCESS(f'Sincronização concluída:'))
        self.stdout.write(f'   - Matrículas processadas: {enrollments_processed}')
        self.stdout.write(f'   - Transações criadas: {transactions_created}')
        self.stdout.write(f'   - Transações marcadas como pagas: {transactions_paid}')
        
        # Verificar estado atual do sistema
        total_enrollments = Enrollment.objects.count()
        total_transactions = PaymentTransaction.objects.count()
        paid_transactions = PaymentTransaction.objects.filter(status=PaymentTransaction.Status.PAID).count()
        
        self.stdout.write(self.style.SUCCESS('Estado atual do sistema:'))
        self.stdout.write(f'   - Total de matrículas: {total_enrollments}')
        self.stdout.write(f'   - Total de transações: {total_transactions}')
        self.stdout.write(f'   - Transações pagas: {paid_transactions}')
