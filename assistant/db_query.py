"""
Módulo otimizado para acesso direto e irrestrito ao banco de dados
Baseado no mapeamento oficial da estrutura do banco de dados
"""
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from core.models import User
from courses.models import Course, Lesson, Enrollment
from payments.models import PaymentTransaction
from invoices.models import Invoice, CompanyConfig
from scheduler.models import Event, EventLocation as Studio, Course, EventParticipant
from django.db.models import Q
import re
import pytz
from datetime import datetime, timedelta

def get_all_students():
    """
    Retorna todos os alunos/clientes da plataforma
    """
    try:
        # Consultar todos os usuários do tipo estudante
        students = User.objects.filter(user_type='STUDENT').order_by('username')
        
        result = "# 👥 Lista Completa de Alunos/Clientes\n"
        result += f"**Total de alunos cadastrados**: {students.count()}\n\n"
        
        # Evitar problemas de relacionamento verificando cada campo individualmente
        for i, student in enumerate(students, 1):
            try:
                # Verificar se há informações de nome
                first_name = student.first_name or "[Sem nome]"
                last_name = student.last_name or ""
                full_name = f"{first_name} {last_name}".strip()
                if not full_name or full_name == "[Sem nome]":
                    full_name = student.username or student.email
                
                # Buscar matrículas do aluno de forma segura
                enrollments = Enrollment.objects.filter(student_id=student.id)
                enrollment_count = enrollments.count()
                
                # Buscar pagamentos do aluno (considerando relação potencialmente diferente)
                # Verificar qual campo está sendo usado para a relação de usuário
                try:
                    payments = PaymentTransaction.objects.filter(user_id=student.id)
                except:
                    # Tentar outras possíveis relações
                    try:
                        payments = PaymentTransaction.objects.filter(student_id=student.id)
                    except:
                        # Se ambas falharem, criar lista vazia
                        payments = []
                        paid_amount = 0
                        
                # Se conseguiu obter pagamentos, calcular total pago
                if payments and hasattr(payments, 'filter'):
                    paid_amount = payments.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
                else:
                    # Alternativa: calcular a partir das matrículas
                    paid_amount = 0
                    for enrollment in enrollments:
                        try:
                            # Tentar obter pagamentos para esta matrícula
                            enrollment_payments = PaymentTransaction.objects.filter(
                                enrollment_id=enrollment.id, 
                                status='PAID'
                            )
                            if enrollment_payments.exists():
                                paid_amount += enrollment_payments.aggregate(Sum('amount'))['amount__sum'] or 0
                        except Exception:
                            # Ignorar erros neste nível
                            pass
                
                # Informações do aluno
                result += f"**{i}. {full_name}** ({student.username or student.email})\n"
                result += f"- **Email**: {student.email}\n"
                result += f"- **Cadastrado em**: {student.date_joined.strftime('%d/%m/%Y')}\n"
                result += f"- **Matrículas**: {enrollment_count}\n"
                result += f"- **Valor total pago**: R$ {float(paid_amount):.2f}\n\n"
                
            except Exception as student_error:
                # Registrar erro para este aluno mas continuar com os outros
                result += f"**{i}. Aluno ID {student.id}** (erro: {str(student_error)})\n\n"
        
        # Se não houver alunos, retornar mensagem específica
        if students.count() == 0:
            result += "Não há alunos cadastrados no sistema.\n"
            
        return result
    except Exception as e:
        return f"Erro ao acessar alunos: {str(e)}"

def get_course_students(course_title=None):
    """
    Retorna alunos matriculados em um curso específico
    """
    try:
        if course_title:
            course = Course.objects.filter(title__icontains=course_title).first()
            if not course:
                return f"Curso '{course_title}' não encontrado."
                
            enrollments = Enrollment.objects.filter(course=course).select_related('student')
            
            result = f"# 📚 Alunos Matriculados em: {course.title}\n"
            result += f"**Professor**: {course.professor.first_name} {course.professor.last_name}\n"
            result += f"**Preço**: R$ {float(course.price):.2f}\n"
            result += f"**Total de matrículas**: {enrollments.count()}\n\n"
            
            # Listar alunos do curso
            for i, enrollment in enumerate(enrollments, 1):
                student = enrollment.student
                result += f"**{i}. {student.first_name} {student.last_name}** ({student.email})\n"
                result += f"- Status: {enrollment.get_status_display()}\n"
                result += f"- Matriculado em: {enrollment.enrolled_at.strftime('%d/%m/%Y')}\n"
                
                # Verificar pagamento
                payment = PaymentTransaction.objects.filter(enrollment=enrollment).first()
                if payment:
                    result += f"- Pagamento: {payment.get_status_display()} "
                    result += f"(R$ {float(payment.amount):.2f})\n\n"
                else:
                    result += "- Pagamento: Não encontrado\n\n"
                    
            return result
        else:
            # Listar todos os cursos e quantidade de alunos
            courses = Course.objects.annotate(
                student_count=Count('enrollments')
            ).order_by('-student_count')
            
            result = "# 📚 Todos os Cursos e Seus Alunos\n\n"
            
            for i, course in enumerate(courses, 1):
                result += f"**{i}. {course.title}**\n"
                result += f"- Professor: {course.professor.first_name} {course.professor.last_name}\n"
                result += f"- Alunos matriculados: {course.student_count}\n"
                result += f"- Preço: R$ {float(course.price):.2f}\n\n"
                
            return result
    except Exception as e:
        return f"Erro ao acessar dados do curso: {str(e)}"

def get_financial_data():
    """
    Retorna dados financeiros completos da plataforma
    """
    try:
        result = "# 💰 Relatório Financeiro Completo\n\n"
        
        try:
            # Dados gerais de pagamentos
            transactions = PaymentTransaction.objects.all()
            total_revenue = transactions.filter(status='PAID').aggregate(Sum('amount'))['amount__sum'] or 0
            pending_amount = transactions.filter(status='PENDING').aggregate(Sum('amount'))['amount__sum'] or 0
            
            # Contagens de transações
            total_paid = transactions.filter(status='PAID').count()
            total_pending = transactions.filter(status='PENDING').count()
            total_cancelled = transactions.filter(status='CANCELLED').count()
        except Exception as payment_error:
            # Se ocorrer erro com transações, definir valores padrão
            result += f"_Aviso: Erro ao acessar transações: {str(payment_error)}_\n\n"
            total_revenue = 0
            pending_amount = 0
            total_paid = 0
            total_pending = 0
            total_cancelled = 0
            transactions = []
        
        try:
            # Matrículas e cursos - protegido contra erros
            total_enrollments = Enrollment.objects.count()
            total_courses = Course.objects.count()
            total_students = User.objects.filter(user_type='STUDENT').count()
        except Exception as counts_error:
            # Se ocorrer erro nas contagens, definir valores padrão
            result += f"_Aviso: Erro ao calcular contagens: {str(counts_error)}_\n\n"
            total_enrollments = 0
            total_courses = 0 
            total_students = 0
        
        # Continuando o relatório
        result += "## Resumo Geral\n"
        result += f"- **Faturamento total**: R$ {float(total_revenue):.2f}\n"
        result += f"- **Valor pendente**: R$ {float(pending_amount):.2f}\n"
        result += f"- **Transações pagas**: {total_paid}\n"
        result += f"- **Transações pendentes**: {total_pending}\n"
        result += f"- **Transações canceladas**: {total_cancelled}\n\n"
        
        result += "## Dados da Plataforma\n"
        result += f"- **Total de alunos**: {total_students}\n"
        result += f"- **Total de cursos**: {total_courses}\n"
        result += f"- **Total de matrículas**: {total_enrollments}\n\n"
        
        # Top cursos por faturamento - com tratamento de erro
        try:
            result += "## Top Cursos por Faturamento\n"
            top_courses = Course.objects.all()
            course_revenues = []
            
            # Calcular receita para cada curso com tratamento de exceções
            for course in top_courses:
                try:
                    # Obter matrículas do curso
                    enrollments = Enrollment.objects.filter(course=course)
                    # Obter pagamentos para essas matrículas
                    course_revenue = 0
                    for enrollment in enrollments:
                        try:
                            # Verificação robusta do relacionamento enrollment-payment
                            # Tenta diferentes possíveis nomes de campos
                            try:
                                paid = PaymentTransaction.objects.filter(
                                    enrollment=enrollment,
                                    status='PAID'
                                ).aggregate(Sum('amount'))['amount__sum'] or 0
                            except:
                                # Tentar outra abordagem com ID direto
                                paid = PaymentTransaction.objects.filter(
                                    enrollment_id=enrollment.id,
                                    status='PAID'
                                ).aggregate(Sum('amount'))['amount__sum'] or 0
                                
                            course_revenue += paid
                        except Exception:
                            # Ignorar erros neste nível e continuar
                            pass
                    
                    # Registrar curso e receita, mesmo que seja zero
                    course_revenues.append({
                        'course': course,
                        'revenue': course_revenue,
                        'enrollment_count': enrollments.count()
                    })
                except Exception as course_error:
                    # Registrar erro para este curso e continuar com os outros
                    result += f"_Erro ao calcular receita para o curso '{course.title}': {str(course_error)}_\n"
            
            # Ordenar por receita e obter os top 5
            if course_revenues:
                course_revenues.sort(key=lambda x: x['revenue'], reverse=True)
                top_courses_with_revenue = course_revenues[:5]
                
                # Mostrar os cursos com maior faturamento
                for i, course_data in enumerate(top_courses_with_revenue, 1):
                    course = course_data['course']
                    revenue = course_data['revenue']
                    enrollment_count = course_data['enrollment_count']
                    
                    result += f"**{i}. {course.title}**\n"
                    result += f"- Faturamento: R$ {float(revenue):.2f}\n"
                    result += f"- Matrículas: {enrollment_count}\n\n"
            else:
                result += "Não há dados de faturamento por curso disponíveis.\n\n"
        except Exception as top_courses_error:
            result += f"_Não foi possível listar os cursos por faturamento: {str(top_courses_error)}_\n\n"
        
        # Pagamentos recentes - com tratamento de erro
        try:
            # Pagamentos recentes (apenas se houver transações)
            if transactions and hasattr(transactions, 'filter'):
                recent_payments = transactions.filter(status='PAID').order_by('-created_at')[:5]
                
                result += "## Pagamentos Recentes\n"
                if recent_payments.exists():
                    for i, payment in enumerate(recent_payments, 1):
                        try:
                            # Tratamento robusto para relações que podem falhar
                            # Nome do usuário
                            try:
                                if payment.user:
                                    user_name = f"{payment.user.first_name or ''} {payment.user.last_name or ''}".strip()
                                    if not user_name:
                                        user_name = payment.user.username or payment.user.email
                                else:
                                    user_name = "N/A"
                            except:
                                user_name = "N/A"
                                
                            # Nome do curso
                            try:
                                if hasattr(payment, 'enrollment') and payment.enrollment:
                                    if hasattr(payment.enrollment, 'course') and payment.enrollment.course:
                                        course_name = payment.enrollment.course.title
                                    else:
                                        course_name = "N/A"
                                else:
                                    course_name = "N/A"
                            except:
                                course_name = "N/A"
                            
                            # Dados do pagamento
                            payment_id = payment.transaction_id if hasattr(payment, 'transaction_id') else f"ID: {payment.id}"
                            payment_amount = payment.amount if hasattr(payment, 'amount') else 0
                            payment_date = payment.created_at.strftime('%d/%m/%Y') if hasattr(payment, 'created_at') else "Data desconhecida"
                            
                            result += f"**{i}. {payment_id}**\n"
                            result += f"- Aluno: {user_name}\n"
                            result += f"- Curso: {course_name}\n"
                            result += f"- Valor: R$ {float(payment_amount):.2f}\n"
                            result += f"- Data: {payment_date}\n\n"
                        except Exception as payment_error:
                            result += f"**{i}. Pagamento** (erro: {str(payment_error)})\n\n"
                else:
                    result += "Não há pagamentos recentes registrados.\n\n"
            else:
                result += "## Pagamentos Recentes\nNão foi possível acessar os dados de pagamentos.\n\n"
                
            # Pagamentos pendentes (apenas se houver transações)
            if transactions and hasattr(transactions, 'filter'):
                try:
                    pending_payments = transactions.filter(status='PENDING').order_by('-created_at')
                    
                    result += "## Pagamentos Pendentes\n"
                    if pending_payments.exists():
                        for i, payment in enumerate(pending_payments[:5], 1):
                            try:
                                # Tratamento robusto para relações
                                # Nome do usuário
                                try:
                                    user_name = "N/A"
                                    if hasattr(payment, 'user') and payment.user:
                                        user_first = payment.user.first_name or ""
                                        user_last = payment.user.last_name or ""
                                        user_name = f"{user_first} {user_last}".strip() or payment.user.username or payment.user.email
                                except:
                                    pass
                                    
                                # Nome do curso
                                try:
                                    course_name = "N/A"
                                    if hasattr(payment, 'enrollment') and payment.enrollment:
                                        if hasattr(payment.enrollment, 'course') and payment.enrollment.course:
                                            course_name = payment.enrollment.course.title
                                except:
                                    pass
                                
                                result += f"**{i}. {payment.transaction_id or f'ID: {payment.id}'}**\n"
                                result += f"- Aluno: {user_name}\n"
                                result += f"- Curso: {course_name}\n"
                                result += f"- Valor: R$ {float(payment.amount):.2f}\n"
                                result += f"- Criado em: {payment.created_at.strftime('%d/%m/%Y')}\n\n"
                            except Exception as e:
                                # Ignorar erros individuais
                                result += f"**{i}. Pagamento pendente** (erro: {str(e)})\n\n"
                        
                        if pending_payments.count() > 5:
                            result += f"_... e mais {pending_payments.count() - 5} pagamentos pendentes_\n\n"
                    else:
                        result += "Não há pagamentos pendentes no momento.\n\n"
                except Exception as pending_error:
                    result += f"_Erro ao listar pagamentos pendentes: {str(pending_error)}_\n\n"
            else:
                result += "## Pagamentos Pendentes\nNão foi possível acessar os dados de pagamentos pendentes.\n\n"
        except Exception as payments_section_error:
            result += f"_Erro ao processar seção de pagamentos: {str(payments_section_error)}_\n\n"
            
        return result
    except Exception as e:
        return f"Erro ao acessar dados financeiros: {str(e)}"

def get_invoice_data(invoice_id=None, user_email=None):
    """
    Retorna dados de notas fiscais
    
    Args:
        invoice_id: ID específico da nota fiscal
        user_email: Email do usuário para filtrar notas
        
    Returns:
        String com dados formatados das notas fiscais
    """
    try:
        result = "# 📄 Informações de Notas Fiscais\n\n"
        
        # Caso específico de nota por ID
        if invoice_id:
            try:
                invoice = Invoice.objects.get(id=invoice_id)
                
                result += f"## 📃 Nota Fiscal #{invoice.id}\n\n"
                result += f"- **Status**: {invoice.get_status_display()}\n"
                result += f"- **Tipo**: {invoice.get_type_display() if hasattr(invoice, 'get_type_display') else invoice.type}\n"
                
                # Informações do RPS
                if invoice.rps_numero:
                    result += f"- **RPS**: Série {invoice.rps_serie}, Número {invoice.rps_numero}\n"
                
                # Informações da transação
                if invoice.transaction:
                    transaction = invoice.transaction
                    result += f"- **Transação**: #{transaction.id}\n"
                    result += f"- **Valor**: R$ {float(transaction.amount):.2f}\n"
                    
                    # Informações do estudante
                    try:
                        enrollment = transaction.enrollment
                        student = enrollment.student
                        result += f"- **Estudante**: {student.get_full_name() or student.email}\n"
                        result += f"- **Curso**: {enrollment.course.title}\n"
                    except:
                        result += "- **Erro**: Não foi possível obter informações do estudante/curso\n"
                elif invoice.amount:
                    # Se não tem transação mas tem valor direto
                    result += f"- **Valor**: R$ {float(invoice.amount):.2f}\n"
                    result += f"- **Cliente**: {invoice.customer_name or 'N/A'}\n"
                    result += f"- **Email**: {invoice.customer_email or 'N/A'}\n"
                    result += f"- **Descrição**: {invoice.description or 'N/A'}\n"
                
                # Datas
                result += f"- **Criada em**: {invoice.created_at.strftime('%d/%m/%Y %H:%M')}\n"
                if invoice.emitted_at:
                    result += f"- **Emitida em**: {invoice.emitted_at.strftime('%d/%m/%Y %H:%M')}\n"
                
                # Links
                if invoice.focus_pdf_url:
                    result += f"- **Link do PDF**: [Acessar PDF da nota]({invoice.focus_pdf_url})\n"
                
                # Erro (se houver)
                if invoice.error_message:
                    result += f"\n**Mensagem de erro**:\n```\n{invoice.error_message}\n```\n"
                
                return result
            except Invoice.DoesNotExist:
                return f"Nota fiscal com ID {invoice_id} não encontrada."
            except Exception as e:
                return f"Erro ao buscar nota fiscal específica: {str(e)}"
        
        # Filtro por email do usuário
        if user_email:
            try:
                user = User.objects.get(email=user_email)
                
                # Verificar se é professor, para mostrar notas emitidas
                if user.user_type == 'PROFESSOR':
                    # Buscar transações dos cursos deste professor que tenham notas
                    invoices = Invoice.objects.filter(
                        transaction__enrollment__course__professor=user
                    ).order_by('-created_at')
                    
                    result += f"## Notas Fiscais Emitidas pelo Professor {user.get_full_name() or user.email}\n\n"
                    
                # Verificar se é estudante, para mostrar notas recebidas
                elif user.user_type == 'STUDENT':
                    # Buscar transações deste estudante que tenham notas
                    invoices = Invoice.objects.filter(
                        transaction__enrollment__student=user
                    ).order_by('-created_at')
                    
                    result += f"## Notas Fiscais do Estudante {user.get_full_name() or user.email}\n\n"
                    
                else:
                    return f"Usuário {user_email} não é professor nem estudante."
                    
                if not invoices.exists():
                    return result + "Não foram encontradas notas fiscais para este usuário."
                
                # Mostrar resumo das notas
                result += f"**Total de notas encontradas**: {invoices.count()}\n\n"
                
                # Mostrar as 10 notas mais recentes
                for i, invoice in enumerate(invoices[:10], 1):
                    result += f"**{i}. Nota #{invoice.id}**\n"
                    result += f"- Status: {invoice.get_status_display()}\n"
                    
                    if invoice.transaction:
                        result += f"- Valor: R$ {float(invoice.transaction.amount):.2f}\n"
                        
                        # Dados do curso
                        try:
                            course = invoice.transaction.enrollment.course
                            result += f"- Curso: {course.title}\n"
                        except:
                            pass
                    elif invoice.amount:
                        result += f"- Valor: R$ {float(invoice.amount):.2f}\n"
                    
                    # Data de emissão
                    if invoice.emitted_at:
                        result += f"- Emitida em: {invoice.emitted_at.strftime('%d/%m/%Y')}\n"
                    else:
                        result += f"- Criada em: {invoice.created_at.strftime('%d/%m/%Y')}\n"
                    
                    # Link para PDF se disponível
                    if invoice.focus_pdf_url:
                        result += f"- [Ver PDF]({invoice.focus_pdf_url})\n"
                    
                    result += "\n"
                
                if invoices.count() > 10:
                    result += f"_... e mais {invoices.count() - 10} notas fiscais_\n"
                
                return result
            except User.DoesNotExist:
                return f"Usuário com email {user_email} não encontrado."
            except Exception as e:
                return f"Erro ao buscar notas por email: {str(e)}"
        
        # Sem filtros - retornar estatísticas gerais
        total_invoices = Invoice.objects.count()
        approved_invoices = Invoice.objects.filter(status='approved').count()
        processing_invoices = Invoice.objects.filter(status='processing').count()
        error_invoices = Invoice.objects.filter(status='error').count()
        
        result += "## Estatísticas Gerais de Notas Fiscais\n\n"
        result += f"- **Total de notas fiscais**: {total_invoices}\n"
        result += f"- **Notas aprovadas**: {approved_invoices}\n"
        result += f"- **Notas em processamento**: {processing_invoices}\n"
        result += f"- **Notas com erro**: {error_invoices}\n\n"
        
        # Últimas 5 notas emitidas
        recent_invoices = Invoice.objects.order_by('-created_at')[:5]
        
        if recent_invoices.exists():
            result += "## Notas Fiscais Recentes\n\n"
            
            for i, invoice in enumerate(recent_invoices, 1):
                result += f"**{i}. Nota #{invoice.id}**\n"
                result += f"- Status: {invoice.get_status_display()}\n"
                
                if invoice.transaction:
                    # Dados da transação
                    result += f"- Transação: #{invoice.transaction.id}\n"
                    result += f"- Valor: R$ {float(invoice.transaction.amount):.2f}\n"
                    
                    # Tentar obter dados do curso e estudante
                    try:
                        enrollment = invoice.transaction.enrollment
                        course = enrollment.course
                        student = enrollment.student
                        result += f"- Curso: {course.title}\n"
                        result += f"- Estudante: {student.get_full_name() or student.email}\n"
                        result += f"- Professor: {course.professor.get_full_name() or course.professor.email}\n"
                    except:
                        # Ignorar erros de relações
                        pass
                elif invoice.amount:
                    result += f"- Valor: R$ {float(invoice.amount):.2f}\n"
                    result += f"- Cliente: {invoice.customer_name or 'N/A'}\n"
                
                # Data de emissão
                if invoice.emitted_at:
                    result += f"- Emitida em: {invoice.emitted_at.strftime('%d/%m/%Y %H:%M')}\n"
                
                result += "\n"
        
        return result
    except Exception as e:
        return f"Erro ao acessar dados de notas fiscais: {str(e)}"

def process_db_query(query, request=None):
    """
    Processa uma consulta e retorna a resposta apropriada com base no tipo de consulta.
    Atualmente suporta:
    - Detalhes de sessões por ID
    - Listagem de alunos
    - Agendamento de sessões (nova funcionalidade)
    - Consulta de agendamentos existentes
    """
    # Lista de palavras-chave para detecção de agendamentos
    booking_keywords = ['agendar', 'agendamento', 'marcar', 'reservar', 'programar', 'criar sessão', 'criar evento']
    
    # Lista de palavras-chave para consulta de agendamentos existentes
    schedule_query_keywords = [
        'tenho', 'possuo', 'existe', 'há', 'tem', 'marcado', 'marcada', 'agenda', 
        'mostrar agendamento', 'ver agenda', 'consultar agenda', 'calendário', 'sessões',
        'quais', 'marcadas', 'aula', 'aulas', 'horário', 'horarios', 'listar', 'consultar',
        'verificar', 'checar', 'confirmar', 'agendadas', 'agendados', 'reservadas', 'reservados'
    ]
    
    query_lower = query.lower()
    
    # Reconhecimento específico para "quais sessões" antes das outras condições
    if ('quais' in query_lower and ('sessões' in query_lower or 'sessoes' in query_lower or 'aulas' in query_lower)) or \
       ('mostrar' in query_lower and ('agenda' in query_lower or 'horários' in query_lower or 'sessões' in query_lower)):
        try:
            # Adicionar "esta semana" se não especificou período
            if 'semana' not in query_lower and 'hoje' not in query_lower and 'amanhã' not in query_lower and 'sexta' not in query_lower and not re.search(r'\d{1,2}[/-]\d{1,2}', query_lower):
                query = query + " esta semana"
            
            result = get_schedule_info(query)
            if result is None:
                return {
                    "response_type": "text",
                    "content": "# 📅 Verificando seus agendamentos\n\nNão foi possível encontrar sessões agendadas para o período informado. Você pode agendar uma nova sessão a qualquer momento."
                }
            
            return {
                "response_type": "text",
                "content": str(result)
            }
        except Exception as e:
            return {
                "response_type": "text",
                "content": f"Erro ao consultar agendamentos: {str(e)}"
            }
    
    # Verificar se é uma consulta de agendamento
    if any(keyword in query_lower for keyword in booking_keywords):
        try:
            result = create_studio_booking(query)
            
            # Garantir que a resposta esteja no formato correto
            if isinstance(result, dict) and 'response_type' in result and 'content' in result:
                # Já está no formato adequado
                return result
            else:
                # Tratar como texto para evitar erros de NOT NULL
                return {
                    "response_type": "text",
                    "content": str(result)
                }
        except Exception as e:
            # Garantir que erros também sejam formatados corretamente
            return {
                "response_type": "text",
                "content": f"Erro ao processar agendamento: {str(e)}"
            }
    
    # Verificar se é uma consulta sobre agendamentos existentes
    if any(keyword in query_lower for keyword in schedule_query_keywords) and ('sessão' in query_lower or 'sessao' in query_lower or 'estudio' in query_lower or 'estúdio' in query_lower or 'agenda' in query_lower or 'aula' in query_lower):
        try:
            # Caso especial para consultas sobre "esta semana" ou "semana"
            if 'semana' in query_lower:
                query = query + " esta semana"  # Adiciona contexto para o processamento
            
            result = get_schedule_info(query)
            if result is None:
                # Caso a função get_schedule_info não processe adequadamente a consulta
                # Criar uma resposta genérica com base nos termos da consulta
                
                # Verificar se menciona um estúdio específico
                studio_info = extract_studio(query)
                studio_name = studio_info[0].name if studio_info else "qualquer estúdio"
                
                # Verificar se menciona uma data específica
                date_time_info = extract_date_time(query)
                date_str = ""
                if date_time_info:
                    date_time, _ = date_time_info
                    weekday = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'][date_time.weekday()]
                    date_str = f"{weekday}, {date_time.strftime('%d/%m/%Y')}"
                else:
                    date_str = "os próximos dias"
                
                return {
                    "response_type": "text",
                    "content": f"# 📅 Verificando agendamentos para {date_str}\n\nConsultando as sessões em {studio_name}...\n\nNão foi possível encontrar sessões agendadas para o período informado. Você pode agendar uma nova sessão a qualquer momento."
                }
            
            return {
                "response_type": "text",
                "content": str(result)
            }
        except Exception as e:
            return {
                "response_type": "text",
                "content": f"Erro ao consultar agendamentos: {str(e)}"
            }
    
    # Padrão para detalhes de sessão (busca por ID)
    session_pattern = r'sess[aãoõ][^0-9]*(\d+)'
    session_match = re.search(session_pattern, query_lower)

    # Padrão para listar alunos (usa keyword "lista")
    students_pattern = r'lista\s+de\s+alunos'
    students_match = re.search(students_pattern, query_lower)

    # Processar com base no tipo de consulta identificado
    try:
        if session_match:
            # Extrair ID da sessão
            session_id = session_match.group(1)
            result = get_session_details(session_id)
            
            # Garantir formato adequado
            return {
                "response_type": "text",
                "content": str(result)
            }
        elif students_match:
            result = get_all_students()
            
            # Garantir formato adequado
            return {
                "response_type": "text",
                "content": str(result)
            }
        else:
            # Se não for uma consulta específica reconhecida
            return {
                "response_type": "text",
                "content": "Não entendi sua consulta. Você pode me perguntar sobre detalhes de sessões específicas, solicitar a lista de alunos, ou agendar uma nova sessão."
            }
    except Exception as e:
        # Garantir que erros também sejam formatados corretamente
        return {
            "response_type": "text",
            "content": f"Erro ao processar consulta: {str(e)}"
        }

def get_session_details(session_index):
    """
    Retorna detalhes completos sobre uma sessão específica
    
    Args:
        session_index: índice da sessão (1-based) ou ID da sessão
    """
    try:
        from scheduler.models import Event, EventLocation, EventParticipant
        from core.models import User
        
        # Identificar o professor atual (para fins de demonstração, usamos o primeiro professor)
        current_user = User.objects.filter(user_type='PROFESSOR').first()
        
        if not current_user:
            return "Não foi possível identificar o professor. Por favor, entre em contato com o suporte."
        
        # Buscar eventos do professor atual
        upcoming_events = Event.objects.filter(
            professor=current_user,
            start_time__gte=timezone.now(),
            status__in=['SCHEDULED', 'CONFIRMED']
        ).order_by('start_time')
        
        # Se não há eventos, informar ao usuário
        if not upcoming_events.exists():
            return "Você não tem sessões agendadas no momento para mostrar detalhes."
        
        # Determinar qual sessão buscar
        target_event = None
        
        if isinstance(session_index, int):
            if session_index > 0 and session_index <= upcoming_events.count():
                # Índice baseado em 1 (primeiro = 1, segundo = 2, etc.)
                target_event = upcoming_events[session_index-1]
            elif session_index == 0:  # Próxima sessão
                target_event = upcoming_events.first()
            elif session_index == -1:  # Última sessão
                target_event = upcoming_events.last()
            else:
                # Tentar buscar pelo ID do evento
                try:
                    target_event = Event.objects.get(id=session_index, professor=current_user)
                except Event.DoesNotExist:
                    return f"Sessão com ID {session_index} não encontrada."
        
        if not target_event:
            return f"Não foi possível encontrar a sessão especificada. Você tem {upcoming_events.count()} sessões agendadas."
        
        # Formatar resposta com detalhes completos
        result = f"# 🎵 Detalhes da Sessão: {target_event.title}\n\n"
        
        # Informações básicas
        start_date = target_event.start_time.strftime('%d/%m/%Y')
        start_time = target_event.start_time.strftime('%H:%M')
        end_time = target_event.end_time.strftime('%H:%M')
        weekday = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'][target_event.start_time.weekday()]
        
        result += f"## 📅 Informações Gerais\n\n"
        result += f"- **Data**: {weekday}, {start_date}\n"
        result += f"- **Horário**: {start_time} às {end_time}\n"
        result += f"- **Duração**: {int(target_event.duration_minutes)} minutos\n"
        result += f"- **Status**: {target_event.get_status_display()}\n"
        
        # Local do evento
        if target_event.location:
            location = target_event.location
            result += f"\n## 📍 Local\n\n"
            result += f"- **Estúdio**: {location.name}\n"
            
            if location.is_online:
                result += f"- **Tipo**: Virtual/Online\n"
                if location.meeting_link:
                    result += f"- **Link de acesso**: {location.meeting_link}\n"
            else:
                result += f"- **Tipo**: Presencial\n"
                if location.address:
                    result += f"- **Endereço**: {location.address}\n"
            
            if location.phone:
                result += f"- **Telefone**: {location.phone}\n"
            
            if location.email:
                result += f"- **Email**: {location.email}\n"
        else:
            result += "\n## 📍 Local\n\n"
            result += "- Local não definido para esta sessão\n"
        
        # Participantes
        participants = EventParticipant.objects.filter(
            event=target_event
        ).select_related('student')
        
        result += f"\n## 👥 Participantes ({participants.count()})\n\n"
        
        if participants.exists():
            # Agrupar por status
            confirmed = participants.filter(attendance_status='CONFIRMED')
            pending = participants.filter(attendance_status='PENDING')
            cancelled = participants.filter(attendance_status='CANCELLED')
            attended = participants.filter(attendance_status='ATTENDED')
            missed = participants.filter(attendance_status='MISSED')
            
            # Mostrar confirmados
            if confirmed.exists():
                result += f"### ✅ Confirmados ({confirmed.count()})\n\n"
                for i, p in enumerate(confirmed, 1):
                    student = p.student
                    result += f"{i}. **{student.first_name} {student.last_name}** ({student.email})\n"
                    if p.confirmed_at:
                        result += f"   - Confirmado em: {p.confirmed_at.strftime('%d/%m/%Y %H:%M')}\n"
                    if p.notes:
                        result += f"   - Observações: {p.notes}\n"
                result += "\n"
            
            # Mostrar pendentes
            if pending.exists():
                result += f"### ⏳ Pendentes ({pending.count()})\n\n"
                for i, p in enumerate(pending, 1):
                    student = p.student
                    result += f"{i}. **{student.first_name} {student.last_name}** ({student.email})\n"
                result += "\n"
            
            # Mostrar cancelados
            if cancelled.exists():
                result += f"### ❌ Cancelados ({cancelled.count()})\n\n"
                for i, p in enumerate(cancelled, 1):
                    student = p.student
                    result += f"{i}. **{student.first_name} {student.last_name}** ({student.email})\n"
                result += "\n"
            
            # Mostrar que compareceram (se for evento passado)
            if attended.exists():
                result += f"### ✓ Compareceram ({attended.count()})\n\n"
                for i, p in enumerate(attended, 1):
                    student = p.student
                    result += f"{i}. **{student.first_name} {student.last_name}** ({student.email})\n"
                result += "\n"
            
            # Mostrar que faltaram (se for evento passado)
            if missed.exists():
                result += f"### ✗ Faltaram ({missed.count()})\n\n"
                for i, p in enumerate(missed, 1):
                    student = p.student
                    result += f"{i}. **{student.first_name} {student.last_name}** ({student.email})\n"
                result += "\n"
        else:
            result += "_Não há participantes registrados para esta sessão._\n\n"
        
        # Descrição e observações
        if target_event.description:
            result += f"\n## 📝 Descrição\n\n{target_event.description}\n\n"
        
        # Curso relacionado
        if target_event.course:
            course = target_event.course
            result += f"\n## 📚 Curso Relacionado\n\n"
            result += f"- **Curso**: {course.title}\n"
            result += f"- **Professor**: {course.professor.first_name} {course.professor.last_name}\n"
            
        # Opções interativas
        result += "\n## O que mais posso te ajudar?\n\n"
        result += "- 📝 Gostaria de editar esta sessão? Posso te mostrar como acessar o painel de edição.\n"
        result += "- 📧 Quer enviar um lembrete para os participantes pendentes?\n"
        result += "- 📊 Precisa ver o histórico completo de sessões com estes alunos?\n"
        result += "- 📆 Quer agendar uma sessão de acompanhamento após esta?\n\n"
        result += f"_Basta perguntar! Por exemplo: 'Envie um lembrete para os participantes pendentes' ou 'Crie uma nova sessão com estes mesmos alunos'_\n"
        
        return result
    except Exception as e:
        return f"Erro ao buscar detalhes da sessão: {str(e)}"

def get_session_student_list(session_index):
    """
    Retorna a lista completa de alunos para uma sessão específica
    
    Args:
        session_index: índice da sessão (1-based) ou ID da sessão
    """
    try:
        from scheduler.models import Event, EventParticipant
        from core.models import User
        
        # Identificar o professor atual (para fins de demonstração, usamos o primeiro professor)
        current_user = User.objects.filter(user_type='PROFESSOR').first()
        
        if not current_user:
            return "Não foi possível identificar o professor. Por favor, entre em contato com o suporte."
        
        # Buscar eventos do professor atual
        upcoming_events = Event.objects.filter(
            professor=current_user,
            start_time__gte=timezone.now(),
            status__in=['SCHEDULED', 'CONFIRMED']
        ).order_by('start_time')
        
        # Se não há eventos, informar ao usuário
        if not upcoming_events.exists():
            return "Você não tem sessões agendadas no momento para mostrar participantes."
        
        # Determinar qual sessão buscar
        target_event = None
        
        if isinstance(session_index, int):
            if session_index > 0 and session_index <= upcoming_events.count():
                # Índice baseado em 1 (primeiro = 1, segundo = 2, etc.)
                target_event = upcoming_events[session_index-1]
            elif session_index == 0:  # Próxima sessão
                target_event = upcoming_events.first()
            elif session_index == -1:  # Última sessão
                target_event = upcoming_events.last()
            else:
                # Tentar buscar pelo ID do evento
                try:
                    target_event = Event.objects.get(id=session_index, professor=current_user)
                except Event.DoesNotExist:
                    return f"Sessão com ID {session_index} não encontrada."
        
        if not target_event:
            return f"Não foi possível encontrar a sessão especificada. Você tem {upcoming_events.count()} sessões agendadas."
        
        # Buscar participantes desta sessão
        participants = EventParticipant.objects.filter(
            event=target_event
        ).select_related('student').order_by('student__first_name')
        
        # Formatar resposta
        start_date = target_event.start_time.strftime('%d/%m/%Y')
        start_time = target_event.start_time.strftime('%H:%M')
        
        result = f"# 👥 Lista de Participantes - {target_event.title}\n\n"
        result += f"**Data**: {start_date}, {start_time}\n"
        result += f"**Local**: {target_event.location.name if target_event.location else 'Local não definido'}\n\n"
        
        if participants.exists():
            result += f"## Lista Completa ({participants.count()} participantes)\n\n"
            
            # Agrupar por status para facilitar a visualização
            status_groups = {
                'CONFIRMED': '✅ Confirmados',
                'PENDING': '⏳ Pendentes',
                'CANCELLED': '❌ Cancelados',
                'ATTENDED': '✓ Compareceram',
                'MISSED': '✗ Faltaram'
            }
            
            # Criar tabela de participantes por status
            for status, label in status_groups.items():
                status_participants = participants.filter(attendance_status=status)
                if status_participants.exists():
                    result += f"### {label} ({status_participants.count()})\n\n"
                    
                    for i, p in enumerate(status_participants, 1):
                        student = p.student
                        result += f"{i}. **{student.first_name} {student.last_name}**\n"
                        result += f"   - Email: {student.email}\n"
                        if student.phone:
                            result += f"   - Telefone: {student.phone}\n"
                        if p.confirmed_at and status == 'CONFIRMED':
                            result += f"   - Confirmado em: {p.confirmed_at.strftime('%d/%m/%Y %H:%M')}\n"
                        if p.notes:
                            result += f"   - Observações: {p.notes}\n"
                        result += "\n"
        else:
            result += "_Não há participantes registrados para esta sessão._\n\n"
        
        # Opções interativas
        result += "## Ações disponíveis\n\n"
        result += "- 📧 Enviar email para todos os participantes\n"
        result += "- 📲 Enviar WhatsApp para confirmar presença dos pendentes\n"
        result += "- ➕ Adicionar mais participantes a esta sessão\n"
        result += "- 📊 Gerar lista de presença para impressão\n\n"
        result += f"_Para realizar alguma dessas ações, basta me pedir. Por exemplo: 'Envie um lembrete para os participantes pendentes da sessão {session_index}'_\n"
        
        return result
    except Exception as e:
        return f"Erro ao buscar lista de participantes: {str(e)}"

def get_schedule_info(query=None):
    """
    Retorna informações sobre agendamentos e sessões de estúdio
    usando os modelos reais do sistema de agendamento.
    """
    try:
        from scheduler.models import Event, EventLocation, EventParticipant
        from django.db.models import Q
        import re
        from datetime import datetime, timedelta
        
        result = "# 🎵 Sessões de Estúdio e Eventos Agendados\n\n"
        
        # Verificar se é uma busca por disponibilidade em uma data específica
        date_specific = False
        studio_specific = False
        is_week_query = False
        is_my_events_query = False
        target_date = None
        target_studio_name = None
        target_studio = None
        
        query_lower = query.lower() if query else ""
        
        # Verificar se é uma consulta sobre "essa semana" ou "próxima semana"
        if any(term in query_lower for term in ['essa semana', 'esta semana', 'semana atual', 'nessa semana', 'nesta semana']):
            is_week_query = True
            # Essa semana = hoje até domingo
            today = timezone.now().date()
            days_to_sunday = 6 - today.weekday()  # 6 = domingo
            end_date = today + timedelta(days=days_to_sunday)
            date_specific = True
            
        elif any(term in query_lower for term in ['próxima semana', 'proxima semana', 'semana que vem']):
            is_week_query = True
            # Próxima semana = próxima segunda até próximo domingo
            today = timezone.now().date()
            days_to_next_monday = 7 - today.weekday() if today.weekday() > 0 else 1
            start_date = today + timedelta(days=days_to_next_monday)
            end_date = start_date + timedelta(days=6)
            date_specific = True
            
        # Verificar se é uma pergunta sobre "minhas sessões"
        if any(term in query_lower for term in ['meus agendamentos', 'minhas sessões', 'meus eventos', 'minhas aulas', 'meu calendário']):
            is_my_events_query = True
        
        # Usar extract_date_time para datas específicas mencionadas na consulta
        date_time_info = extract_date_time(query)
        if date_time_info:
            date_time, timezone_name = date_time_info
            target_date = date_time.date()
            date_specific = True
        
        # Usar extract_studio para estúdios específicos mencionados na consulta
        studio_info = extract_studio(query)
        if studio_info:
            target_studio, target_studio_id = studio_info
            target_studio_name = target_studio.name
            studio_specific = True
        else:
            # Manter a lógica original como fallback
            all_studios = EventLocation.objects.filter(is_active=True)
            
            # Verificar menções a localizações específicas (bairros/áreas)
            location_keywords = {
                'barra': ['barra', 'barra da tijuca'],
                'botafogo': ['botafogo'],
                'ipanema': ['ipanema'],
                'centro': ['centro', 'downtown'],
                'zona sul': ['zona sul', 'south zone'],
                'zona norte': ['zona norte', 'north zone']
            }
            
            if not studio_specific:
                for location, keywords in location_keywords.items():
                    if any(keyword in query_lower for keyword in keywords):
                        # Tentar encontrar um estúdio com esta localização no nome ou endereço
                        for studio in all_studios:
                            address = studio.address.lower() if studio.address else ""
                            if location in studio.name.lower() or location in address:
                                target_studio = studio
                                target_studio_name = studio.name
                                studio_specific = True
                                break
                        # Se encontrou um estúdio, não continuar procurando
                        if studio_specific:
                            break
        
        # Verificar se é uma consulta sobre sessões agendadas nesta semana
        if is_week_query or is_my_events_query or (query_lower and 'agendad' in query_lower):
            try:
                from core.models import User
                current_user = User.objects.filter(user_type='PROFESSOR').first()
                
                if not current_user:
                    return "Não foi possível identificar o professor. Por favor, entre em contato com o suporte."
                
                # Definir o período para consulta
                if is_week_query:
                    # Essa/próxima semana
                    today = timezone.now().date()
                    
                    if 'próxima' in query_lower or 'proxima' in query_lower:
                        # Próxima semana = próxima segunda a domingo
                        days_to_next_monday = 7 - today.weekday() if today.weekday() > 0 else 1
                        start_date = today + timedelta(days=days_to_next_monday)
                    else:
                        # Essa semana = hoje até domingo
                        start_date = today
                        
                    # Final da semana é domingo
                    days_to_end = 6 - start_date.weekday()
                    end_date = start_date + timedelta(days=days_to_end)
                    
                    start_datetime = timezone.datetime.combine(start_date, datetime.min.time())
                    start_datetime = timezone.make_aware(start_datetime)
                    
                    end_datetime = timezone.datetime.combine(end_date, datetime.max.time())
                    end_datetime = timezone.make_aware(end_datetime)
                    
                elif target_date:
                    # Data específica
                    start_datetime = timezone.datetime.combine(target_date, datetime.min.time())
                    start_datetime = timezone.make_aware(start_datetime)
                    
                    end_datetime = timezone.datetime.combine(target_date, datetime.max.time())
                    end_datetime = timezone.make_aware(end_datetime)
                else:
                    # Período padrão: próximos 7 dias
                    start_datetime = timezone.now()
                    end_datetime = start_datetime + timedelta(days=7)
                
                # Criar o filtro de eventos
                events_filter = Q(
                    start_time__gte=start_datetime,
                    start_time__lte=end_datetime,
                    status__in=['SCHEDULED', 'CONFIRMED']
                )
                
                # Se for consulta pessoal, filtrar por professor
                if is_my_events_query:
                    events_filter &= Q(professor=current_user)
                
                # Se especificou estúdio, filtrar por estúdio
                if studio_specific and target_studio:
                    events_filter &= Q(location=target_studio)
                
                # Buscar eventos para o período
                events = Event.objects.filter(events_filter).order_by('start_time').select_related('location', 'professor')
                
                # Formatar o cabeçalho da resposta
                if is_week_query:
                    if 'próxima' in query_lower or 'proxima' in query_lower:
                        result = f"# 📅 Sessões Agendadas para a Próxima Semana ({start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')})\n\n"
                    else:
                        result = f"# 📅 Sessões Agendadas para Esta Semana ({start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')})\n\n"
                elif target_date:
                    weekday = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'][target_date.weekday()]
                    result = f"# 📅 Sessões Agendadas para {weekday}, {target_date.strftime('%d/%m/%Y')}\n\n"
                else:
                    result = "# 📅 Sessões Agendadas para os Próximos Dias\n\n"
                
                if is_my_events_query:
                    result = result.replace("Sessões Agendadas", "Suas Sessões Agendadas")
                
                if studio_specific and target_studio_name:
                    result = result.replace("\n\n", f" no Estúdio {target_studio_name}\n\n")
                
                # Verificar se há eventos
                if events.exists():
                    # Agrupar eventos por estúdio - apenas se não for filtrado por estúdio específico
                    if not studio_specific:
                        events_by_location = {}
                        for event in events:
                            location_name = event.location.name if event.location else "Sem local definido"
                            if location_name not in events_by_location:
                                events_by_location[location_name] = []
                            events_by_location[location_name].append(event)
                        
                        # Mostrar apenas estúdios que têm sessões agendadas
                        for location_name, location_events in events_by_location.items():
                            if location_events:  # Apenas mostrar estúdios com eventos
                                result += f"## 🏢 {location_name}\n\n"
                                
                                for i, event in enumerate(location_events, 1):
                                    # Formatação de data e hora
                                    weekday = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][event.start_time.weekday()]
                                    start_date = event.start_time.strftime('%d/%m/%Y')
                                    start_time = event.start_time.strftime('%H:%M')
                                    end_time = event.end_time.strftime('%H:%M')
                                    
                                    # Formatar saída do evento
                                    result += f"**{i}. {event.title}**\n"
                                    result += f"- **Data**: {weekday}, {start_date}\n"
                                    result += f"- **Horário**: {start_time} às {end_time}\n"
                                    result += f"- **Status**: {event.get_status_display()}\n"
                                    result += f"- **Professor**: {event.professor.first_name} {event.professor.last_name}\n"
                                    
                                    # Mostrar número de participantes
                                    participant_count = event.participants.count()
                                    result += f"- **Participantes**: {participant_count}\n\n"
                                    
                                    # Mostrar primeiros participantes se houver muitos
                                    if participant_count > 0:
                                        participants = EventParticipant.objects.filter(
                                            event=event
                                        ).select_related('student')[:3]
                                        
                                        if participants:
                                            result += "  _Alguns participantes:_ "
                                            for p in participants:
                                                result += f"{p.student.first_name}, "
                                            result = result.rstrip(", ")
                                            
                                            if participant_count > 3:
                                                result += f" _e mais {participant_count - 3}_"
                                            
                                            result += "\n\n"
                    else:
                        # Mostrar eventos em ordem cronológica (quando filtrado por estúdio específico)
                        for i, event in enumerate(events, 1):
                            # Formatação de data e hora
                            weekday = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][event.start_time.weekday()]
                            start_date = event.start_time.strftime('%d/%m/%Y')
                            start_time = event.start_time.strftime('%H:%M')
                            end_time = event.end_time.strftime('%H:%M')
                            
                            # Formatar saída do evento
                            result += f"**{i}. {event.title}**\n"
                            result += f"- **Data**: {weekday}, {start_date}\n"
                            result += f"- **Horário**: {start_time} às {end_time}\n"
                            result += f"- **Status**: {event.get_status_display()}\n"
                            result += f"- **Professor**: {event.professor.first_name} {event.professor.last_name}\n"
                            
                            # Mostrar número de participantes
                            participant_count = event.participants.count()
                            result += f"- **Participantes**: {participant_count}\n\n"
                            
                            # Mostrar primeiros participantes se houver muitos
                            if participant_count > 0:
                                participants = EventParticipant.objects.filter(
                                    event=event
                                ).select_related('student')[:3]
                                
                                if participants:
                                    result += "  _Alguns participantes:_ "
                                    for p in participants:
                                        result += f"{p.student.first_name}, "
                                    result = result.rstrip(", ")
                                    
                                    if participant_count > 3:
                                        result += f" _e mais {participant_count - 3}_"
                                    
                                    result += "\n\n"
                    
                    # Adicionar perguntas interativas no final
                    result += "## O que mais posso te ajudar?\n\n"
                    result += "- 🔍 Gostaria de ver os detalhes completos de alguma sessão específica?\n"
                    result += "- 📝 Quer saber como editar algum dos agendamentos?\n"
                    result += "- 👥 Precisa ver a lista completa de participantes de alguma sessão?\n"
                    result += "- 📊 Quer verificar a disponibilidade de horários para agendar novas sessões?\n\n"
                    result += "_Basta perguntar! Por exemplo: 'Mostre-me os detalhes da sessão 2' ou 'Qual a disponibilidade do estúdio da Barra para a próxima semana?'_\n\n"
                    
                else:
                    # Não há eventos para o período
                    result += "_Não há sessões agendadas para este período._\n\n"
                    
                    # Sugerir próximas ações
                    result += "## Quer agendar uma nova sessão?\n\n"
                    result += "- 📆 Posso mostrar a disponibilidade dos estúdios para este período.\n"
                    result += "- 🔍 Talvez você queira verificar outro período ou outro estúdio?\n"
                    result += "- 📋 Ou precisa de ajuda para criar um novo agendamento?\n\n"
                    
                    # Dar dicas específicas baseadas no contexto
                    if studio_specific:
                        result += f"_Dica: O estúdio {target_studio_name} está completamente disponível para este período. Você pode agendar qualquer horário._\n\n"
                    elif is_week_query:
                        result += "_Dica: Experimente perguntar 'Quais estúdios estão disponíveis esta semana?' para ver opções de agendamento._\n\n"
                    
                # Adicionar instruções para agendamento no final
                result += "## Como agendar uma nova sessão\n\n"
                result += "Para agendar um novo evento ou sessão de estúdio, acesse o painel de administração "
                result += "e navegue até 'Agenda > Eventos'. Lá você poderá criar um novo evento, "
                result += "selecionar o estúdio desejado e adicionar participantes.\n"
                
                return result
                
            except Exception as e:
                return f"Erro ao buscar agendamentos: {str(e)}"
                
    except ImportError:
        # Fallback se os modelos não puderem ser importados
        return "O sistema de agendamento de estúdio está em manutenção no momento. " + \
               "Por favor, entre em contato com o suporte técnico para agendar sessões."
    except Exception as e:
        return f"Erro ao obter informações de agendamento: {str(e)}"
    
    # Caso nenhuma das consultas específicas seja processada, retornar uma resposta genérica
    # para que a função não retorne None
    return "# 📅 Sessões Agendadas\n\nNão há sessões agendadas para o período informado. Você pode agendar uma nova sessão a qualquer momento."

def create_studio_booking(query):
    """
    Processa uma solicitação de agendamento de estúdio.
    Extrai informações como data, hora, estúdio, participantes e cria um evento no banco de dados.
    """
    # Extrair informações da consulta
    date_time_info = extract_date_time(query)
    studio_info = extract_studio(query)
    session_title = extract_session_title(query)
    duration = extract_duration(query) 
    course_info = extract_course(query)
    participants_info = extract_participants(query)
    
    # Verificar se há informações suficientes
    missing_info = []
    if not date_time_info:
        missing_info.append("data e hora")
    if not studio_info:
        missing_info.append("estúdio")
    if not session_title:
        missing_info.append("título ou propósito da sessão")
    
    # Se faltam informações, pedir ao usuário
    if missing_info:
        missing_str = ", ".join(missing_info)
        return {
            "response_type": "text",
            "content": f"Para agendar sua sessão de estúdio, preciso de mais algumas informações:\n\n" +
                      f"ℹ️ Informações que faltam: *{missing_str}*\n\n" +
                      f"Poderia me informar esses detalhes para que eu possa finalizar seu agendamento? Exemplo de solicitação completa: 'Agendar aula de violão no estúdio Barra para amanhã às 15h'"
        }
    
    # Desempacotar informações
    start_datetime, timezone_name = date_time_info
    studio, studio_id = studio_info
    
    # Definir duração padrão se não foi especificada
    if not duration:
        duration = 60  # Padrão: 1 hora
    
    # Verificar que a duração está dentro de limites razoáveis (entre 15 minutos e 8 horas)
    duration = max(15, min(duration, 480))
    
    # Calcular horário de término
    end_datetime = start_datetime + timedelta(minutes=duration)
    
    # Garantir que data e hora estejam no futuro
    # Usar timezones consistentes para comparar datas
    timezone_obj = pytz.timezone(timezone_name)
    now_utc = timezone.now()
    
    # Converter ambos para o timezone local (America/Sao_Paulo) antes de comparar
    now_local = now_utc.astimezone(timezone_obj)
    
    # Garantir que start_datetime esteja no mesmo timezone antes de comparar
    start_local = start_datetime.astimezone(timezone_obj)
    
    # Comparar ambos no mesmo timezone
    if start_local < now_local:
        # Se a data solicitada já passou, agendar para amanhã no mesmo horário
        tomorrow = (now_local + timedelta(days=1)).date()
        
        # Combinar a data de amanhã com o horário original
        tomorrow_time = start_local.time()
        tomorrow_naive = datetime.combine(tomorrow, tomorrow_time)
        start_datetime = timezone.make_aware(tomorrow_naive, timezone=timezone_obj)
        end_datetime = start_datetime + timedelta(minutes=duration)
    
    # Verificar disponibilidade do estúdio
    try:
        # Garantir que ambas as datas estejam no mesmo timezone para a consulta ao banco
        start_datetime_utc = start_datetime.astimezone(timezone.utc)
        end_datetime_utc = end_datetime.astimezone(timezone.utc)
        
        conflicting_events = Event.objects.filter(
            Q(location_id=studio_id) &
            (
                # Eventos que começam durante o novo evento
                (Q(start_time__gte=start_datetime_utc) & Q(start_time__lt=end_datetime_utc)) |
                # Eventos que terminam durante o novo evento
                (Q(end_time__gt=start_datetime_utc) & Q(end_time__lte=end_datetime_utc)) |
                # Eventos que englobam completamente o novo evento
                (Q(start_time__lte=start_datetime_utc) & Q(end_time__gte=end_datetime_utc))
            )
        )
    except Exception as e:
        return {
            "response_type": "text",
            "content": f"Erro ao verificar disponibilidade do estúdio: {str(e)}"
        }
    
    # Se houver conflitos, sugerir horários alternativos
    if conflicting_events.exists():
        conflict_list = []
        for event in conflicting_events:
            start_time = event.start_time.strftime('%H:%M')
            end_time = event.end_time.strftime('%H:%M')
            date = event.start_time.strftime('%d/%m/%Y')
            conflict_list.append(f"• {date} das {start_time} às {end_time}: {event.title}")
        
        conflict_str = "\n".join(conflict_list)
        
        # Sugerir horários alternativos (mais coerentes)
        try:
            # 1. No mesmo dia, 1h30 antes do horário solicitado
            alt_start_1 = start_datetime - timedelta(minutes=90)
            alt_end_1 = alt_start_1 + timedelta(minutes=duration)
            
            # 2. No mesmo dia, 1h30 depois do horário solicitado
            alt_start_2 = end_datetime + timedelta(minutes=30)
            alt_end_2 = alt_start_2 + timedelta(minutes=duration)
            
            # 3. No dia seguinte, mesmo horário
            next_day = start_datetime + timedelta(days=1)
            # Usar diretamente o timedelta para manter o timezone
            alt_start_3 = next_day
            alt_end_3 = alt_start_3 + timedelta(minutes=duration)
            
            # Verificar se os horários estão coerentes
            # Se o horário de término for anterior ao de início, significa que houve um erro
            if alt_end_1 < alt_start_1:
                # Corrigir calculando o fim como início + duração
                alt_end_1 = alt_start_1 + timedelta(minutes=duration)
            
            if alt_end_2 < alt_start_2:
                # Corrigir calculando o fim como início + duração
                alt_end_2 = alt_start_2 + timedelta(minutes=duration)
            
            if alt_end_3 < alt_start_3:
                # Corrigir calculando o fim como início + duração
                alt_end_3 = alt_start_3 + timedelta(minutes=duration)
            
            # Buscar outras unidades disponíveis no mesmo horário
            other_studios = Studio.objects.filter(is_active=True).exclude(id=studio_id)
            available_studios = []
            
            for other_studio in other_studios:
                # Verificar se há conflitos nesta unidade no mesmo horário
                try:
                    conflicts = Event.objects.filter(
                        Q(location=other_studio) &
                        (
                            (Q(start_time__gte=start_datetime_utc) & Q(start_time__lt=end_datetime_utc)) |
                            (Q(end_time__gt=start_datetime_utc) & Q(end_time__lte=end_datetime_utc)) |
                            (Q(start_time__lte=start_datetime_utc) & Q(end_time__gte=end_datetime_utc))
                        )
                    ).exists()
                    
                    if not conflicts:
                        available_studios.append(other_studio)
                except Exception as e:
                    # Ignorar erro e continuar com os próximos estúdios
                    continue
        except Exception as e:
            return {
                "response_type": "text",
                "content": f"Erro ao calcular horários alternativos: {str(e)}"
            }
        
        # Formatar mensagem amigável
        response = f"Olá! Infelizmente o estúdio {studio.name} já está reservado no horário solicitado para as seguintes atividades:\n\n"
        response += f"{conflict_str}\n\n"
        
        response += "Posso sugerir algumas alternativas:\n\n"
        
        # Formatar horários de forma mais clara
        def format_time_range(start, end):
            start_date = start.strftime('%d/%m/%Y')
            start_time = start.strftime('%H:%M')
            end_time = end.strftime('%H:%M')
            return f"{start_date} das {start_time} às {end_time}"
        
        # Sugestões de horários alternativos
        response += "📅 *Outros horários disponíveis:*\n"
        response += f"• {format_time_range(alt_start_1, alt_end_1)} no {studio.name}\n"
        response += f"• {format_time_range(alt_start_2, alt_end_2)} no {studio.name}\n"
        response += f"• {format_time_range(alt_start_3, alt_end_3)} no {studio.name} (dia seguinte)\n\n"
        
        # Sugestões de outras unidades
        if available_studios:
            response += "🏢 *Outras unidades disponíveis neste mesmo horário:*\n"
            for avail_studio in available_studios:
                response += f"• {avail_studio.name}\n"
            response += "\nGostaria que eu agendasse em alguma dessas opções?"
        else:
            response += "Não há outras unidades disponíveis neste horário. Gostaria que eu agendasse em algum dos horários alternativos sugeridos?"
        
        return {
            "response_type": "text",
            "content": response
        }
    
    # Criar o evento
    try:
        # Como não temos SessionType, vamos usar o event_type do modelo Event
        
        # Criar o evento
        event = Event(
            title=session_title,
            start_time=start_datetime,
            end_time=end_datetime,
            location=studio,  # Alteração: studio para location
            event_type='CLASS',  # Usando um tipo padrão
            description=f"Agendamento via assistente: {query}",
            status='SCHEDULED'
        )
        
        # Tentar obter um usuário professor para associar ao evento (requisito do modelo)
        professor = User.objects.filter(user_type='PROFESSOR').first()
        if professor:
            event.professor = professor
        else:
            return {
                "response_type": "text",
                "content": "Não foi possível criar o agendamento: nenhum professor disponível no sistema."
            }
        
        # Associar ao curso, se especificado
        if course_info:
            course, _ = course_info
            event.course = course
        
        event.save()
        
        # Adicionar participantes, se especificados
        if participants_info:
            for participant, _ in participants_info:
                EventParticipant.objects.create(
                    event=event,
                    student=participant,
                    attendance_status="CONFIRMED"  # Usando o valor correto do modelo
                )
        
        # Preparar resposta de confirmação
        participants_str = ""
        if participants_info:
            participant_names = [p[0].first_name for p in participants_info]  # Usando first_name em vez de name
            participants_str = f"\n👥 *Participantes:* {', '.join(participant_names)}"
        
        course_str = ""
        if course_info:
            course_str = f"\n📚 *Curso:* {course_info[0].title}"
        
        # Formatar data de forma mais legível
        date_formatted = start_datetime.strftime('%d/%m/%Y')
        weekday_map = {
            0: "Segunda-feira",
            1: "Terça-feira",
            2: "Quarta-feira",
            3: "Quinta-feira",
            4: "Sexta-feira",
            5: "Sábado",
            6: "Domingo"
        }
        weekday = weekday_map.get(start_datetime.weekday(), "")
        
        # Formatar horário de forma padronizada
        start_time = start_datetime.strftime('%H:%M')
        end_time = end_datetime.strftime('%H:%M')
        time_range = f"das {start_time} às {end_time}"
        
        return {
            "response_type": "text",
            "content": f"✅ *Agendamento confirmado com sucesso!*\n\n" +
                      f"🎵 *Atividade:* {session_title}\n" +
                      f"📅 *Data:* {date_formatted} ({weekday})\n" +
                      f"⏰ *Horário:* {time_range}\n" +
                      f"🏢 *Estúdio:* {studio.name}" +
                      course_str +
                      participants_str +
                      f"\n\nTudo pronto para sua sessão! Caso precise reagendar ou cancelar, é só me avisar."
        }
        
    except Exception as e:
        return {
            "response_type": "text",
            "content": f"Erro ao criar agendamento: {str(e)}"
        }

def cancel_studio_booking(query):
    """
    Processa uma solicitação de cancelamento de sessões de estúdio.
    Permite cancelar sessões específicas ou múltiplas sessões com base em critérios como data, horário ou local.
    """
    try:
        from scheduler.models import Event, EventParticipant
        from django.db.models import Q
        from datetime import datetime, timedelta, date
        from django.utils import timezone
        import re
        
        # Lista de palavras-chave que indicam cancelamento
        cancel_words = [
            'cancel', 'cancelar', 'cancele', 'remov', 'remover', 'delet', 'deletar', 'desmarcar',
            'desmarque', 'excluir', 'exclu', 'anular', 'anule', 'cancelament', 'tirar'
        ]
        
        # Verificar se a consulta realmente é sobre cancelamento
        query_lower = query.lower()
        is_cancel_query = any(word in query_lower for word in cancel_words)
        
        if not is_cancel_query:
            return {
                "response_type": "text",
                "content": "Não entendi se você deseja cancelar uma sessão. Por favor, especifique que deseja cancelar e qual sessão (por data, horário ou estúdio)."
            }
        
        # Extrair informações da consulta
        date_time_info = extract_date_time(query)
        studio_info = extract_studio(query)
        
        # Extrair horários específicos mencionados na consulta
        start_hour = None
        end_hour = None
        
        # Padrão para horários como "14h às 16h" ou "14:00 às 16:00"
        time_range_pattern = r'(\d{1,2})(?:h|:00|:\d{2})?\s*(?:às|as|a|até|ate|-)?\s*(\d{1,2})(?:h|:00|:\d{2})?'
        time_range_match = re.search(time_range_pattern, query_lower)
        
        # Padrão para horário único como "14h" ou "14:00"
        single_time_pattern = r'(\d{1,2})(?:h|:00|:\d{2})'
        single_time_match = re.search(single_time_pattern, query_lower)
        
        if time_range_match:
            # Se encontrou um intervalo de horários
            start_hour = int(time_range_match.group(1))
            end_hour = int(time_range_match.group(2))
        elif single_time_match:
            # Se encontrou apenas um horário específico
            specific_hour = int(single_time_match.group(1))
            start_hour = specific_hour
            end_hour = start_hour + 2  # Assumir duração padrão de 2 horas
        
        # Verificar menção a "todas" ou "todos" (ex: "cancele todas as minhas sessões")
        all_sessions_terms = ['todas', 'todos', 'tudo', 'qualquer', 'meus agendamentos', 'minhas sessões']
        all_sessions = any(term in query_lower for term in all_sessions_terms)
        
        # Verificar padrões específicos que indicam cancelamento de todas as sessões
        all_sessions_patterns = [
            'todas as sessões', 'todos os agendamentos', 'todas as aulas',
            'desmarque todas', 'cancele todas', 'remova todas',
            'meus agendamentos', 'minhas sessões'
        ]
        
        # Verificação específica para o padrão problemático
        if 'todas as sessões de estudio' in query_lower or 'todas as sessões do estudio' in query_lower:
            all_sessions = True
            
        # Verificar por outras variações do padrão
        for pattern in all_sessions_patterns:
            if pattern in query_lower:
                all_sessions = True
                break
        
        # Verificar menção a dias da semana
        weekdays = {
            'segunda': 0, 'segunda-feira': 0, 'seg': 0,
            'terça': 1, 'terca': 1, 'terça-feira': 1, 'ter': 1,
            'quarta': 2, 'quarta-feira': 2, 'qua': 2,
            'quinta': 3, 'quinta-feira': 3, 'qui': 3,
            'sexta': 4, 'sexta-feira': 4, 'sex': 4,
            'sábado': 5, 'sabado': 5, 'sab': 5,
            'domingo': 6, 'dom': 6
        }
        
        # Procurar menções a dias da semana
        mentioned_weekday = None
        for day, day_num in weekdays.items():
            if day in query_lower:
                mentioned_weekday = day_num
                break
        
        # Construir a consulta base - eventos futuros não cancelados
        today = timezone.now().date()
        current_time = timezone.now()
        
        # Obter usuário professor atual
        from core.models import User
        current_user = User.objects.filter(user_type='PROFESSOR').first()
        
        if not current_user:
            return {
                "response_type": "text",
                "content": "Não foi possível identificar o professor atual. Por favor, entre em contato com o suporte."
            }
        
        # Filtrar eventos futuros do professor atual que não estejam cancelados
        base_query = Q(
            professor=current_user,
            status__in=['SCHEDULED', 'CONFIRMED']
        )
        
        # Se solicitou cancelar todas as sessões
        if all_sessions:
            # Não aplicar mais filtros adicionais além dos básicos
            pass
        # Adicionar filtros específicos de data/hora/estúdio se fornecidos
        else:
            # Filtrar por data específica se fornecida
            if date_time_info:
                target_datetime, _ = date_time_info
                target_date = target_datetime.date()
                
                # Filtrar por data específica
                start_of_day = datetime.combine(target_date, datetime.min.time())
                start_of_day = timezone.make_aware(start_of_day)
                end_of_day = datetime.combine(target_date, datetime.max.time())
                end_of_day = timezone.make_aware(end_of_day)
                
                base_query &= Q(start_time__gte=start_of_day, start_time__lte=end_of_day)
                
                # Se também temos horários específicos, filtrar por eles
                if start_hour is not None:
                    # Se temos hora de início e fim, filtrar eventos que se sobrepõem a esse período
                    if end_hour is not None:
                        # Eventos que começam dentro do intervalo especificado
                        hour_query = Q(start_time__hour__gte=start_hour, start_time__hour__lt=end_hour)
                        # Eventos que terminam dentro do intervalo especificado
                        hour_query |= Q(end_time__hour__gt=start_hour, end_time__hour__lte=end_hour)
                        # Eventos que englobam completamente o intervalo especificado
                        hour_query |= Q(start_time__hour__lte=start_hour, end_time__hour__gte=end_hour)
                        
                        base_query &= hour_query
                    else:
                        # Se temos apenas hora de início, filtrar eventos que começam nessa hora
                        base_query &= Q(start_time__hour=start_hour)
            
            elif mentioned_weekday is not None:
                # Se mencionou um dia da semana, encontrar a próxima ocorrência desse dia
                days_ahead = (mentioned_weekday - today.weekday()) % 7
                if days_ahead == 0:
                    # Se for o mesmo dia da semana, verificar se já passou do horário atual
                    if current_time.hour >= 20:  # Após às 20h, considerar a próxima semana
                        days_ahead = 7
                
                next_occurrence = today + timedelta(days=days_ahead)
                
                start_of_day = datetime.combine(next_occurrence, datetime.min.time())
                start_of_day = timezone.make_aware(start_of_day)
                end_of_day = datetime.combine(next_occurrence, datetime.max.time())
                end_of_day = timezone.make_aware(end_of_day)
                
                base_query &= Q(start_time__gte=start_of_day, start_time__lte=end_of_day)
                
                # Se também temos horários específicos, filtrar por eles
                if start_hour is not None:
                    if end_hour is not None:
                        # Filtrar eventos que se sobrepõem ao intervalo de horas
                        hour_query = Q(start_time__hour__gte=start_hour, start_time__hour__lt=end_hour)
                        hour_query |= Q(end_time__hour__gt=start_hour, end_time__hour__lte=end_hour)
                        hour_query |= Q(start_time__hour__lte=start_hour, end_time__hour__gte=end_hour)
                        
                        base_query &= hour_query
                    else:
                        # Filtrar eventos que começam nessa hora específica
                        base_query &= Q(start_time__hour=start_hour)
            
            elif start_hour is not None:
                # Se temos apenas horários mas não data específica, considerar qualquer data futura
                if end_hour is not None:
                    # Filtrar eventos que se sobrepõem ao intervalo de horas
                    hour_query = Q(start_time__hour__gte=start_hour, start_time__hour__lt=end_hour)
                    hour_query |= Q(end_time__hour__gt=start_hour, end_time__hour__lte=end_hour)
                    hour_query |= Q(start_time__hour__lte=start_hour, end_time__hour__gte=end_hour)
                    
                    base_query &= hour_query
                else:
                    # Filtrar eventos que começam nessa hora específica
                    base_query &= Q(start_time__hour=start_hour)
        
        # Adicionar filtro por estúdio, se especificado
        if studio_info:
            studio, studio_id = studio_info
            base_query &= Q(location=studio)
        
        # Buscar os eventos que correspondem aos critérios
        events_to_cancel = Event.objects.filter(base_query).order_by('start_time')
        
        # Verificar se encontrou algum evento
        if not events_to_cancel.exists():
            return {
                "response_type": "text",
                "content": "Não encontrei nenhuma sessão agendada que corresponda aos critérios informados. Verifique se a data, horário ou estúdio estão corretos."
            }
        
        # Limite para exibição na confirmação (se cancelar muitos eventos)
        display_limit = 5
        total_events = events_to_cancel.count()
        
        # Formatar informações para confirmação
        events_info = []
        for event in events_to_cancel[:display_limit]:
            weekday = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][event.start_time.weekday()]
            date_str = event.start_time.strftime('%d/%m/%Y')
            time_str = f"{event.start_time.strftime('%H:%M')} às {event.end_time.strftime('%H:%M')}"
            studio_name = event.location.name if event.location else "Sem local definido"
            
            events_info.append(f"• **{event.title}** - {weekday}, {date_str} - {time_str} - {studio_name}")
        
        # Se há mais eventos do que o limite de exibição, adicionar uma nota
        if total_events > display_limit:
            events_info.append(f"• _E mais {total_events - display_limit} sessões..._")
        
        # Atualizar o status dos eventos para 'CANCELLED'
        for event in events_to_cancel:
            event.status = 'CANCELLED'
            event.save()
            
            # Também atualizar o status dos participantes
            EventParticipant.objects.filter(event=event).update(attendance_status='CANCELLED')
        
        # Mensagem de sucesso
        if total_events == 1:
            success_message = "✅ Sessão cancelada com sucesso!\n\n"
        else:
            success_message = f"✅ {total_events} sessões canceladas com sucesso!\n\n"
        
        success_message += "As seguintes sessões foram canceladas:\n\n"
        success_message += "\n".join(events_info)
        success_message += "\n\nSe desejar reagendar alguma dessas sessões, basta me informar."
        
        return {
            "response_type": "text",
            "content": success_message
        }
        
    except Exception as e:
        return {
            "response_type": "text",
            "content": f"Ocorreu um erro ao processar sua solicitação de cancelamento: {str(e)}"
        }

def extract_date_time(query):
    """
    Extrai data e hora da consulta do usuário.
    Retorna uma tupla (datetime, timezone) ou None se não encontrado.
    """
    query_lower = query.lower()
    
    # Padrões de data (dd/mm/yyyy, dd/mm, dd de mês)
    date_patterns = [
        r'(\d{1,2})[/\-\.](\d{1,2})(?:[/\-\.](\d{2,4}))?',  # dd/mm/yyyy ou dd/mm
        r'(\d{1,2}) de (janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)(?: de (\d{2,4}))?',  # dd de mês de yyyy
        r'(hoje|amanhã|depois de amanhã)',  # palavras-chave de data relativa
        r'próxima (segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)',  # próximo dia da semana
        r'(segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)(?:-feira)?'  # dia da semana sem "próxima"
    ]
    
    # Padrões de hora (hh:mm, hh h, meio-dia, etc)
    time_patterns = [
        r'(\d{1,2}):(\d{2})',  # hh:mm
        r'(\d{1,2})h(?:(\d{2}))?',  # hh h ou hh h mm
        r'(meio[- ]dia)',  # meio-dia
        r'(\d{1,2}) horas',  # hh horas
        r'(\d{1,2}) da (manhã|tarde|noite)'  # hh da manhã/tarde/noite
    ]
    
    # Extrair data
    date_str = None
    match_date = None
    
    for pattern in date_patterns:
        match = re.search(pattern, query_lower)
        if match:
            match_date = match
            break
    
    # Usar django.utils.timezone para obter o datetime atual com timezone
    today = timezone.now().date()
    
    if match_date:
        # Processar com base no padrão que deu match
        if 'hoje' in match_date.group():
            date_obj = today
        elif 'amanhã' in match_date.group() or 'amanha' in match_date.group():
            date_obj = today + timedelta(days=1)
        elif 'depois de amanhã' in match_date.group() or 'depois de amanha' in match_date.group():
            date_obj = today + timedelta(days=2)
        elif 'próxima' in match_date.group() or any(day in match_date.group() for day in ['segunda', 'terça', 'terca', 'quarta', 'quinta', 'sexta', 'sábado', 'sabado', 'domingo']):
            # Mapear dia da semana para número (0 = segunda, 6 = domingo)
            weekday_map = {
                'segunda': 0, 'terça': 1, 'terca': 1, 'quarta': 2, 
                'quinta': 3, 'sexta': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6
            }
            
            # Extrair o dia da semana independentemente se tem "próxima" ou não
            day_str = match_date.group(1) if 'próxima' in match_date.group() else match_date.group(0)
            
            target_weekday = None
            for key, value in weekday_map.items():
                if key in day_str:
                    target_weekday = value
                    break
            
            if target_weekday is not None:
                # Calcular dias até o próximo dia da semana
                days_ahead = target_weekday - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                
                date_obj = today + timedelta(days=days_ahead)
            else:
                # Se não conseguiu mapear o dia da semana, usar hoje como padrão
                date_obj = today
        elif 'de' in match_date.group():
            # Formato "dd de mês"
            day = int(match_date.group(1))
            
            # Mapear nome do mês para número
            month_map = {
                'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 
                'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7, 
                'agosto': 8, 'setembro': 9, 'outubro': 10, 
                'novembro': 11, 'dezembro': 12
            }
            
            month_str = match_date.group(2)
            month = month_map.get(month_str, today.month)
            
            year = int(match_date.group(3)) if match_date.group(3) else today.year
            # Ajustar ano de 2 dígitos
            if year < 100:
                year += 2000
            
            date_obj = datetime(year, month, day).date()
        else:
            # Formato dd/mm/yyyy ou dd/mm
            day = int(match_date.group(1))
            month = int(match_date.group(2))
            year = int(match_date.group(3)) if match_date.group(3) else today.year
            
            # Ajustar ano de 2 dígitos
            if year < 100:
                year += 2000
            
            date_obj = datetime(year, month, day).date()
    else:
        # Se não encontrou data, usar hoje como padrão
        date_obj = today
    
    # Extrair hora
    # Usar timezone.now() para obter horário com timezone
    time_obj = timezone.now().time()  # Padrão: hora atual
    
    for pattern in time_patterns:
        match = re.search(pattern, query_lower)
        if match:
            if 'meio-dia' in match.group() or 'meio dia' in match.group():
                hour = 12
                minute = 0
            elif 'da' in match.group():
                hour = int(match.group(1))
                minute = 0
                period = match.group(2)
                
                # Ajustar para formato 24h
                if period == 'tarde' and hour < 12:
                    hour += 12
                elif period == 'noite' and hour < 12:
                    hour += 12
            else:
                hour = int(match.group(1))
                # Se tiver minutos no padrão
                minute = int(match.group(2)) if match.group(2) else 0
            
            time_obj = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
            break
    
    # Combinar data e hora
    datetime_naive = datetime.combine(date_obj, time_obj)
    
    # Aplicar timezone usando django.utils.timezone
    timezone_name = 'America/Sao_Paulo'  # Padrão para Brasil
    timezone_obj = pytz.timezone(timezone_name)
    datetime_aware = timezone.make_aware(datetime_naive, timezone=timezone_obj)
    
    return (datetime_aware, timezone_name)

def extract_studio(query):
    """
    Identifica o estúdio mencionado na consulta.
    Retorna uma tupla (objeto do estúdio, id do estúdio) ou None se não encontrado.
    """
    query_lower = query.lower()
    
    # Buscar todos os estúdios ativos no banco de dados
    studios = Studio.objects.filter(is_active=True)
    
    # Mapeamento de nomes simplificados para os nomes completos
    studio_aliases = {
        'barra': 'School of Rock - Barra da Tijuca',
        'tijuca': 'School of Rock - Barra da Tijuca',
        'ipanema': 'School of Rock - Ipanema',
        'botafogo': 'School of Rock - Botafogo',
        'centro': 'School of Rock - Centro'
    }
    
    # Verificar primeiro os aliases simplificados
    for alias, full_name in studio_aliases.items():
        if alias in query_lower:
            for studio in studios:
                if studio.name == full_name:
                    return (studio, studio.id)
    
    # Se não encontrou por alias, verificar pelo nome completo
    for studio in studios:
        # Verificar se o nome do estúdio está na consulta
        if studio.name.lower() in query_lower:
            return (studio, studio.id)
    
    # Se mencionou a palavra "estúdio" mas não especificou qual, pegar o primeiro
    studio_keywords = ['estúdio', 'estudio', 'sala', 'espaço', 'espaco']
    if any(keyword in query_lower for keyword in studio_keywords):
        if studios.exists():
            studio = studios.first()
            return (studio, studio.id)
    
    return None

def extract_session_title(query):
    """
    Extrai o título ou propósito da sessão a partir da consulta.
    """
    query_lower = query.lower()
    
    # Lista de palavras e frases para filtrar do título
    filter_words = [
        'mim', 'me', 'eu', 'nos', 'nós', 'a gente', 'para mim', 'para nós', 
        'para essa', 'para esta', 'nessa', 'nesta', 'dessa', 'desta',
        'hoje', 'amanhã', 'depois', 'próxima', 'proxima', 'seguinte',
        'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo',
        'de manhã', 'à tarde', 'à noite', 'às', 'as', 'no dia', 'na data',
        'para', 'do', 'da', 'dos', 'das', 'no', 'na', 'nos', 'nas'
    ]
    
    # Padrões para identificar o título/propósito
    title_patterns = [
        r'sess[ãa]o\s+(?:de|para)\s+(.*?)(?:no dia|às|as|no estúdio|no estudio|com|por|durante|na unidade)',
        r'aula\s+(?:de|para)\s+(.*?)(?:no dia|às|as|no estúdio|no estudio|com|por|durante|na unidade)',
        r'marcar\s+(?:uma\s+)?(?:aula|sessão|sessao)\s+(?:de|para)\s+(.*?)(?:no dia|às|as|no estúdio|no estudio|com|por|durante|na unidade)',
        r'título[:\s]+([^,.]+)',
        r'titulo[:\s]+([^,.]+)',
        r'tema[:\s]+([^,.]+)',
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, query_lower)
        if match:
            title = match.group(1).strip()
            # Filtrar palavras indesejadas
            for word in filter_words:
                title = re.sub(r'\b' + re.escape(word) + r'\b', '', title)
            
            # Limpar múltiplos espaços e espaços no início/fim
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Se sobrou algo significativo, usar como título
            if len(title) > 2:  # Pelo menos 3 caracteres
                return title.capitalize()
            # Se não sobrou nada significativo, continuar procurando
    
    # Palavras comuns que podem indicar o tipo de sessão
    session_types = {
        'gravação': 'Sessão de Gravação',
        'gravacao': 'Sessão de Gravação',
        'mixagem': 'Sessão de Mixagem',
        'mixar': 'Sessão de Mixagem',
        'masterização': 'Sessão de Masterização',
        'masterizacao': 'Sessão de Masterização',
        'aula': 'Aula',
        'violão': 'Aula de Violão',
        'violao': 'Aula de Violão',
        'guitarra': 'Aula de Guitarra',
        'bateria': 'Aula de Bateria',
        'piano': 'Aula de Piano',
        'canto': 'Aula de Canto',
        'ensaio': 'Ensaio',
        'produção': 'Sessão de Produção',
        'producao': 'Sessão de Produção',
        'reunião': 'Reunião',
        'reuniao': 'Reunião',
    }
    
    for keyword, title in session_types.items():
        if keyword in query_lower:
            # Se encontrou uma palavra-chave, verificar se há contexto adicional
            context_match = re.search(f"{keyword} (?:de|para) ([^,.]+)", query_lower)
            if context_match:
                context = context_match.group(1).strip()
                # Filtrar palavras indesejadas do contexto
                for word in filter_words:
                    context = re.sub(r'\b' + re.escape(word) + r'\b', '', context)
                
                # Limpar múltiplos espaços e espaços no início/fim
                context = re.sub(r'\s+', ' ', context).strip()
                
                # Se sobrou algo significativo, usar como contexto
                if len(context) > 2:  # Pelo menos 3 caracteres
                    return f"{title}: {context.capitalize()}"
            return title
    
    # Default
    return "Sessão de Estúdio"

def extract_duration(query):
    """
    Extrai a duração da sessão em minutos a partir da consulta.
    Se for especificado um horário de início e fim, calcula a duração.
    """
    query_lower = query.lower()
    
    # Primeiro, verificar se há horário de início e fim especificados
    start_end_pattern = r'(\d{1,2})h(?:(\d{2}))?(?:\s*(?:às|as|ate|até)\s*)(\d{1,2})h(?:(\d{2}))?'
    match = re.search(start_end_pattern, query_lower)
    if match:
        start_hour = int(match.group(1))
        start_min = int(match.group(2) or 0)
        end_hour = int(match.group(3))
        end_min = int(match.group(4) or 0)
        
        # Ajustar para lidar com períodos que atravessam a meia-noite
        if end_hour < start_hour:
            end_hour += 24
        
        # Converter para minutos e calcular a diferença
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        duration = end_minutes - start_minutes
        
        # Verificar se a duração faz sentido (entre 15 minutos e 8 horas)
        if 15 <= duration <= 480:
            return duration
    
    # Padrões de duração explícita
    duration_patterns = [
        r'(\d+) hora[s]?',
        r'(\d+)h',
        r'(\d+) minuto[s]?',
        r'(\d+)min',
        r'(\d+):(\d+)',  # formato h:mm
        r'(\d+) hora[s]? e (\d+) minuto[s]?',
    ]
    
    for pattern in duration_patterns:
        match = re.search(pattern, query_lower)
        if match:
            if 'minuto' in pattern or 'min' in pattern:
                return int(match.group(1))
            elif 'hora' in pattern or 'h' in pattern and 'minuto' not in pattern:
                return int(match.group(1)) * 60
            elif ':' in pattern:
                return int(match.group(1)) * 60 + int(match.group(2))
            elif 'hora' in pattern and 'minuto' in pattern:
                return int(match.group(1)) * 60 + int(match.group(2))
    
    # Duração padrão: 1 hora
    return 60

def extract_course(query):
    """
    Identifica o curso mencionado na consulta.
    Retorna uma tupla (objeto do curso, id do curso) ou None se não encontrado.
    """
    query_lower = query.lower()
    
    # Buscar todos os cursos ativos
    courses = Course.objects.filter(status='ACTIVE')
    
    for course in courses:
        if course.title.lower() in query_lower:
            return (course, course.id)
    
    # Verificar palavras-chave gerais de curso
    course_keywords = ['curso', 'aula', 'disciplina', 'matéria', 'materia']
    if any(keyword in query_lower for keyword in course_keywords):
        # Se mencionou curso mas não especificou qual, tentar extrair mais contexto
        common_courses = {
            'teoria': 'Teoria Musical',
            'piano': 'Piano',
            'violão': 'Violão',
            'violao': 'Violão',
            'guitarra': 'Guitarra',
            'bateria': 'Bateria',
            'canto': 'Canto',
            'produção': 'Produção Musical',
            'producao': 'Produção Musical',
        }
        
        for keyword, course_name in common_courses.items():
            if keyword in query_lower:
                # Buscar curso pelo nome
                course = Course.objects.filter(title__icontains=course_name).first()
                if course:
                    return (course, course.id)
    
    return None

def extract_participants(query):
    """
    Extrai os alunos mencionados na consulta.
    Retorna uma lista de tuplas (objeto do aluno, id do aluno) ou lista vazia se nenhum for encontrado.
    """
    query_lower = query.lower()
    
    # Buscar todos os alunos ativos (adaptado para usar User em vez de Student)
    active_students = User.objects.filter(user_type='STUDENT', is_active=True)
    participants = []
    
    # Verificar cada aluno
    for student in active_students:
        # Verificar nome completo ou primeiro nome
        full_name = f"{student.first_name} {student.last_name}".lower()
        if full_name in query_lower:
            participants.append((student, student.id))
            continue
        
        # Verificar apenas o primeiro nome
        first_name = student.first_name.lower() if student.first_name else ""
        if first_name and first_name in query_lower.split():
            participants.append((student, student.id))
    
    return participants
