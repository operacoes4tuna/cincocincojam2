from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect, Http404, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseServerError
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.db import transaction as db_transaction
from django.utils.translation import gettext_lazy as _
import logging
import traceback
import json

from payments.models import PaymentTransaction, SingleSale
from users.decorators import professor_required, admin_required

from .models import CompanyConfig, Invoice, MunicipalServiceCode, InvoicePixPayment
from .forms import CompanyConfigForm, MunicipalServiceCodeFormSet
from .services import NFEioService
from .pix_service import InvoicePixService

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
        service_codes_formset = MunicipalServiceCodeFormSet(request.POST, instance=company_config)
        
        if form.is_valid() and service_codes_formset.is_valid():
            with db_transaction.atomic():
                company_config = form.save()
                service_codes_formset.save()
                
                # Atualiza o campo city_service_code se ele estiver vazio
                # ou se não estiver entre os códigos cadastrados
                selected_code = form.cleaned_data.get('city_service_code')
                if selected_code:
                    company_config.city_service_code = selected_code
                    company_config.save()
                
            messages.success(request, _('Configurações fiscais atualizadas com sucesso!'))
            return redirect('invoices:company_settings')
    else:
        form = CompanyConfigForm(instance=company_config)
        service_codes_formset = MunicipalServiceCodeFormSet(instance=company_config)
    
    is_complete = company_config.is_complete() if company_config.pk else False
    
    return render(request, 'invoices/company_settings.html', {
        'form': form,
        'service_codes_formset': service_codes_formset,
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
    
    # Criar a invoice no banco de dados somente após sucesso na emissão
    logger.info(f"Criando nova invoice para transação {transaction_id}")
    with db_transaction.atomic():
        try:
            # Tentar emitir a nota fiscal
            logger.info(f"Iniciando emissão via NFEioService para transação {transaction_id}")
            service = NFEioService()
            try:
                logger.debug(f"Chamando service.emit_invoice para transação {transaction_id}")
                # Criar a invoice antes de chamar o serviço
                invoice = Invoice.objects.create(
                    transaction=transaction,
                    status='pending'
                )
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
                    logger.info(f"Nota fiscal em processamento para transação {transaction_id}")
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
        is_admin = request.user.is_superuser or request.user.is_staff
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
            # Professores podem ver apenas suas próprias notas fiscais (transações e vendas avulsas)
            try:
                # Tentar buscar por transação primeiro
                invoice = Invoice.objects.get(
                    id=invoice_id,
                    transaction__enrollment__course__professor=request.user
                )
            except Invoice.DoesNotExist:
                # Se não encontrou por transação, tentar por venda avulsa
                try:
                    invoice = Invoice.objects.get(
                        id=invoice_id,
                        singlesale__seller=request.user
                    )
                except Invoice.DoesNotExist:
                    # Se não encontrou nem por transação nem por venda avulsa, usar 404
                    from django.http import Http404
                    raise Http404("Invoice não encontrada para este professor")
            return_url = 'payments:professor_transactions'
            
        return render(request, 'invoices/invoice_detail.html', {
            'invoice': invoice,
            'return_url': return_url,
            'is_admin': is_admin,
            'debug': settings.DEBUG,
        })
    except Exception as e:
        logger.error(f"Erro ao exibir detalhes da nota fiscal {invoice_id}: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(request, _('Erro ao exibir detalhes da nota fiscal.'))
        
        # Redirecionar para a página apropriada com base no tipo de usuário
        if request.user.is_superuser or request.user.is_staff:
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
        if invoice.transaction:
            # Para transações de cursos
            if not (request.user == invoice.transaction.enrollment.course.professor or 
                    request.user == invoice.transaction.enrollment.student or
                    request.user.is_superuser):
                messages.error(request, _('Você não tem permissão para visualizar esta nota fiscal.'))
                return redirect('payments:transactions')
            # Professor da transação
            professor = invoice.transaction.enrollment.course.professor
        elif invoice.singlesale:
            # Para vendas avulsas
            if not (request.user == invoice.singlesale.seller or
                    request.user.is_superuser):
                messages.error(request, _('Você não tem permissão para visualizar esta nota fiscal.'))
                return redirect('payments:singlesale_list')
            # Vendedor da venda avulsa
            professor = invoice.singlesale.seller
        else:
            messages.error(request, _('Nota fiscal inválida.'))
            return redirect('dashboard')
        
        # Verificar se o campo external_id está preenchido
        if not invoice.external_id:
            messages.error(request, _('Não foi possível gerar o PDF. A nota fiscal ainda não possui um ID externo.'))
            if invoice.transaction:
                return redirect('payments:transactions')
            else:
                return redirect('payments:singlesale_list')
        
        # Se tiver a URL do PDF diretamente, usar ela
        if invoice.focus_pdf_url:
            return HttpResponseRedirect(invoice.focus_pdf_url)
            
        # Obter a configuração da empresa
        company_config = get_object_or_404(CompanyConfig, user=professor)
        
        # Construir a URL para o PDF usando o endpoint da API
        service = NFEioService()
        pdf_url = service.get_pdf_url(company_config.id, invoice.external_id)
        
        # Redirecionar para a URL do PDF
        return HttpResponseRedirect(pdf_url)
        
    except Exception as e:
        logger.error(f"Erro ao obter PDF da nota fiscal {invoice_id}: {str(e)}")
        messages.error(request, _('Erro ao obter o PDF da nota fiscal.'))
        return redirect('dashboard')

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
        if invoice.transaction:
            # Para transações de cursos
            if not (request.user == invoice.transaction.enrollment.course.professor or 
                    request.user == invoice.transaction.enrollment.student or
                    request.user.is_superuser):
                messages.error(request, _('Você não tem permissão para visualizar esta nota fiscal.'))
                return redirect('payments:transactions')
            # Professor da transação
            professor = invoice.transaction.enrollment.course.professor
        elif invoice.singlesale:
            # Para vendas avulsas
            if not (request.user == invoice.singlesale.seller or
                    request.user.is_superuser):
                messages.error(request, _('Você não tem permissão para visualizar esta nota fiscal.'))
                return redirect('payments:singlesale_list')
            # Vendedor da venda avulsa
            professor = invoice.singlesale.seller
        else:
            messages.error(request, _('Nota fiscal inválida.'))
            return redirect('dashboard')
        
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
            return redirect('dashboard')
        
        # Retornar o conteúdo do PDF com os cabeçalhos adequados
        from django.http import HttpResponse
        pdf_response = HttpResponse(response.content, content_type='application/pdf')
        pdf_response['Content-Disposition'] = f'inline; filename="nota_fiscal_{invoice.id}.pdf"'
        return pdf_response
        
    except Exception as e:
        logger.error(f"Erro ao fazer download do PDF: {str(e)}")
        messages.error(request, _('Erro ao obter o PDF da nota fiscal.'))
        return redirect('dashboard')

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

@login_required
@professor_required
def sync_invoice_status(request, invoice_id):
    """
    Sincroniza o status da nota fiscal com a API NFE.io.
    Funciona tanto para notas fiscais de transações quanto de vendas avulsas.
    """
    try:
        # Tentar obter a invoice de duas formas: transação ou venda avulsa
        try:
            # Primeiro tenta encontrar via transação
            invoice = get_object_or_404(
                Invoice, 
                id=invoice_id, 
                transaction__enrollment__course__professor=request.user
            )
        except (Invoice.DoesNotExist, Http404):
            # Se não encontrou, tenta via venda avulsa
            invoice = get_object_or_404(
                Invoice, 
                id=invoice_id, 
                singlesale__seller=request.user
            )
        
        # Inicializar o serviço NFE.io
        service = NFEioService()
        
        # Verificar o status atual na API
        status_result = service.check_invoice_status(invoice)
        
        if status_result['success']:
            return JsonResponse({'success': True, 'message': _('Status da nota fiscal sincronizado com sucesso.')})
        else:
            return JsonResponse({'success': False, 'message': _('Erro ao sincronizar status da nota fiscal: {}').format(status_result['message'])})
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar status da nota fiscal {invoice_id}: {str(e)}")
        return JsonResponse({'success': False, 'message': _('Erro ao sincronizar status da nota fiscal.')})

@login_required
@professor_required
def emit_singlesale_invoice(request, sale_id):
    """
    Emite uma nota fiscal para uma venda avulsa.
    """
    try:
        sale = get_object_or_404(
            SingleSale,
            id=sale_id,
            seller=request.user
        )
        logger.debug(f"Venda avulsa encontrada: {sale_id}, valor: {sale.amount}, status: {sale.status}")
    except Exception as e:
        logger.error(f"Erro ao obter venda avulsa {sale_id}: {str(e)}")
        messages.error(request, _('Erro ao localizar venda avulsa.'))
        return redirect('payments:singlesale_list')
    
    # Verificar se já existe uma nota fiscal para esta venda
    existing_invoice = Invoice.objects.filter(singlesale=sale).first()
    if existing_invoice:
        logger.info(f"Já existe nota fiscal para venda avulsa {sale_id}: Invoice ID {existing_invoice.id}, status: {existing_invoice.status}")
        messages.info(request, _('Já existe uma nota fiscal para esta venda.'))
        return redirect('payments:singlesale_list')
    
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
    logger.info(f"Criando nova invoice para venda avulsa {sale_id}")
    
    try:
        # Criar a invoice
        invoice = Invoice.objects.create(
            singlesale=sale,
            amount=sale.amount,
            customer_name=sale.customer_name,
            customer_email=sale.customer_email,
            customer_tax_id=sale.customer_cpf,
            description=sale.description,
            type=sale.invoice_type or 'rps',
            status='pending'
        )
        
        # Iniciar o processo de emissão da nota fiscal
        try:
            # Inicializar o serviço NFE.io
            service = NFEioService()
            
            # Gerar número RPS
            service._generate_rps_for_invoice(invoice, request.user)
            
            # Emitir a nota fiscal
            result = service.emit_invoice(invoice)
                
            logger.info(f"Resultado da emissão: {result}")
            
            if not result.get('error', False):
                # Atualizar o status da invoice
                invoice.status = 'processing'
                invoice.emitted_at = timezone.now()
                invoice.save()
                
                messages.success(request, _('Nota fiscal enviada para processamento. Acompanhe o status na lista de notas fiscais.'))
            else:
                # Em caso de erro, atualizar o status da invoice
                invoice.status = 'error'
                invoice.error_message = result.get('message', _('Erro desconhecido ao enviar para emissão.'))
                invoice.save()
                
                messages.error(request, _('Erro ao emitir nota fiscal: {}').format(invoice.error_message))
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Exceção ao processar emissão: {str(e)}\n{error_traceback}")
            
            invoice.status = 'error'
            invoice.error_message = str(e)
            invoice.save()
            
            messages.error(request, _('Erro ao processar nota fiscal: {}').format(str(e)))
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Exceção ao criar invoice: {str(e)}\n{error_traceback}")
        messages.error(request, _('Erro ao criar nota fiscal: {}').format(str(e)))
    
    logger.info(f"Concluindo processo de emissão para venda avulsa {sale_id}")
    return redirect('payments:singlesale_list')

@login_required
def invoice_detail_json(request, invoice_id):
    """
    Retorna os detalhes de uma nota fiscal em formato JSON.
    Acessível tanto para professores quanto para administradores.
    """
    try:
        # Verificar se o usuário é admin ou professor
        is_admin = hasattr(request.user, 'is_admin') and request.user.is_admin
        is_professor = hasattr(request.user, 'is_professor') and request.user.is_professor
        
        if not (is_admin or is_professor):
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        
        # Filtrar pela nota fiscal
        if is_admin:
            # Administradores podem ver qualquer nota fiscal
            invoice = get_object_or_404(Invoice, id=invoice_id)
        else:
            # Professores podem ver apenas suas próprias notas fiscais
            try:
                # Tentar obter via transação
                invoice = get_object_or_404(
                    Invoice,
                    id=invoice_id,
                    transaction__enrollment__course__professor=request.user
                )
            except (Invoice.DoesNotExist, Http404):
                # Se não encontrou, tentar via venda avulsa
                invoice = get_object_or_404(
                    Invoice,
                    id=invoice_id,
                    singlesale__seller=request.user
                )
        
        # Retornar dados básicos da nota fiscal
        data = {
            'id': invoice.id,
            'status': invoice.status,
            'external_id': invoice.external_id,
            'focus_status': invoice.focus_status,
            'focus_pdf_url': invoice.focus_pdf_url,
            'focus_xml_url': invoice.focus_xml_url,
            'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
            'emitted_at': invoice.emitted_at.isoformat() if invoice.emitted_at else None,
            'customer_name': invoice.customer_name,
            'amount': str(invoice.amount) if invoice.amount else None,
            'description': invoice.description,
            'error_message': invoice.error_message
        }
        
        # Verificar o status novamente na API se necessário
        if 'refresh' in request.GET and request.GET['refresh'] == 'true':
            try:
                service = NFEioService()
                status_result = service.check_invoice_status(invoice)
                data['refresh_status'] = status_result
                
                # Atualizar os dados com os valores mais recentes
                data['status'] = invoice.status
                data['focus_status'] = invoice.focus_status
                data['focus_pdf_url'] = invoice.focus_pdf_url
                data['focus_xml_url'] = invoice.focus_xml_url
                data['error_message'] = invoice.error_message
            except Exception as e:
                data['refresh_error'] = str(e)
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Erro ao retornar detalhes da nota fiscal em JSON: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def send_invoice_email(request, invoice_id):
    """
    Página para envio de nota fiscal por email via SendGrid
    """
    try:
        # Verificar se o usuário tem permissão para acessar esta nota fiscal
        is_admin = hasattr(request.user, 'is_admin') and request.user.is_admin
        is_professor = hasattr(request.user, 'is_professor') and request.user.is_professor
        
        if not (is_admin or is_professor):
            messages.error(request, _('Acesso negado.'))
            return redirect('dashboard')
        
        # Buscar a nota fiscal
        if is_admin:
            invoice = get_object_or_404(Invoice, id=invoice_id)
        else:
            # Professores podem acessar apenas suas próprias notas fiscais
            try:
                # Tentar obter via transação
                invoice = get_object_or_404(
                    Invoice,
                    id=invoice_id,
                    transaction__enrollment__course__professor=request.user
                )
            except (Invoice.DoesNotExist, Http404):
                # Se não encontrou, tentar via venda avulsa
                invoice = get_object_or_404(
                    Invoice,
                    id=invoice_id,
                    singlesale__seller=request.user
                )
        
        # Avisos informativos (mas não impedem o envio)
        info_messages = []
        
        if invoice.status != 'approved':
            info_messages.append('Nota: Esta nota fiscal ainda não foi aprovada, mas o email será enviado mesmo assim.')
        
        # ✅ REMOVIDO: Não verificar PDF aqui - deixar o sistema de email decidir
        # O sistema de anexo melhorado tentará baixar o PDF automaticamente
        
        # Mostrar mensagens informativas
        if info_messages:
            for msg in info_messages:
                messages.info(request, msg)
        
        if request.method == 'POST':
            from .forms import SendEmailForm
            form = SendEmailForm(request.POST)
            
            if form.is_valid():
                recipient_email = form.cleaned_data['recipient_email']
                custom_message = form.cleaned_data.get('custom_message', '')
                
                # Enviar o email usando o serviço
                from .email_service import EmailService
                email_service = EmailService()
                result = email_service.send_invoice_email(invoice, recipient_email, custom_message)
                
                if result['success']:
                    messages.success(request, result['message'])
                    # Permanecer na página para permitir novos envios
                    return redirect('invoices:send_email', invoice_id=invoice_id)
                else:
                    messages.error(request, result['message'])
        else:
            from .forms import SendEmailForm
            # Pré-preencher com email do cliente se disponível
            initial_data = {}
            if invoice.customer_email:
                initial_data['recipient_email'] = invoice.customer_email
            
            form = SendEmailForm(initial=initial_data)
        
        # Obter dados da nota fiscal para exibição
        invoice_data = {
            'numero': invoice.external_id or invoice.id,
            'valor': invoice.amount or (invoice.transaction.amount if invoice.transaction else (invoice.singlesale.amount if invoice.singlesale else 0)),
            'cliente': invoice.customer_name or (invoice.transaction.enrollment.student.get_full_name() if invoice.transaction else (invoice.singlesale.customer_name if invoice.singlesale else 'Cliente'))
        }
        
        return render(request, 'invoices/send_email.html', {
            'invoice': invoice,
            'invoice_data': invoice_data,
            'form': form,
        })
        
    except Exception as e:
        logger.error(f"Erro ao exibir página de envio de email para nota fiscal {invoice_id}: {str(e)}")
        messages.error(request, _('Erro ao carregar página de envio de email.'))
        # Tentar ir para dashboard em vez de transações
        return redirect('dashboard')

@login_required
def send_invoice_email_ajax(request, invoice_id):
    """
    Endpoint AJAX para envio rápido de email da nota fiscal
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    try:
        # Verificar permissões
        is_admin = hasattr(request.user, 'is_admin') and request.user.is_admin
        is_professor = hasattr(request.user, 'is_professor') and request.user.is_professor
        
        if not (is_admin or is_professor):
            return JsonResponse({'success': False, 'message': 'Acesso negado'}, status=403)
        
        # Buscar a nota fiscal
        if is_admin:
            invoice = get_object_or_404(Invoice, id=invoice_id)
        else:
            try:
                invoice = get_object_or_404(
                    Invoice,
                    id=invoice_id,
                    transaction__enrollment__course__professor=request.user
                )
            except (Invoice.DoesNotExist, Http404):
                invoice = get_object_or_404(
                    Invoice,
                    id=invoice_id,
                    singlesale__seller=request.user
                )
        
        # Verificações básicas
        if invoice.status != 'approved':
            return JsonResponse({
                'success': False, 
                'message': 'Apenas notas fiscais aprovadas podem ser enviadas por email.'
            })
        
        # ✅ REMOVIDO: Não verificar PDF aqui - deixar o sistema de email decidir
        # O sistema de anexo melhorado tentará baixar o PDF automaticamente
        
        # Obter email do cliente
        recipient_email = None
        if invoice.customer_email:
            recipient_email = invoice.customer_email
        elif invoice.transaction and invoice.transaction.enrollment.student.email:
            recipient_email = invoice.transaction.enrollment.student.email
        elif invoice.singlesale and invoice.singlesale.customer_email:
            recipient_email = invoice.singlesale.customer_email
        
        if not recipient_email:
            return JsonResponse({
                'success': False, 
                'message': 'Email do cliente não disponível. Use a página de envio personalizado.'
            })
        
        # Enviar o email
        from .email_service import EmailService
        email_service = EmailService()
        result = email_service.send_invoice_email(invoice, recipient_email)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Erro ao enviar email via AJAX para nota fiscal {invoice_id}: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': f'Erro ao enviar email: {str(e)}'
        })

@login_required
def test_pdf_attachment_view(request, invoice_id):
    """
    View para testar o anexo de PDF de uma nota fiscal específica.
    Útil para debug via navegador.
    """
    if not settings.DEBUG:
        messages.error(request, _('Esta funcionalidade só está disponível em ambiente de desenvolvimento.'))
        return redirect('dashboard')
    
    try:
        # Verificar se o usuário tem permissão
        is_admin = hasattr(request.user, 'is_admin') and request.user.is_admin
        is_professor = hasattr(request.user, 'is_professor') and request.user.is_professor
        
        if not (is_admin or is_professor):
            messages.error(request, _('Acesso negado.'))
            return redirect('dashboard')
        
        # Buscar a nota fiscal
        if is_admin:
            invoice = get_object_or_404(Invoice, id=invoice_id)
        else:
            # Professores podem acessar apenas suas próprias notas fiscais
            try:
                invoice = get_object_or_404(
                    Invoice,
                    id=invoice_id,
                    transaction__enrollment__course__professor=request.user
                )
            except (Invoice.DoesNotExist, Http404):
                invoice = get_object_or_404(
                    Invoice,
                    id=invoice_id,
                    singlesale__seller=request.user
                )
        
        from .email_service import EmailService
        email_service = EmailService()
        
        # Executar teste de debug
        success = email_service.debug_pdf_attachment(invoice)
        
        if success:
            messages.success(request, f'✅ PDF da nota fiscal #{invoice.id} pode ser anexado com sucesso!')
        else:
            messages.error(request, f'❌ Falha ao anexar PDF da nota fiscal #{invoice.id}. Verifique os logs.')
        
        # Informações adicionais para o usuário
        info_messages = []
        
        if not invoice.focus_pdf_url:
            info_messages.append('📎 Esta nota fiscal não possui URL de PDF.')
        
        if invoice.status != 'approved':
            info_messages.append(f'📋 Status da nota fiscal: {invoice.get_status_display()}')
        
        if not email_service.nfeio_api_key:
            info_messages.append('🔑 Credenciais NFE.io não configuradas.')
            
        for msg in info_messages:
            messages.info(request, msg)
        
        return redirect('invoices:invoice_detail', invoice_id=invoice_id)
        
    except Exception as e:
        logger.error(f"Erro ao testar anexo PDF da nota fiscal {invoice_id}: {str(e)}")
        messages.error(request, f'Erro ao testar anexo: {str(e)}')
        return redirect('dashboard')

@login_required
def create_invoice_pix_payment(request, invoice_id):
    """
    Cria um pagamento Pix para uma nota fiscal aprovada.
    """
    try:
        # Buscar invoice com permissões simplificadas
        if request.user.is_superuser or request.user.is_staff:
            # Admin pode acessar qualquer invoice
            invoice = get_object_or_404(Invoice, id=invoice_id)
        elif hasattr(request.user, 'is_professor') and request.user.is_professor:
            # Professor só pode acessar suas próprias invoices (transações e vendas avulsas)
            try:
                # Tentar buscar por transação primeiro
                invoice = Invoice.objects.get(
                    id=invoice_id,
                    transaction__enrollment__course__professor=request.user
                )
            except Invoice.DoesNotExist:
                # Se não encontrou por transação, tentar por venda avulsa
                try:
                    invoice = Invoice.objects.get(
                        id=invoice_id,
                        singlesale__seller=request.user
                    )
                except Invoice.DoesNotExist:
                    # Se não encontrou nem por transação nem por venda avulsa, usar 404
                    from django.http import Http404
                    raise Http404("Invoice não encontrada")
        else:
            # Outros usuários (alunos, etc.) - buscar e verificar depois
            invoice = get_object_or_404(Invoice, id=invoice_id)
            
            # Verificar se tem permissão
            has_permission = False
            if invoice.transaction and invoice.transaction.enrollment.student == request.user:
                has_permission = True
            elif invoice.singlesale and invoice.customer_email == request.user.email:
                has_permission = True
            
            if not has_permission:
                messages.error(request, _('Você não tem permissão para gerar Pix para esta nota fiscal.'))
                return redirect('dashboard')
        
        # Verificar se a nota fiscal está aprovada
        if invoice.status not in ['approved', 'issued']:
            messages.error(request, _('Só é possível gerar pagamento Pix para notas fiscais aprovadas.'))
            return redirect('invoices:invoice_detail', invoice_id=invoice.id)
        
        # Criar o pagamento Pix
        try:
            pix_service = InvoicePixService()
            result = pix_service.create_pix_payment_for_invoice(invoice)
            
            if result['success']:
                if result.get('existing'):
                    messages.info(request, _('Já existe um pagamento Pix ativo para esta nota fiscal.'))
                else:
                    messages.success(request, _('Pagamento Pix gerado com sucesso!'))
                    if result.get('warning'):
                        messages.warning(request, _(result['warning']))
                
                return redirect('invoices:invoice_pix_detail', invoice_id=invoice.id)
            else:
                error_msg = result.get('error', 'Erro desconhecido')
                logger.error(f"Erro no serviço Pix para invoice {invoice_id}: {error_msg}")
                messages.error(request, _('Erro ao gerar pagamento Pix: {}').format(error_msg))
                return redirect('invoices:invoice_detail', invoice_id=invoice.id)
                
        except Exception as service_error:
            logger.error(f"Exceção no serviço Pix para invoice {invoice_id}: {str(service_error)}")
            logger.error(traceback.format_exc())
            messages.error(request, _('Erro no serviço de pagamento Pix. Tente novamente.'))
            return redirect('invoices:invoice_detail', invoice_id=invoice.id)
            
    except Exception as e:
        logger.error(f"Erro geral ao criar pagamento Pix para invoice {invoice_id}: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(request, _('Erro interno ao gerar pagamento Pix.'))
        return redirect('invoices:invoice_detail', invoice_id=invoice_id)


@login_required
def invoice_pix_detail(request, invoice_id):
    """
    Exibe os detalhes do pagamento Pix de uma nota fiscal.
    """
    logger.info(f"Acessando invoice_pix_detail para invoice {invoice_id} pelo usuário {request.user.username}")
    try:
        # Verificar permissões e buscar invoice
        invoice = None
        
        # Verificar se é admin primeiro
        if request.user.is_superuser or request.user.is_staff:
            # Admin pode acessar qualquer invoice
            invoice = get_object_or_404(Invoice, id=invoice_id)
        elif hasattr(request.user, 'is_professor') and request.user.is_professor:
            # Professor só pode acessar suas próprias invoices (transações e vendas avulsas)
            try:
                # Tentar buscar por transação primeiro
                invoice = Invoice.objects.get(
                    id=invoice_id,
                    transaction__enrollment__course__professor=request.user
                )
            except Invoice.DoesNotExist:
                # Se não encontrou por transação, tentar por venda avulsa
                try:
                    invoice = Invoice.objects.get(
                        id=invoice_id,
                        singlesale__seller=request.user
                    )
                except Invoice.DoesNotExist:
                    # Se não encontrou nem por transação nem por venda avulsa, usar 404
                    from django.http import Http404
                    raise Http404("Invoice não encontrada para este professor")
        else:
            # Outros usuários - tentar buscar a invoice e verificar permissões depois
            invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Verificar se existe pagamento Pix
        logger.info(f"Verificando pagamento Pix para invoice {invoice_id}")
        try:
            pix_payment = invoice.pix_payment
            logger.info(f"Pagamento Pix encontrado: ID {pix_payment.id}, Status: {pix_payment.status}")
        except InvoicePixPayment.DoesNotExist:
            logger.warning(f"Pagamento Pix não encontrado para invoice {invoice_id}")
            messages.error(request, _('Não foi encontrado pagamento Pix para esta nota fiscal.'))
            return redirect('invoices:invoice_detail', invoice_id=invoice.id)
        except Exception as e:
            logger.error(f"Erro ao acessar pix_payment da invoice {invoice_id}: {str(e)}")
            logger.error(traceback.format_exc())
            messages.error(request, _('Erro ao acessar dados do pagamento Pix.'))
            return redirect('invoices:invoice_detail', invoice_id=invoice.id)
        
        # Determinar tipo de usuário e permissões
        is_professor = hasattr(request.user, 'is_professor') and request.user.is_professor
        is_admin = request.user.is_superuser or request.user.is_staff
        is_customer = False
        
        # Verificar se é cliente
        if invoice.transaction and invoice.transaction.enrollment.student == request.user:
            is_customer = True
        elif invoice.singlesale and invoice.customer_email == request.user.email:
            is_customer = True
        
        # Verificar permissões específicas para não-admins
        if not is_admin:
            if is_professor:
                # Professor deve ser dono da invoice
                if invoice.transaction and invoice.transaction.enrollment.course.professor != request.user:
                    messages.error(request, _('Você não tem permissão para acessar este pagamento.'))
                    return redirect('dashboard')
            elif not is_customer:
                # Se não é admin, não é professor e não é cliente, não pode acessar
                messages.error(request, _('Você não tem permissão para acessar este pagamento.'))
                return redirect('dashboard')
        
        context = {
            'invoice': invoice,
            'pix_payment': pix_payment,
            'is_customer': is_customer,
            'is_professor': is_professor,
            'qr_code_image_data': pix_payment.qrcode_image_data,
            'qr_code_image_url': pix_payment.qrcode_image_url,
            'debug': settings.DEBUG,
        }
        
        logger.info(f"Renderizando template para invoice {invoice_id}")
        logger.info(f"Context: QR Data={bool(pix_payment.qrcode_image_data)}, QR URL={bool(pix_payment.qrcode_image_url)}")
        
        return render(request, 'invoices/invoice_pix_detail.html', context)
        
    except Exception as e:
        logger.error(f"Erro ao exibir pagamento Pix da invoice {invoice_id}: {str(e)}")
        messages.error(request, _('Erro ao carregar detalhes do pagamento Pix.'))
        return redirect('invoices:invoice_detail', invoice_id=invoice_id)


@login_required
def check_invoice_pix_status(request, invoice_id):
    """
    Verifica o status do pagamento Pix de uma nota fiscal (AJAX).
    """
    try:
        # Verificar se a invoice existe e se o usuário tem acesso
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Verificar permissões
        can_access = False
        if hasattr(request.user, 'is_professor') and request.user.is_professor:
            # Professor
            can_access = invoice.transaction and invoice.transaction.enrollment.course.professor == request.user
        elif request.user.is_superuser or request.user.is_staff:
            # Admin
            can_access = True
        elif invoice.transaction and invoice.transaction.enrollment.student == request.user:
            # Cliente da transação
            can_access = True
        elif invoice.singlesale and invoice.customer_email == request.user.email:
            # Cliente da venda avulsa
            can_access = True
        
        if not can_access:
            return JsonResponse({
                'success': False,
                'error': 'Permissão negada'
            }, status=403)
        
        # Verificar se existe pagamento Pix
        try:
            pix_payment = invoice.pix_payment
        except InvoicePixPayment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pagamento Pix não encontrado'
            }, status=404)
        
        # Verificar status
        pix_service = InvoicePixService()
        result = pix_service.check_payment_status(pix_payment)
        
        # Adicionar informações extras se o pagamento foi confirmado
        if result.get('status') == 'PAID':
            result['paid_at_formatted'] = pix_payment.paid_at.strftime('%d/%m/%Y %H:%M') if pix_payment.paid_at else ''
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Erro ao verificar status do pagamento Pix da invoice {invoice_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Erro interno'
        }, status=500)


@login_required
def simulate_invoice_pix_payment(request, invoice_id):
    """
    Simula o pagamento de um Pix (apenas para desenvolvimento).
    """
    if not settings.DEBUG:
        return JsonResponse({
            'success': False,
            'error': 'Função disponível apenas em modo DEBUG'
        }, status=403)
    
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Verificar se existe pagamento Pix
        try:
            pix_payment = invoice.pix_payment
        except InvoicePixPayment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pagamento Pix não encontrado'
            }, status=404)
        
        # Simular pagamento
        pix_service = InvoicePixService()
        if pix_service.simulate_payment_confirmation(pix_payment):
            messages.success(request, _('Pagamento simulado como confirmado!'))
            return JsonResponse({
                'success': True,
                'message': 'Pagamento simulado como confirmado',
                'status': 'PAID'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Não foi possível simular o pagamento'
            })
            
    except Exception as e:
        logger.error(f"Erro ao simular pagamento da invoice {invoice_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Erro interno'
        }, status=500)

@login_required
def serve_pdf_for_whatsapp(request, invoice_id):
    """
    Serve o PDF da nota fiscal diretamente para download/compartilhamento
    especialmente para uso com WhatsApp Web API
    """
    try:
        # Obter a nota fiscal
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Verificar permissão
        if invoice.transaction:
            # Para transações de cursos
            if not (request.user == invoice.transaction.enrollment.course.professor or 
                    request.user == invoice.transaction.enrollment.student or
                    request.user.is_superuser):
                messages.error(request, _('Você não tem permissão para acessar esta nota fiscal.'))
                return HttpResponseForbidden('Acesso negado')
            professor = invoice.transaction.enrollment.course.professor
        elif invoice.singlesale:
            # Para vendas avulsas
            if not (request.user == invoice.singlesale.seller or
                    request.user.is_superuser):
                messages.error(request, _('Você não tem permissão para acessar esta nota fiscal.'))
                return HttpResponseForbidden('Acesso negado')
            professor = invoice.singlesale.seller
        else:
            return HttpResponseForbidden('Nota fiscal inválida')
        
        # Verificar se o PDF está disponível
        if not invoice.focus_pdf_url:
            return HttpResponseBadRequest('PDF não disponível')
        
        # Obter o serviço NFE.io
        service = NFEioService()
        
        # Se a URL do PDF é externa (da NFE.io), fazer proxy da requisição
        if invoice.focus_pdf_url.startswith('http'):
            import requests
            response = requests.get(invoice.focus_pdf_url, headers=service.headers, timeout=30)
            
            if response.status_code == 200:
                # Retornar o PDF com headers adequados para download
                pdf_response = HttpResponse(response.content, content_type='application/pdf')
                pdf_response['Content-Disposition'] = f'attachment; filename="nota_fiscal_{invoice.id}.pdf"'
                pdf_response['Access-Control-Allow-Origin'] = '*'  # Para permitir CORS
                pdf_response['Access-Control-Allow-Methods'] = 'GET'
                pdf_response['Access-Control-Allow-Headers'] = 'Content-Type'
                return pdf_response
            else:
                logger.error(f"Erro ao obter PDF: {response.status_code}")
                return HttpResponseServerError('Erro ao obter PDF')
        else:
            # Se for URL local, redirecionar
            return HttpResponseRedirect(invoice.focus_pdf_url)
            
    except Exception as e:
        logger.error(f"Erro ao servir PDF para WhatsApp: {str(e)}")
        return HttpResponseServerError('Erro interno do servidor')
