from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
import logging

from .models import ChatSession, Message, AssistantBehavior
from .openai_manager import OpenAIManager

# Inicializa o logger
logger = logging.getLogger(__name__)

# Inicializa o gerenciador de OpenAI
openai_manager = OpenAIManager()

def index(request):
    """View para renderizar a página principal do assistente"""
    return render(request, 'assistant/index.html')

@csrf_exempt
def create_session(request):
    """API para criar uma nova sessão de chat"""
    if request.method == 'POST':
        try:
            logger.info("Criando nova sessão de chat")
            session_id = str(uuid.uuid4())
            user = request.user if request.user.is_authenticated else None
            
            if user:
                logger.info(f"Sessão sendo criada para usuário autenticado: {user.username}")
            else:
                logger.info("Sessão sendo criada para usuário anônimo")
            
            session = ChatSession.objects.create(
                session_id=session_id,
                user=user
            )
            
            logger.info(f"Sessão criada com sucesso. ID: {session_id}")
            
            return JsonResponse({
                'success': True,
                'session_id': session_id
            })
        except Exception as e:
            logger.error(f"Erro ao criar sessão: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Erro ao criar sessão: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)

@csrf_exempt
def send_message(request):
    """API para enviar uma mensagem para o assistente"""
    if request.method == 'POST':
        try:
            # Verifica o formato da requisição e obtém os dados
            if request.content_type and 'application/json' in request.content_type:
                data = json.loads(request.body)
                logger.info("Requisição recebida em formato JSON")
            else:
                # Obtém dados do formulário
                data = request.POST
                logger.info("Requisição recebida em formato de formulário")
            
            session_id = data.get('session_id')
            message_content = data.get('message')
            
            logger.info(f"Requisição para enviar mensagem. Session ID: {session_id}")
            
            if not session_id or not message_content:
                logger.warning(f"Parâmetros inválidos. Session ID: {session_id}, Message: {'presente' if message_content else 'ausente'}")
                return JsonResponse({
                    'success': False,
                    'message': 'Parâmetros inválidos'
                }, status=400)
            
            try:
                chat_session = ChatSession.objects.get(session_id=session_id, is_active=True)
                logger.info(f"Sessão encontrada: {chat_session.id}")
            except ChatSession.DoesNotExist:
                logger.warning(f"Sessão não encontrada: {session_id}")
                return JsonResponse({
                    'success': False,
                    'message': 'Sessão não encontrada'
                }, status=404)
            
            # Cria a mensagem do usuário
            user_message = Message.objects.create(
                chat_session=chat_session,
                sender='user',
                content=message_content
            )
            logger.info(f"Mensagem do usuário criada: {user_message.id}")
            
            # Busca o histórico de mensagens da sessão
            message_history = Message.objects.filter(chat_session=chat_session).order_by('timestamp')
            logger.info(f"Histórico de mensagens recuperado. Total: {message_history.count()}")
            
            # Formata o histórico para a API da OpenAI
            formatted_messages = openai_manager.format_chat_history(list(message_history))
            
            # Adiciona contexto sobre o usuário autenticado
            system_message = formatted_messages[0]
            user_context = ""
            if request.user.is_authenticated:
                user_context = f"""
                O usuário atual está autenticado com o email {request.user.email} e username {request.user.username}.
                Tipo de usuário: {request.user.user_type}.
                
                Ao responder perguntas sobre cursos matriculados ou informações pessoais, você pode usar este email
                para consultar o banco de dados diretamente.
                """
                
                system_message["content"] += user_context
                logger.info(f"Contexto do usuário adicionado para: {request.user.username}")
            
            # ACESSO DIRETO AO BANCO DE DADOS
            # Palavras-chave que indicam consultas a dados financeiros ou do sistema
            finance_keywords = ['faturamento', 'receita', 'pagamento', 'pagamentos', 'financeiro', 
                              'financeira', 'pagar', 'transacao', 'transacoes', 'transação', 
                              'transações', 'dinheiro', 'venda', 'vendas', 'estatística']
                              
            client_keywords = ['melhor cliente', 'maior cliente', 'cliente que mais', 'top cliente',
                             'cliente principal', 'quem compra mais', 'maior comprador']
                             
            invoice_keywords = ['nota fiscal', 'notas fiscais', 'nfe', 'nfse', 'invoice', 'rps',
                             'emissão de nota', 'emitir nota']
            
            lower_message = message_content.lower()
            is_finance_query = any(keyword in lower_message for keyword in finance_keywords)
            is_client_query = any(keyword in lower_message for keyword in client_keywords)
            is_invoice_query = any(keyword in lower_message for keyword in invoice_keywords)
            
            # Se for qualquer tipo de consulta financeira ou sobre o melhor cliente, responde diretamente
            if is_finance_query or is_client_query or is_invoice_query:
                from .db_manager import DatabaseManager
                from .direct_query import format_financial_data, get_best_client_info
                db_manager = DatabaseManager()
                
                # Se for consulta sobre notas fiscais
                if is_invoice_query:
                    logger.info("Consulta sobre notas fiscais detectada")
                    # Usar nossa função db_query
                    from .db_query import get_invoice_data
                    bot_response = get_invoice_data()
                    
                # Se for consulta sobre o melhor cliente
                elif is_client_query:
                    logger.info("Consulta sobre melhores clientes detectada")
                    # Usar nossa nova função otimizada que acessa diretamente o banco
                    bot_response = get_best_client_info()
                    
                # Se for consulta sobre dados financeiros
                elif is_finance_query:
                    logger.info("Consulta sobre dados financeiros detectada")
                    # Usar nossa nova função que formata todos os dados financeiros
                    bot_response = format_financial_data()
                    
                # Situação não coberta pelos casos específicos acima
                # Usar a função do banco de dados default
                else:
                    logger.info("Consulta de banco de dados genérica detectada")
                    # Busca informações sobre pagamentos pendentes
                    pending_data = db_manager.get_pending_payments()
                    # Formata a resposta
                    if pending_data and 'total_count' in pending_data:
                        count = pending_data.get('total_count', 0)
                        total = pending_data.get('total_amount', 0)
                        
                        bot_response = f"# ⏳ Pagamentos Pendentes\n"
                        bot_response += f"**Total de pagamentos pendentes**: {count} | "
                        bot_response += f"**Valor total pendente**: R$ {float(total):.2f}\n"
                        
                        if count > 0 and 'payments' in pending_data:
                            bot_response += "### Lista de Pagamentos Pendentes\n"
                            
                            for i, payment in enumerate(pending_data.get('payments', []), 1):
                                bot_response += f"**{i}. Pagamento #{payment.get('id')}** - "
                                bot_response += f"Aluno: {payment.get('student_name', 'N/A')} ({payment.get('student_email', 'N/A')}) | "
                                bot_response += f"Curso: {payment.get('course_name', 'N/A')} | "
                                bot_response += f"Valor: R$ {float(payment.get('amount', 0)):.2f} | "
                                bot_response += f"Data: {payment.get('created_at', 'N/A')}\n"
                        else:
                            bot_response += "_Não há pagamentos pendentes no momento._\n"
                    else:
                        bot_response = "Não foram encontrados dados sobre pagamentos pendentes."
            else:
                # Se não for sobre finanças, prossegue normalmente
                logger.info("Consulta geral. Processando com OpenAI")
                bot_response = openai_manager.get_response(formatted_messages)
                logger.info("Resposta obtida da OpenAI")
            
            # Cria a mensagem do bot
            bot_message = Message.objects.create(
                chat_session=chat_session,
                sender='bot',
                content=bot_response
            )
            logger.info(f"Mensagem do bot salva: {bot_message.id}")
            
            return JsonResponse({
                'success': True,
                'response': bot_response,
                'timestamp': bot_message.timestamp.isoformat()
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON inválido: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'JSON inválido'
            }, status=400)
        except Exception as e:
            logger.error(f"Erro não esperado: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)

@csrf_exempt
def get_message_history(request):
    """API para buscar o histórico de mensagens de uma sessão"""
    if request.method == 'GET':
        session_id = request.GET.get('session_id')
        
        logger.info(f"Solicitando histórico para session_id: {session_id}")
        
        if not session_id:
            logger.warning("Parâmetro session_id não fornecido")
            return JsonResponse({
                'success': False,
                'message': 'Parâmetro session_id obrigatório'
            }, status=400)
        
        try:
            chat_session = ChatSession.objects.get(session_id=session_id, is_active=True)
            logger.info(f"Sessão encontrada: {chat_session.id}")
        except ChatSession.DoesNotExist:
            logger.warning(f"Sessão não encontrada: {session_id}")
            return JsonResponse({
                'success': False,
                'message': 'Sessão não encontrada'
            }, status=404)
        
        # Busca todas as mensagens da sessão
        messages = Message.objects.filter(chat_session=chat_session).order_by('timestamp')
        logger.info(f"Mensagens recuperadas: {messages.count()}")
        
        # Formata as mensagens para o retorno
        message_list = [{
            'id': msg.id,
            'sender': msg.sender,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages]
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'messages': message_list
        })
    
    logger.warning("Método não permitido para obter histórico")
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)

@login_required
def chat_history(request, session_id=None):
    """View para exibir o histórico de chat"""
    if session_id:
        try:
            session = ChatSession.objects.get(session_id=session_id)
            messages = session.messages.all()
            return render(request, 'assistant/history.html', {
                'session': session,
                'messages': messages
            })
        except ChatSession.DoesNotExist:
            pass
    
    # Se não houver session_id ou a sessão não existir, exibe todas as sessões do usuário
    sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, 'assistant/sessions.html', {'sessions': sessions})

def is_admin_or_staff(user):
    """Verifica se o usuário é admin ou staff"""
    return user.is_authenticated and (user.is_superuser or user.is_staff or user.user_type == 'ADMIN')

@login_required
def behavior_config(request):
    """
    View para configurar o comportamento do assistente IA.
    Permite criar ou editar o comportamento ativo sem precisar usar o admin do Django.
    """
    # Verifica se há um ID para editar (passado via query string)
    edit_id = request.GET.get('edit')
    
    # Verifica se o usuário pode editar (apenas admin ou staff)
    can_edit = is_admin_or_staff(request.user)
    
    if edit_id and can_edit:
        # Se foi solicitada a edição de um comportamento específico e usuário tem permissão
        behavior = get_object_or_404(AssistantBehavior, id=edit_id)
    else:
        # Busca o comportamento ativo ou cria um padrão se não existir
        behavior = AssistantBehavior.get_active_behavior()
    
    # Se não existir comportamento ativo, cria um objeto temporário (não salva no banco)
    if not behavior:
        behavior = AssistantBehavior(
            name="Comportamento Padrão",
            is_active=True,
            system_prompt="""Você é um assistente virtual para o CincoCincoJAM, uma plataforma que facilita a gestão de 
                      eventos e transmissões ao vivo, além de oferecer cursos online. Seja prestativo, 
                      educado e conciso em suas respostas.
                      
                      Quando o usuário fizer perguntas sobre a plataforma, você deve fornecer informações 
                      precisas e úteis. Se não souber a resposta para alguma pergunta específica sobre o sistema, 
                      seja honesto e sugira que o usuário entre em contato com o suporte."""
        )
    
    # Lista todos os comportamentos para exibir no histórico (apenas para admins e staff)
    all_behaviors = AssistantBehavior.objects.all().order_by('-updated_at') if can_edit else []
    
    return render(request, 'assistant/behavior_config.html', {
        'behavior': behavior,
        'all_behaviors': all_behaviors,
        'can_edit': can_edit,
    })

@login_required
@user_passes_test(is_admin_or_staff)
def save_behavior(request):
    """
    View para salvar o comportamento do assistente IA.
    """
    if request.method == 'POST':
        behavior_id = request.POST.get('behavior_id')
        name = request.POST.get('name')
        system_prompt = request.POST.get('system_prompt')
        is_active = bool(request.POST.get('is_active', False))
        
        if not name or not system_prompt:
            messages.error(request, 'Todos os campos são obrigatórios.')
            return redirect('assistant:behavior_config')
        
        # Se um ID foi fornecido, tenta atualizar o comportamento existente
        if behavior_id and behavior_id != 'new':
            try:
                behavior = AssistantBehavior.objects.get(id=behavior_id)
                behavior.name = name
                behavior.system_prompt = system_prompt
                behavior.is_active = is_active
                
                # Se este comportamento está sendo ativado, desativa todos os outros
                if is_active:
                    AssistantBehavior.objects.exclude(id=behavior.id).update(is_active=False)
                    
                behavior.save()
                messages.success(request, 'Comportamento do assistente atualizado com sucesso.')
            except AssistantBehavior.DoesNotExist:
                messages.error(request, 'Comportamento não encontrado.')
        else:
            # Cria um novo comportamento
            behavior = AssistantBehavior(
                name=name,
                system_prompt=system_prompt,
                is_active=is_active,
                created_by=request.user
            )
            
            # Se este comportamento está sendo ativado, desativa todos os outros
            if is_active:
                AssistantBehavior.objects.all().update(is_active=False)
                
            behavior.save()
            messages.success(request, 'Novo comportamento do assistente criado com sucesso.')
        
        return redirect('assistant:behavior_config')
    
    # Se não for um POST, redireciona para a página de configuração
    return redirect('assistant:behavior_config')
