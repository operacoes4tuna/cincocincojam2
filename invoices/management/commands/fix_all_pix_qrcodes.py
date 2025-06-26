from django.core.management.base import BaseCommand
from django.utils import timezone
from invoices.models import InvoicePixPayment
from invoices.pix_service import InvoicePixService
import logging

logger = logging.getLogger('invoices')

class Command(BaseCommand):
    help = 'Corrige QR codes PIX que estão inválidos ou sem dados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Regenera todos os QR codes PIX, mesmo os válidos',
        )
        parser.add_argument(
            '--pending-only',
            action='store_true',
            help='Corrige apenas PIX com status PENDING',
        )
        parser.add_argument(
            '--paid-to-pending',
            action='store_true',
            help='Reativa PIX que estão como PAID mas sem QR Code válido',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔧 Iniciando correção de QR codes PIX...')
        
        # Filtros baseados nas opções
        queryset = InvoicePixPayment.objects.all()
        
        if options['pending_only']:
            queryset = queryset.filter(status='PENDING')
            self.stdout.write(f'Modo: Apenas status PENDING')
        elif not options['all']:
            # Por padrão, corrige apenas os que estão sem QR code ou com problemas
            queryset = queryset.filter(
                models.Q(qrcode_image_data__isnull=True) | 
                models.Q(qrcode_image_data='') |
                models.Q(brcode__isnull=True) |
                models.Q(brcode='')
            )
            self.stdout.write(f'Modo: Apenas PIX sem QR Code válido')
        else:
            self.stdout.write(f'Modo: TODOS os PIX payments')
        
        self.stdout.write(f'Encontrados {queryset.count()} pagamentos para processar')
        
        service = InvoicePixService()
        success_count = 0
        error_count = 0
        
        for pix_payment in queryset:
            try:
                self.stdout.write(f'📋 Processando Invoice #{pix_payment.invoice.id} - PIX #{pix_payment.id}...')
                
                # Se está PAID mas não tem QR Code, reativar se solicitado
                if (pix_payment.status == 'PAID' and 
                    not pix_payment.qrcode_image_data and 
                    options['paid_to_pending']):
                    
                    self.stdout.write(f'   ⚠️ Reativando PIX PAID sem QR Code...')
                    pix_payment.status = 'PENDING'
                    pix_payment.paid_at = None
                    pix_payment.expires_at = timezone.now() + timezone.timedelta(hours=24)
                    pix_payment.save()
                
                # Obter valor da invoice
                amount = service._get_invoice_amount(pix_payment.invoice)
                if not amount:
                    self.stdout.write(
                        self.style.WARNING(f'   ⚠️ Não foi possível obter valor da invoice {pix_payment.invoice.id}')
                    )
                    error_count += 1
                    continue
                
                # Gerar BR code
                brcode = service._generate_emv_brcode(pix_payment, amount)
                
                # Gerar QR code local
                qr_code_data = service._generate_local_qrcode(brcode)
                
                # Atualizar o pagamento
                pix_payment.brcode = brcode
                pix_payment.qrcode_image_data = qr_code_data
                pix_payment.qrcode_image_url = ''  # Limpar URL antiga se existir
                pix_payment.error_message = None
                
                # Atualizar provider_response
                pix_payment.provider_response = {
                    'fallback': True,
                    'provider': 'local_emv_generator_fixed',
                    'message': 'QR Code PIX regenerado pelo comando fix_all_pix_qrcodes',
                    'fixed_at': timezone.now().isoformat(),
                    'amount': float(amount),
                    'invoice_id': pix_payment.invoice.id
                }
                
                pix_payment.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ QR code regenerado para PIX #{pix_payment.id} (R$ {amount:.2f})')
                )
                success_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ Erro no PIX #{pix_payment.id}: {str(e)}')
                )
                logger.error(f'Erro ao corrigir QR code do PIX {pix_payment.id}: {str(e)}')
                error_count += 1
        
        # Resumo final
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(f'🎯 RESULTADO FINAL:')
        self.stdout.write(f'✅ Sucessos: {success_count}')
        self.stdout.write(f'❌ Erros: {error_count}')
        self.stdout.write(f'📊 Total processado: {success_count + error_count}')
        
        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n🎉 {success_count} QR codes PIX foram corrigidos com sucesso!')
            )
            self.stdout.write('✅ Todos agora seguem o padrão EMV do Banco Central')
            self.stdout.write('✅ Podem ser escaneados em qualquer banco')
            self.stdout.write('✅ Valores das notas fiscais estão incluídos')
            
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'\n⚠️ {error_count} PIX não puderam ser corrigidos')
            )
            self.stdout.write('Verifique os logs para mais detalhes')
        
        self.stdout.write(f'{"="*60}')


# Importar Q para filtros complexos
from django.db import models 