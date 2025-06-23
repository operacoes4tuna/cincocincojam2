from django.core.management.base import BaseCommand
from invoices.models import InvoicePixPayment
from invoices.pix_service import InvoicePixService
import logging

logger = logging.getLogger('invoices')

class Command(BaseCommand):
    help = 'Corrige QR codes dos pagamentos Pix existentes que não possuem dados base64'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força a regeneração mesmo se já tiver QR code',
        )

    def handle(self, *args, **options):
        self.stdout.write('Iniciando correção de QR codes dos pagamentos Pix...')
        
        # Buscar pagamentos Pix que precisam de correção
        if options['force']:
            pix_payments = InvoicePixPayment.objects.filter(status='PENDING')
            self.stdout.write(f'Modo FORCE: processando {pix_payments.count()} pagamentos')
        else:
            pix_payments = InvoicePixPayment.objects.filter(
                status='PENDING',
                qrcode_image_data__isnull=True
            )
            self.stdout.write(f'Processando {pix_payments.count()} pagamentos sem QR code local')
        
        service = InvoicePixService()
        
        for pix_payment in pix_payments:
            try:
                self.stdout.write(f'Processando pagamento #{pix_payment.id}...')
                
                # Obter valor da invoice
                amount = service._get_invoice_amount(pix_payment.invoice)
                if not amount:
                    self.stdout.write(
                        self.style.WARNING(f'  Não foi possível obter valor da invoice {pix_payment.invoice.id}')
                    )
                    continue
                
                # Gerar BR code
                brcode = service._generate_mock_brcode(pix_payment, amount)
                
                # Gerar QR code local
                qr_code_data = service._generate_local_qrcode(brcode)
                
                # Atualizar o pagamento
                pix_payment.brcode = brcode
                pix_payment.qrcode_image_data = qr_code_data
                
                # Atualizar provider_response
                if not pix_payment.provider_response:
                    pix_payment.provider_response = {}
                
                pix_payment.provider_response.update({
                    'fallback': True,
                    'method': 'local_qrcode_fix',
                    'fixed_at': '2025-06-23T15:45:00.000Z'
                })
                
                pix_payment.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ QR code gerado para pagamento #{pix_payment.id}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Erro no pagamento #{pix_payment.id}: {str(e)}')
                )
                logger.error(f'Erro ao corrigir QR code do pagamento {pix_payment.id}: {str(e)}')
        
        self.stdout.write(
            self.style.SUCCESS('Correção de QR codes concluída!')
        ) 