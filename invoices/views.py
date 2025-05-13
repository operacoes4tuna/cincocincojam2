from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.db import transaction as db_transaction
from django.utils.translation import gettext_lazy as _
import logging
import traceback
import json

from payments.models import PaymentTransaction
from users.decorators import professor_required, admin_required

from .models import CompanyConfig, Invoice
from .forms import CompanyConfigForm
from .services import NFEioService

# Configuração do logger
logger = logging.getLogger('invoices')

# Views para configuração de empresa

@login_required
@professor_required
def company_settings(request):
    """
    Permite que o professor configure seus dados fiscais para emissão de notas fiscais.
    """
    try:
        company_config = CompanyConfig.objects.get(user=request.user)
    except CompanyConfig.DoesNotExist:
        company_config = CompanyConfig(user=request.user)
    
    if request.method == 'POST':
        form = CompanyConfigForm(request.POST, instance=company_config)
        if form.is_valid():
            form.save()
            messages.success(request, _('Configurações fiscais atualizadas com sucesso!'))
            return redirect('invoices:company_settings')
    else:
        form = CompanyConfigForm(instance=company_config)
    
    is_complete = company_config.is_complete() if company_config.pk else False
    
    return render(request, 'invoices/company_settings.html', {
        'form': form,
        'company_config': company_config,
        'is_complete': is_complete,
    })

# Views para emissão de notas fiscais

@login_required
@professor_required
def emit_invoice(request, transaction_id):
    """
    Emite uma nota fiscal para uma transação.
    """
    try:
        transaction = get_object_or_404(
            PaymentTransaction,
            id=transaction_id,
            enrollment__course__professor=request.user
        )
        logger.debug(f"Transação encontrada: {transaction_id}, valor: {transaction.amount}, status: {transaction.status}")
    except Exception as e:
        logger.error(f"Erro ao obter transação {transaction_id}: {str(e)}")
        messages.error(request, _('Erro ao localizar transação.'))
        return redirect('payments:professor_transactions')
    
    # Verificar se já existe uma nota fiscal para esta transação
    existing_invoice = Invoice.objects.filter(transaction=transaction).first()
    if existing_invoice:
        logger.info(f"Já existe nota fiscal para transação {transaction_id}: Invoice ID {existing_invoice.id}, status: {existing_invoice.status}")
        messages.info(request, _('Já existe uma nota fiscal para esta transação.'))
        return redirect('payments:professor_transactions')
    
    # Verificar se o professor tem as configurações fiscais completas
    try:
        company_config = CompanyConfig.objects.get(user=request.user)
        if not company_config.enabled:
            logger.warning(f"Emissão de nota fiscal desabilitada para professor ID {request.user.id}")
            messages.error(request, _('A emissão de notas fiscais não está habilitada. Verifique suas configurações fiscais.'))
            return redirect('invoices:company_settings')
        
        if not company_config.is_complete():
            logger.warning(f"Configurações fiscais incompletas para professor ID {request.user.id}")
            messages.error(request, _('Configure todas as informações fiscais antes de emitir notas fiscais.'))
            return redirect('invoices:company_settings')
            
        logger.debug(f"Configurações fiscais verificadas para professor ID {request.user.id}")
    except CompanyConfig.DoesNotExist:
        logger.warning(f"Professor ID {request.user.id} não possui configuração fiscal")
        messages.error(request, _('Configure suas informações fiscais antes de emitir notas fiscais.'))
        return redirect('invoices:company_settings')
    
    # Criar a invoice no banco de dados
    logger.info(f"Criando nova invoice para transação {transaction_id}")
    with db_transaction.atomic():
        try:
            invoice = Invoice.objects.create(
                transaction=transaction,
                status='pending'
            )
            logger.debug(f"Invoice criada com ID {invoice.id}")
            
            # Tentar emitir a nota fiscal
            logger.info(f"Iniciando emissão via NFEioService para invoice ID {invoice.id}")
            service = NFEioService()
            try:
                logger.debug(f"Chamando service.emit_invoice para invoice ID {invoice.id}")
                response = service.emit_invoice(invoice)
                logger.info(f"Resposta da emissão: {json.dumps(response, indent=2)}")
                
                # Verificar se houve erro na resposta
                if response and isinstance(response, dict):
                    if response.get('error') is True:
                        logger.error(f"Erro na emissão: {response.get('message', 'Erro não especificado')}")
                        messages.error(request, _('Erro ao emitir nota fiscal: {}').format(response.get('message', 'Erro não especificado')))
                    else:
                        logger.info(f"Nota fiscal em processamento para invoice ID {invoice.id}")
                        messages.success(request, _('Nota fiscal em processamento. Acompanhe o status na lista de transações.'))
                else:
                    logger.info(f"Nota fiscal em processamento para invoice ID {invoice.id}")
                    messages.success(request, _('Nota fiscal em processamento. Acompanhe o status na lista de transações.'))
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Exceção ao emitir nota fiscal: {str(e)}\n{error_traceback}")
                messages.error(request, _('Erro ao emitir nota fiscal: {}').format(str(e)))
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Exceção ao criar invoice: {str(e)}\n{error_traceback}")
            messages.error(request, _('Erro ao criar nota fiscal: {}').format(str(e)))
    
    logger.info(f"Concluindo processo de emissão para transação {transaction_id}")
    return redirect('payments:professor_transactions')

@login_required
@professor_required
def retry_invoice(request, invoice_id):
    """
    Tenta emitir uma nota fiscal novamente.
    """
    logger.info(f"Tentando re-emitir nota fiscal ID: {invoice_id}")
    
    try:
        invoice = get_object_or_404(
            Invoice,
            id=invoice_id,
            transaction__enrollment__course__professor=request.user,
            status='error'
        )
        logger.debug(f"Invoice encontrada: {invoice_id}, status atual: {invoice.status}")
        
        service = NFEioService()
        try:
            logger.debug(f"Chamando service.emit_invoice para retry da invoice ID {invoice_id}")
            response = service.emit_invoice(invoice)
            logger.info(f"Resposta da re-emissão: {json.dumps(response, indent=2)}")
            
            if response and isinstance(response, dict):
                if response.get('error') is True:
                    logger.error(f"Erro na re-emissão: {response.get('message', 'Erro não especificado')}")
                    messages.error(request, _('Erro ao re-emitir nota fiscal: {}').format(response.get('message', 'Erro não especificado')))
                else:
                    logger.info(f"Nota fiscal em processamento após retry para invoice ID {invoice_id}")
                    messages.success(request, _('Nota fiscal em processamento. Acompanhe o status na lista de transações.'))
            else:
                logger.info(f"Nota fiscal em processamento após retry para invoice ID {invoice_id}")
                messages.success(request, _('Nota fiscal em processamento. Acompanhe o status na lista de transações.'))
                
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Exceção ao re-emitir nota fiscal: {str(e)}\n{error_traceback}")
            messages.error(request, _('Erro ao re-emitir nota fiscal: {}').format(str(e)))
            
    except Exception as e:
        logger.error(f"Erro ao localizar invoice {invoice_id} para retry: {str(e)}")
        messages.error(request, _('Nota fiscal não encontrada ou não pode ser re-emitida.'))
    
    logger.info(f"Concluindo processo de re-emissão para invoice {invoice_id}")
    return redirect('payments:professor_transactions')

@login_required
@professor_required
def check_invoice_status(request, invoice_id, format=None):
    """
    Verifica o status de uma nota fiscal.
    """
    try:
        # Obter a nota fiscal
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Verificar permissão (apenas o professor que emitiu ou o aluno destinatário)
        if not (request.user == invoice.transaction.enrollment.course.professor or 
                request.user == invoice.transaction.enrollment.student):
            if format == 'json':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Você não tem permissão para verificar esta nota fiscal.'
                }, status=403)
            messages.error(request, _('Você não tem permissão para verificar esta nota fiscal.'))
            return redirect('payments:transactions')
        
        # Verificar status atual na API NFE.io
        nfe_service = NFEioService()
        status_result = nfe_service.check_invoice_status(invoice)
        
        # Atualizar o status da nota fiscal no banco de dados
        if status_result['success']:
            invoice.status = status_result['status']
            invoice.external_status = status_result.get('external_status', '')
            invoice.external_message = status_result.get('message', '')
            invoice.last_checked = timezone.now()
            invoice.save()
        
        # Retornar resposta baseada no formato solicitado
        if format == 'json':
            return JsonResponse({
                'status': invoice.status,
                'external_status': invoice.external_status,
                'message': invoice.external_message,
                'last_checked': invoice.last_checked.isoformat() if invoice.last_checked else None,
                'success': status_result['success']
            })
        
        # Redirecionar para a página de detalhes da nota fiscal
        messages.info(request, _('Status da nota fiscal atualizado.'))
        return redirect('invoices:invoice_detail', invoice_id=invoice_id)
        
    except Exception as e:
        logger.error(f"Erro ao verificar status da nota fiscal {invoice_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        if format == 'json':
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao verificar status: {str(e)}',
                'success': False
            }, status=500)
        
        messages.error(request, _('Erro ao verificar status da nota fiscal.'))
        return redirect('payments:transactions')

@login_required
@professor_required
def cancel_invoice(request, invoice_id):
    """
    Cancela uma nota fiscal aprovada.
    """
    logger.info(f"Iniciando cancelamento de nota fiscal ID: {invoice_id}")
    
    try:
        invoice = get_object_or_404(
            Invoice,
            id=invoice_id,
            transaction__enrollment__course__professor=request.user,
            status='approved'
        )
        logger.debug(f"Invoice encontrada para cancelamento: {invoice_id}, status atual: {invoice.status}")
        
        if request.method == 'POST':
            cancel_reason = request.POST.get('reason', '')
            logger.debug(f"Razão do cancelamento: {cancel_reason}")
            
            if not cancel_reason:
                logger.warning(f"Tentativa de cancelamento sem justificativa para invoice {invoice_id}")
                messages.error(request, _('A justificativa para cancelamento é obrigatória.'))
                return redirect('payments:professor_transactions')
            
            service = NFEioService()
            try:
                logger.debug(f"Chamando service.cancel_invoice para invoice ID {invoice_id}")
                response = service.cancel_invoice(invoice, cancel_reason)
                logger.info(f"Resposta do cancelamento: {response}")
                
                if response and isinstance(response, dict) and response.get('error'):
                    logger.error(f"Erro no cancelamento: {response.get('message', 'Erro não especificado')}")
                    messages.error(request, _('Erro ao cancelar nota fiscal: {}').format(response.get('message', 'Erro não especificado')))
                else:
                    logger.info(f"Solicitação de cancelamento enviada para invoice ID {invoice_id}")
                    messages.success(request, _('Solicitação de cancelamento enviada. Acompanhe o status na lista de transações.'))
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Exceção ao cancelar nota fiscal: {str(e)}\n{error_traceback}")
                messages.error(request, _('Erro ao cancelar nota fiscal: {}').format(str(e)))
    except Exception as e:
        logger.error(f"Erro ao localizar invoice {invoice_id} para cancelamento: {str(e)}")
        messages.error(request, _('Nota fiscal não encontrada ou não pode ser cancelada.'))
    
    logger.info(f"Concluindo processo de cancelamento para invoice {invoice_id}")
    return redirect('payments:professor_transactions')

@login_required
@professor_required
def delete_invoice(request, invoice_id):
    """
    Deleta uma nota fiscal do banco de dados (apenas para testes).
    Essa função é apenas para ambiente de desenvolvimento e testes.
    """
    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
        transaction__enrollment__course__professor=request.user
    )
    
    transaction = invoice.transaction
    
    if request.method == 'POST':
        # Armazena informações para a mensagem
        transaction_id = transaction.id
        invoice_status = invoice.status
        
        # Deleta a nota fiscal
        invoice.delete()
        
        messages.success(
            request, 
            _(f'Nota fiscal #{invoice_id} (status: {invoice_status}) da transação #{transaction_id} foi excluída. Você pode emitir uma nova nota agora.')
        )
        return redirect('payments:professor_transactions')
    
    return render(request, 'invoices/delete_invoice_confirm.html', {
        'invoice': invoice,
        'transaction': invoice.transaction
    })

# View para modo de teste

@login_required
@professor_required
def test_mode(request):
    """
    Ativa ou desativa o modo de teste para a emissão de notas fiscais.
    """
    if not request.user.is_admin:
        messages.error(request, _('Apenas administradores podem alterar o modo de teste.'))
        return redirect('payments:professor_transactions')
    
    # Alternar o modo de teste
    settings.FOCUS_NFE_TEST_MODE = not settings.FOCUS_NFE_TEST_MODE
    
    if settings.FOCUS_NFE_TEST_MODE:
        messages.success(request, _('Modo de teste ativado. As notas fiscais serão emitidas em ambiente de simulação.'))
    else:
        messages.success(request, _('Modo de teste desativado. As notas fiscais serão emitidas no ambiente real.'))
    
    return redirect('payments:professor_transactions')

@login_required
def invoice_detail(request, invoice_id):
    """
    Exibe os detalhes de uma nota fiscal.
    Acessível tanto para professores quanto para administradores.
    """
    try:
        # Verificar se o usuário é admin ou professor
        is_admin = hasattr(request.user, 'is_admin') and request.user.is_admin
        is_professor = hasattr(request.user, 'is_professor') and request.user.is_professor
        
        if not (is_admin or is_professor):
            logger.warning(f"Usuário {request.user.id} tentou acessar detalhes da nota fiscal {invoice_id} sem permissão")
            messages.error(request, _('Você não tem permissão para acessar esta página.'))
            return redirect('dashboard')
        
        # Filtrar pela nota fiscal
        if is_admin:
            # Administradores podem ver qualquer nota fiscal
            invoice = get_object_or_404(Invoice, id=invoice_id)
            return_url = 'payments:admin_dashboard'
        else:
            # Professores podem ver apenas suas próprias notas fiscais
            invoice = get_object_or_404(
                Invoice,
                id=invoice_id,
                transaction__enrollment__course__professor=request.user
            )
            return_url = 'payments:professor_transactions'
            
        return render(request, 'invoices/invoice_detail.html', {
            'invoice': invoice,
            'return_url': return_url,
            'is_admin': is_admin
        })
    except Exception as e:
        logger.error(f"Erro ao exibir detalhes da nota fiscal {invoice_id}: {str(e)}")
        messages.error(request, _('Erro ao exibir detalhes da nota fiscal.'))
        
        # Redirecionar para a página apropriada com base no tipo de usuário
        if hasattr(request.user, 'is_admin') and request.user.is_admin:
            return redirect('payments:admin_dashboard')
        else:
            return redirect('payments:professor_transactions')

@login_required
@admin_required
def approve_invoice_manually(request, invoice_id):
    """
    Simula a aprovação de uma nota fiscal (apenas para testes).
    IMPORTANTE: Esta função é apenas para testes e não deve ser usada em produção.
    """
    # Verificar se estamos em ambiente de produção
    if not settings.DEBUG:
        messages.error(request, _('Esta funcionalidade só está disponível em ambiente de desenvolvimento.'))
        return redirect('payments:admin_dashboard')
    
    invoice = get_object_or_404(
        Invoice,
        id=invoice_id
    )
    
    logger.info(f"[ADMIN] Forçando aprovação da nota fiscal {invoice_id} para testes.")
    
    if invoice.status in ['approved', 'cancelled']:
        messages.warning(request, _('Esta nota fiscal já está em um estado final (aprovada ou cancelada).'))
        return redirect('invoices:invoice_detail', invoice_id=invoice_id)
    
    # Atualizar o status para aprovado
    previous_status = invoice.status
    invoice.status = 'approved'
    invoice.focus_status = 'Authorized'
    invoice.response_data = {
        'flowStatus': 'Authorized',
        'flowAction': 'ManualApproval',
        'flowMessage': 'Aprovação manual para fins de teste'
    }
    
    # Gerar uma URL fictícia para o PDF se não existir
    if not invoice.focus_pdf_url:
        # Usar um domínio real para o PDF simulado
        invoice.focus_pdf_url = f"https://storage.googleapis.com/cincocincojam-dev/invoices/pdf_simulated/{invoice.id}.pdf"
    
    invoice.save()
    
    messages.success(request, _(f'Nota fiscal #{invoice.id} aprovada manualmente com sucesso. Status alterado de {previous_status} para approved. ATENÇÃO: Esta é apenas uma simulação para testes.'))
    return redirect('invoices:invoice_detail', invoice_id=invoice_id)


@login_required
def transaction_invoice_status(request, transaction_id):
    """
    Verifica se uma transação possui nota fiscal e retorna seu status.
    """
    try:
        transaction = get_object_or_404(PaymentTransaction, id=transaction_id)
        
        # Verificar permissão (apenas o professor que emitiu ou o aluno destinatário)
        if not (request.user == transaction.enrollment.course.professor or 
                request.user == transaction.enrollment.student):
            return JsonResponse({
                'success': False,
                'message': 'Você não tem permissão para verificar esta transação.'
            }, status=403)
        
        # Verificar se a transação possui nota fiscal
        has_invoice = transaction.invoices.exists()
        
        response_data = {
            'success': True,
            'has_invoice': has_invoice
        }
        
        # Se tiver nota fiscal, incluir informações adicionais
        if has_invoice:
            invoice = transaction.invoices.first()
            response_data.update({
                'invoice_id': invoice.id,
                'status': invoice.status,
                'external_id': invoice.external_id,
                'detail_url': reverse('invoices:invoice_detail', kwargs={'invoice_id': invoice.id})
            })
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Erro ao verificar status da nota fiscal para transação {transaction_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        return JsonResponse({
            'success': False,
            'message': f'Erro ao verificar status: {str(e)}'
        }, status=500)

@login_required
def view_pdf(request, invoice_id):
    """
    Redireciona para o PDF da nota fiscal usando o endpoint da API.
    /v1/companies/{company_id}/serviceinvoices/{id}/pdf
    """
    try:
        # Obter a nota fiscal
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Verificar permissão
        if not (request.user == invoice.transaction.enrollment.course.professor or 
                request.user == invoice.transaction.enrollment.student or
                request.user.is_superuser):
            messages.error(request, _('Você não tem permissão para visualizar esta nota fiscal.'))
            return redirect('payments:transactions')
        
        # Verificar se o campo external_id está preenchido
        if not invoice.external_id:
            messages.error(request, _('Não foi possível gerar o PDF. A nota fiscal ainda não possui um ID externo.'))
            return redirect('payments:transactions')
        
        # Obter a configuração da empresa
        company_config = get_object_or_404(CompanyConfig, user=invoice.transaction.enrollment.course.professor)
        
        # Construir a URL para o PDF usando o endpoint da API
        service = NFEioService()
        pdf_url = service.get_pdf_url(company_config.id, invoice.external_id)
        
        # Redirecionar para a URL do PDF
        return HttpResponseRedirect(pdf_url)
        
    except Exception as e:
        logger.error(f"Erro ao obter PDF da nota fiscal {invoice_id}: {str(e)}")
        messages.error(request, _('Erro ao obter o PDF da nota fiscal.'))
        return redirect('payments:transactions')

@login_required
def download_pdf(request, invoice_id):
    """
    Faz download do PDF da nota fiscal diretamente da API NFE.io
    usando as credenciais adequadas e retorna o conteúdo para o usuário.
    """
    try:
        # Verificar se o usuário está autenticado
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login'))
            
        # Obter a nota fiscal pelo external_id
        invoice = get_object_or_404(Invoice, external_id=invoice_id)
        
        # Verificar permissão
        if not (request.user == invoice.transaction.enrollment.course.professor or 
                request.user == invoice.transaction.enrollment.student or
                request.user.is_superuser):
            messages.error(request, _('Você não tem permissão para visualizar esta nota fiscal.'))
            return redirect('payments:transactions')
        
        # Obter a configuração da empresa
        company_config = get_object_or_404(CompanyConfig, user=invoice.transaction.enrollment.course.professor)
        
        # Inicializar o serviço
        service = NFEioService()
        
        # Construir a URL da API
        api_url = f"{service.base_url}/v1/companies/{service.company_id}/serviceinvoices/{invoice_id}/pdf"
        
        # Fazer a requisição autenticada para a API
        import requests
        response = requests.get(api_url, headers=service.headers)
        
        # Verificar se a requisição foi bem-sucedida
        if response.status_code != 200:
            logger.error(f"Erro ao obter PDF da API: {response.status_code} {response.text}")
            messages.error(request, _('Erro ao obter o PDF da nota fiscal. Código de erro: {}').format(response.status_code))
            return redirect('payments:transactions')
        
        # Retornar o conteúdo do PDF com os cabeçalhos adequados
        from django.http import HttpResponse
        pdf_response = HttpResponse(response.content, content_type='application/pdf')
        pdf_response['Content-Disposition'] = f'inline; filename="nota_fiscal_{invoice.id}.pdf"'
        return pdf_response
        
    except Exception as e:
        logger.error(f"Erro ao fazer download do PDF: {str(e)}")
        messages.error(request, _('Erro ao obter o PDF da nota fiscal.'))
        return redirect('payments:transactions')

@login_required
@professor_required
def retry_waiting_invoices(request):
    """
    Busca todas as notas fiscais no estado WaitingSend e tenta enviá-las novamente.
    Esta view pode ser acessada manualmente pelo professor ou administrador.
    """
    try:
        # Inicializar o serviço NFE.io
        service = NFEioService()
        
        # Verificar se o usuário é admin ou professor
        is_admin = hasattr(request.user, 'is_admin') and request.user.is_admin
        
        # Se for professor, buscar apenas suas notas
        if not is_admin:
            # Buscar todas as notas do professor com status 'processing' e focus_status 'WaitingSend'
            waiting_invoices = Invoice.objects.filter(
                transaction__enrollment__course__professor=request.user,
                status='processing', 
                focus_status='WaitingSend', 
                external_id__isnull=False
            )
        else:
            # Se for admin, buscar todas as notas
            waiting_invoices = Invoice.objects.filter(
                status='processing', 
                focus_status='WaitingSend', 
                external_id__isnull=False
            )
        
        if not waiting_invoices.exists():
            messages.info(request, _('Não há notas fiscais aguardando envio.'))
            if is_admin:
                return redirect('payments:admin_dashboard')
            else:
                return redirect('payments:professor_transactions')
        
        # Para cada nota, tentar enviar novamente
        success_count = 0
        error_count = 0
        
        for invoice in waiting_invoices:
            # Tentar enviar a nota
            response = service.send_invoice(invoice)
            
            # Registrar resultado
            if not response.get('error'):
                success_count += 1
            else:
                error_count += 1
            
            # Aguardar um pouco entre as requisições para não sobrecarregar a API
            import time
            time.sleep(1)
        
        # Exibir mensagem de sucesso
        if success_count > 0:
            messages.success(
                request, 
                _('%(success)s nota(s) fiscal(is) reenviada(s) com sucesso. %(error)s nota(s) com erro.') % {
                    'success': success_count,
                    'error': error_count
                }
            )
        else:
            messages.warning(
                request, 
                _('Nenhuma nota fiscal foi reenviada com sucesso. %(error)s nota(s) com erro.') % {'error': error_count}
            )
        
        # Redirecionar para a página apropriada
        if is_admin:
            return redirect('payments:admin_dashboard')
        else:
            return redirect('payments:professor_transactions')
            
    except Exception as e:
        logger.error(f"Erro ao reenviar notas fiscais: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(request, _('Erro ao reenviar notas fiscais: %s') % str(e))
        
        # Redirecionar para a página apropriada
        if hasattr(request.user, 'is_admin') and request.user.is_admin:
            return redirect('payments:admin_dashboard')
        else:
            return redirect('payments:professor_transactions')
