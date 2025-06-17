from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

from payments.models import PaymentTransaction
from payments.openpix_service import OpenPixService
from courses.models import Enrollment


class Command(BaseCommand):
    help = 'Verifica o status de pagamentos PIX pendentes e atualiza automaticamente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-age-hours',
            type=int,
            default=24,
            help='Verificar apenas pagamentos com no máximo X horas (padrão: 24)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa sem fazer alterações no banco de dados'
        )
        parser.add_argument(
            '--force-all',
            action='store_true',
            help='Verifica todos os pagamentos pendentes, independente da idade'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostra informações detalhadas durante a execução'
        )

    def handle(self, *args, **options):
        """
        Executa a verificação de status dos pagamentos PIX pendentes.
        """
        # Configurar logging
        logger = logging.getLogger('payments')
        if options['verbose']:
            logging.basicConfig(level=logging.INFO)

        self.stdout.write(
            self.style.SUCCESS('🔍 Iniciando verificação de pagamentos PIX pendentes...')
        )

        # Determinar o filtro de data
        if options['force_all']:
            self.stdout.write('📅 Verificando TODOS os pagamentos pendentes...')
            queryset = PaymentTransaction.objects.filter(
                payment_method='PIX',
                status=PaymentTransaction.Status.PENDING,
                correlation_id__isnull=False
            ).exclude(correlation_id='')
        else:
            max_age = timezone.now() - timedelta(hours=options['max_age_hours'])
            self.stdout.write(f'📅 Verificando pagamentos dos últimos {options["max_age_hours"]} horas...')
            queryset = PaymentTransaction.objects.filter(
                payment_method='PIX',
                status=PaymentTransaction.Status.PENDING,
                correlation_id__isnull=False,
                created_at__gte=max_age
            ).exclude(correlation_id='')

        pending_transactions = queryset.order_by('created_at')
        total_count = pending_transactions.count()

        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('⚠️  Nenhum pagamento PIX pendente encontrado.')
            )
            return

        self.stdout.write(f'📊 Encontrados {total_count} pagamentos PIX pendentes para verificar.')

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('🔍 MODO DRY-RUN: Nenhuma alteração será feita no banco de dados.')
            )

        # Inicializar serviço PIX
        try:
            openpix = OpenPixService()
            health_check = openpix.health_check()
            
            if health_check.get('status') != 'healthy':
                self.stdout.write(
                    self.style.ERROR(f'❌ API PIX não está saudável: {health_check}')
                )
                if not options['force_all']:
                    return
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠️  Continuando mesmo com API não saudável (--force-all ativo)...')
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao inicializar serviço PIX: {str(e)}')
            )
            return

        # Contadores
        checked_count = 0
        updated_count = 0
        error_count = 0
        paid_count = 0

        # Processar cada transação
        for transaction in pending_transactions:
            checked_count += 1
            
            try:
                if options['verbose']:
                    self.stdout.write(
                        f'🔍 Verificando pagamento #{transaction.id} '
                        f'(correlação: {transaction.correlation_id})'
                    )

                # Verificar status na API
                status_data = openpix.get_charge_status(transaction.correlation_id)
                
                if not status_data:
                    error_count += 1
                    if options['verbose']:
                        self.stdout.write(
                            self.style.ERROR(f'❌ Erro ao consultar status do pagamento #{transaction.id}')
                        )
                    continue

                current_status = status_data.get('status')
                
                if options['verbose']:
                    self.stdout.write(f'📋 Status atual: {current_status}')

                # Processar mudança de status
                if current_status == 'COMPLETED':
                    if not options['dry_run']:
                        # Atualizar transação
                        transaction.status = PaymentTransaction.Status.PAID
                        transaction.payment_date = timezone.now()
                        transaction.save()

                        # Atualizar matrícula
                        enrollment = transaction.enrollment
                        enrollment.status = Enrollment.Status.ACTIVE
                        enrollment.save()

                        updated_count += 1
                        paid_count += 1

                        logger.info(f'Pagamento #{transaction.id} marcado como pago automaticamente')

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Pagamento #{transaction.id} confirmado! '
                            f'Aluno: {transaction.enrollment.student.email} '
                            f'Curso: {transaction.enrollment.course.title}'
                        )
                    )

                elif current_status in ['EXPIRED', 'CANCELLED']:
                    if not options['dry_run']:
                        transaction.status = PaymentTransaction.Status.FAILED
                        transaction.save()
                        updated_count += 1

                    self.stdout.write(
                        self.style.ERROR(
                            f'❌ Pagamento #{transaction.id} expirou/cancelado - Status: {current_status}'
                        )
                    )

                elif current_status == 'ACTIVE':
                    if options['verbose']:
                        self.stdout.write(f'⏳ Pagamento #{transaction.id} ainda está ativo (aguardando)')

                else:
                    if options['verbose']:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  Status desconhecido: {current_status}')
                        )

            except Exception as e:
                error_count += 1
                logger.error(f'Erro ao verificar pagamento #{transaction.id}: {str(e)}')
                
                if options['verbose']:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Erro no pagamento #{transaction.id}: {str(e)}')
                    )

            # Mostrar progresso a cada 10 transações
            if checked_count % 10 == 0:
                self.stdout.write(f'📊 Progresso: {checked_count}/{total_count} verificados...')

        # Relatório final
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 RELATÓRIO FINAL'))
        self.stdout.write('='*60)
        self.stdout.write(f'🔍 Total verificado: {checked_count}')
        self.stdout.write(f'✅ Pagamentos confirmados: {paid_count}')
        self.stdout.write(f'📝 Total atualizado: {updated_count}')
        self.stdout.write(f'❌ Erros: {error_count}')
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('⚠️  MODO DRY-RUN: Nenhuma alteração foi feita no banco de dados.')
            )

        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'🎉 Verificação concluída! {updated_count} pagamentos atualizados.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ Verificação concluída! Nenhuma atualização necessária.')
            ) 