import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from courses.models import Course, Enrollment
from payments.models import PaymentTransaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Gera dados financeiros de teste, incluindo matrículas e transações de pagamento'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enrollments',
            type=int,
            default=20,
            help='Número de matrículas a serem geradas'
        )
        parser.add_argument(
            '--paid-percentage',
            type=int,
            default=70,
            help='Percentual de matrículas que devem ser marcadas como pagas'
        )

    def handle(self, *args, **options):
        num_enrollments = options['enrollments']
        paid_percentage = options['paid_percentage']
        
        students = User.objects.filter(user_type='STUDENT')
        courses = Course.objects.filter(status=Course.Status.PUBLISHED)
        
        if not students:
            self.stdout.write(self.style.ERROR('Nenhum aluno encontrado no sistema.'))
            return
            
        if not courses:
            self.stdout.write(self.style.ERROR('Nenhum curso publicado encontrado no sistema.'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'Gerando {num_enrollments} matrículas...'))
        
        # Contador de registros criados
        enrollments_created = 0
        transactions_paid = 0
        
        # Gerar matrículas aleatórias
        for i in range(num_enrollments):
            student = random.choice(students)
            course = random.choice(courses)
            
            # Verificar se já existe matrícula para este aluno/curso
            if Enrollment.objects.filter(student=student, course=course).exists():
                continue
                
            # Criar matrícula (isso também criará uma transação pendente automaticamente)
            enrollment = Enrollment.objects.create(
                student=student,
                course=course,
                status=Enrollment.Status.ACTIVE,
                progress=random.randint(0, 100)
            )
            enrollments_created += 1
            
            # Definir uma data de matrícula no passado (entre 1 e 60 dias atrás)
            days_ago = random.randint(1, 60)
            past_date = timezone.now() - timedelta(days=days_ago)
            
            # Atualizar a data de matrícula
            enrollment.enrolled_at = past_date
            enrollment.save(update_fields=['enrolled_at'])
            
            # Recuperar a transação criada automaticamente e definir sua data
            transaction = PaymentTransaction.objects.filter(enrollment=enrollment).first()
            if transaction:
                transaction.created_at = past_date
                
                # Definir uma porcentagem das transações como pagas
                if random.randint(1, 100) <= paid_percentage:
                    payment_date = past_date + timedelta(days=random.randint(0, 3))
                    transaction.mark_as_paid()
                    transaction.payment_date = payment_date
                    transaction.payment_method = random.choice(['Cartão de Crédito', 'Boleto', 'Pix', 'Transferência'])
                    transaction.transaction_id = f'TRX-{random.randint(100000, 999999)}'
                    transactions_paid += 1
                
                transaction.save()
        
        self.stdout.write(self.style.SUCCESS(f'Gerados com sucesso: {enrollments_created} matrículas'))
        self.stdout.write(self.style.SUCCESS(f'Transações marcadas como pagas: {transactions_paid}'))
