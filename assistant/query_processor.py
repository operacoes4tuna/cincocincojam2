"""
Processador de consultas para respostas no chat
Implementa consultas otimizadas baseadas nas diretrizes técnicas fornecidas
"""
from django.db.models import Sum, Count, F, Q, Avg, Max, Min, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

from core.models import User
from courses.models import Course, Lesson, Enrollment
from payments.models import PaymentTransaction
from assistant.advanced_queries import AdvancedQueries

def process_query(query):
    """
    Processa uma consulta do usuário e retorna as informações solicitadas
    Utiliza o módulo AdvancedQueries para obter dados otimizados
    
    Args:
        query: Texto da consulta do usuário
        
    Returns:
        Texto formatado com os resultados da consulta ou None se não identificar o tipo de consulta
    """
    # Normaliza a consulta
    query = query.lower().strip()
    
    # Função auxiliar para detectar correspondência de termos
    def matches_terms(text, terms_list):
        return any(term in text for term in terms_list)
    
    # Sistema de pontuação para classificar o tipo de consulta
    query_scores = {
        'top_students': 0,
        'top_courses': 0,
        'pending_payments': 0,
        'financial': 0,
        'student_search': 0
    }
    
    # === Análise de intenção baseada em palavras-chave ===
    
    # Termos para alunos top/faturamento
    student_revenue_terms = [
        'melhor aluno', 'aluno com maior', 'maior faturamento', 'aluno que mais pagou', 
        'cliente que mais comprou', 'aluno top', 'melhores alunos', 'alunos que mais pagaram'
    ]
    if matches_terms(query, student_revenue_terms):
        query_scores['top_students'] += 3
    
    # Termos para cursos mais vendidos
    top_courses_terms = [
        'curso mais vendido', 'cursos mais vendidos', 'curso mais popular', 
        'mais matrículas', 'cursos populares', 'top cursos', 'ranking de cursos',
        'cursos com mais alunos'
    ]
    if matches_terms(query, top_courses_terms):
        query_scores['top_courses'] += 3
    
    # Termos para pagamentos pendentes
    pending_payments_terms = [
        'pagamentos pendentes', 'não pagos', 'pendente', 'pendência', 'devendo', 
        'inadimplência', 'aguardando pagamento', 'em atraso', 'dívidas'
    ]
    if matches_terms(query, pending_payments_terms):
        query_scores['pending_payments'] += 3
    
    # Termos para dados financeiros gerais
    financial_terms = [
        'financeiro', 'finanças', 'faturamento', 'receita', 'financeira', 'vendas totais',
        'resumo financeiro', 'balanço', 'valores', 'ganhos', 'lucro', 'dinheiro', 'pagamentos'
    ]
    if matches_terms(query, financial_terms):
        query_scores['financial'] += 2  # Peso menor por ser mais genérico
    
    # Termos para busca de aluno específico
    student_search_terms = ['buscar aluno', 'procurar aluno', 'encontrar aluno', 'dados do aluno']
    if matches_terms(query, student_search_terms):
        query_scores['student_search'] += 3
    
    # Pontuação adicional baseada em detalhes específicos na consulta
    if 'maior' in query and ('aluno' in query or 'cliente' in query):
        query_scores['top_students'] += 1
    
    if 'curso' in query and ('vendido' in query or 'popular' in query):
        query_scores['top_courses'] += 1
    
    if 'pendente' in query or 'não pago' in query:
        query_scores['pending_payments'] += 1
    
    # Determinar o tipo de consulta com base na maior pontuação
    query_type = max(query_scores.items(), key=lambda x: x[1])
    
    # Se nenhuma categoria atingiu pontuação mínima, retorna None
    # para permitir que outros processadores tentem interpretar
    if query_type[1] < 1:
        return None
    
    # === Processamento baseado no tipo de consulta identificado ===
    
    if query_type[0] == 'top_students':
        # Determinar limite com base na consulta
        limit = 5
        if 'top 10' in query:
            limit = 10
        elif 'top 3' in query:
            limit = 3
        
        # Executa a consulta otimizada
        result = AdvancedQueries.get_top_students_by_revenue(limit=limit)
        return AdvancedQueries.format_response(result, 'top_students')
    
    elif query_type[0] == 'top_courses':
        # Determinar limite
        limit = 5
        if 'top 10' in query:
            limit = 10
        elif 'top 3' in query:
            limit = 3
        
        # Determinar status das matrículas
        status = 'ACTIVE'
        if 'total' in query or 'todas' in query:
            status = None  # Considerar todas as matrículas
        elif 'completas' in query or 'concluídas' in query:
            status = 'COMPLETED'
        
        # Executa a consulta
        result = AdvancedQueries.get_top_courses_by_enrollment(limit=limit, status=status)
        return AdvancedQueries.format_response(result, 'top_courses')
    
    elif query_type[0] == 'pending_payments':
        result = AdvancedQueries.get_courses_with_pending_payments(limit=10)
        return AdvancedQueries.format_response(result, 'pending_payments')
    
    elif query_type[0] == 'financial':
        result = AdvancedQueries.get_financial_overview()
        return AdvancedQueries.format_response(result, 'financial')
    
    elif query_type[0] == 'student_search':
        # Extrair termo de busca da consulta
        words = query.split()
        ignore_words = ['buscar', 'procurar', 'encontrar', 'aluno', 'cliente', 'estudante', 
                       'sobre', 'informações', 'dados', 'o', 'a', 'os', 'as', 'do', 'da', 'dos', 'das']
        
        search_term = ' '.join([word for word in words if word not in ignore_words]).strip()
        
        if search_term:
            result = AdvancedQueries.search_students(search_term)
            return AdvancedQueries.format_response(result, 'student_search')
        else:
            return "Por favor, especifique um termo de busca para encontrar o aluno."

def extend_advanced_queries():
    """
    Estende a classe AdvancedQueries com métodos adicionais se eles não existirem
    """
    # Verificar se os métodos já existem
    if not hasattr(AdvancedQueries, 'get_financial_overview'):
        @staticmethod
        def get_financial_overview():
            """
            Fornece uma visão geral das finanças da plataforma
            
            Returns:
                Dicionário com estatísticas financeiras
            """
            try:
                # Estatísticas gerais
                transactions = PaymentTransaction.objects.all()
                
                # Pagamentos por status
                paid = transactions.filter(status='PAID')
                pending = transactions.filter(status='PENDING')
                cancelled = transactions.filter(status='CANCELLED')
                
                # Valores totais
                total_revenue = paid.aggregate(Sum('amount'))['amount__sum'] or 0
                pending_amount = pending.aggregate(Sum('amount'))['amount__sum'] or 0
                
                # Estatísticas por período
                today = timezone.now().date()
                last_month = today - timedelta(days=30)
                last_week = today - timedelta(days=7)
                
                # Faturamento por período
                revenue_last_month = paid.filter(
                    created_at__date__gte=last_month
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                revenue_last_week = paid.filter(
                    created_at__date__gte=last_week
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                # Ticket médio
                avg_ticket = paid.aggregate(Avg('amount'))['amount__avg'] or 0
                
                return {
                    'success': True,
                    'financials': {
                        'total_revenue': float(total_revenue),
                        'pending_amount': float(pending_amount),
                        'transactions_count': {
                            'paid': paid.count(),
                            'pending': pending.count(),
                            'cancelled': cancelled.count(),
                            'total': transactions.count()
                        },
                        'period_revenue': {
                            'last_month': float(revenue_last_month),
                            'last_week': float(revenue_last_week)
                        },
                        'avg_ticket': float(avg_ticket)
                    }
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': f"Erro ao obter visão financeira: {str(e)}"
                }
                
        # Adicionar o método à classe
        setattr(AdvancedQueries, 'get_financial_overview', get_financial_overview)
        
    if not hasattr(AdvancedQueries, 'search_students'):
        @staticmethod
        def search_students(query, limit=10):
            """
            Pesquisa alunos por nome, email ou username
            
            Args:
                query: Termo de pesquisa
                limit: Número máximo de resultados
                
            Returns:
                Lista de alunos que correspondem à consulta
            """
            try:
                # Pesquisa por múltiplos campos
                students = User.objects.filter(
                    user_type='STUDENT'
                ).filter(
                    Q(first_name__icontains=query) | 
                    Q(last_name__icontains=query) | 
                    Q(email__icontains=query) | 
                    Q(username__icontains=query)
                )[:limit]
                
                result = []
                for student in students:
                    # Obter matrículas de forma segura
                    enrollments = Enrollment.objects.filter(student=student)
                    
                    # Usar método alternativo para pagamentos
                    total_paid = 0
                    for enrollment in enrollments:
                        try:
                            payments = PaymentTransaction.objects.filter(
                                enrollment=enrollment,
                                status='PAID'
                            )
                            enrollment_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0
                            total_paid += float(enrollment_paid)
                        except:
                            pass
                    
                    result.append({
                        'id': student.id,
                        'nome': f"{student.first_name} {student.last_name}",
                        'email': student.email,
                        'username': student.username,
                        'matriculas': enrollments.count(),
                        'total_pago': total_paid
                    })
                
                return {
                    'success': True,
                    'students': result,
                    'count': len(result)
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': f"Erro na pesquisa de alunos: {str(e)}"
                }
                
        # Adicionar o método à classe
        setattr(AdvancedQueries, 'search_students', search_students)
        
    if not hasattr(AdvancedQueries, 'format_response'):
        @staticmethod
        def format_response(query_data, query_type):
            """
            Formata os resultados das consultas em texto legível
            
            Args:
                query_data: Resultados da consulta
                query_type: Tipo de consulta realizada
                
            Returns:
                Texto formatado para exibição
            """
            if not query_data.get('success', False):
                return f"⚠️ Erro na consulta: {query_data.get('error', 'Erro desconhecido')}"
            
            # Formatação para diferentes tipos de consulta
            if query_type == 'top_students':
                students = query_data.get('students', [])
                result = "# 🏆 Alunos com Maior Faturamento\n\n"
                
                if not students:
                    return result + "Não foram encontrados dados de alunos com pagamentos.\n"
                    
                for i, student in enumerate(students, 1):
                    result += f"**{i}. {student['nome']}**\n"
                    result += f"- Email: {student['email']}\n"
                    result += f"- Total pago: R$ {student['total_pago']:.2f}\n"
                    result += f"- Cursos matriculados: {student['num_cursos']}\n\n"
                    
                return result
            
            elif query_type == 'top_courses':
                courses = query_data.get('courses', [])
                result = "# 📚 Cursos com Mais Matrículas\n\n"
                
                if not courses:
                    return result + "Não foram encontrados dados de cursos com matrículas.\n"
                    
                for i, course in enumerate(courses, 1):
                    result += f"**{i}. {course['titulo']}**\n"
                    result += f"- Professor: {course['professor']}\n"
                    result += f"- Preço: R$ {course['preco']:.2f}\n"
                    result += f"- Matrículas: {course['matriculas']}\n"
                    result += f"- Faturamento: R$ {course['faturamento']:.2f}\n\n"
                    
                return result
            
            elif query_type == 'pending_payments':
                courses = query_data.get('courses', [])
                result = "# ⏳ Cursos com Pagamentos Pendentes\n\n"
                
                if not courses:
                    return result + "Não foram encontrados cursos com pagamentos pendentes.\n"
                    
                for i, course in enumerate(courses, 1):
                    result += f"**{i}. {course['titulo']}**\n"
                    result += f"- Professor: {course['professor']}\n"
                    result += f"- Pagamentos pendentes: {course['pagamentos_pendentes']}\n"
                    result += f"- Valor pendente: R$ {course['valor_pendente']:.2f}\n\n"
                    
                return result
            
            elif query_type == 'financial':
                financials = query_data.get('financials', {})
                result = "# 💰 Resumo Financeiro\n\n"
                
                if not financials:
                    return result + "Não foram encontrados dados financeiros.\n"
                
                result += "## Receita\n"
                result += f"- **Faturamento total**: R$ {financials['total_revenue']:.2f}\n"
                result += f"- **Pagamentos pendentes**: R$ {financials['pending_amount']:.2f}\n"
                result += f"- **Ticket médio**: R$ {financials['avg_ticket']:.2f}\n\n"
                
                result += "## Transações\n"
                result += f"- **Pagas**: {financials['transactions_count']['paid']}\n"
                result += f"- **Pendentes**: {financials['transactions_count']['pending']}\n"
                result += f"- **Canceladas**: {financials['transactions_count']['cancelled']}\n\n"
                
                result += "## Últimos Períodos\n"
                result += f"- **Últimos 30 dias**: R$ {financials['period_revenue']['last_month']:.2f}\n"
                result += f"- **Últimos 7 dias**: R$ {financials['period_revenue']['last_week']:.2f}\n"
                
                return result
            
            elif query_type == 'student_search':
                students = query_data.get('students', [])
                result = "# 🔍 Resultados da Pesquisa\n\n"
                
                if not students:
                    return result + "Nenhum aluno encontrado com esses critérios.\n"
                    
                for i, student in enumerate(students, 1):
                    result += f"**{i}. {student['nome']}**\n"
                    result += f"- Email: {student['email']}\n"
                    result += f"- Username: {student['username']}\n"
                    result += f"- Matrículas: {student['matriculas']}\n"
                    result += f"- Total pago: R$ {student['total_pago']:.2f}\n\n"
                    
                return result
            
            return "Tipo de consulta não reconhecido."
            
        # Adicionar o método à classe
        setattr(AdvancedQueries, 'format_response', format_response)

# Estender a classe ao importar este módulo
extend_advanced_queries()
