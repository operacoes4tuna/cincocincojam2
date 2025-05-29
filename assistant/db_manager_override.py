"""
Módulo para garantir acesso irrestrito ao banco de dados para o assistente virtual
"""
import logging
from django.db import connection
import json

logger = logging.getLogger(__name__)

def execute_raw_sql(query):
    """
    Executa uma consulta SQL diretamente no banco de dados sem restrições
    
    Args:
        query: String contendo a consulta SQL a ser executada
        
    Returns:
        Lista de dicionários com os resultados da consulta
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            # Se for uma consulta SELECT que retorna resultados
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                return [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
            # Se for uma consulta que não retorna resultados (INSERT, UPDATE, etc)
            else:
                return {"status": "success", "affected_rows": cursor.rowcount}
    except Exception as e:
        logger.error(f"Erro ao executar SQL: {str(e)}")
        return {"error": str(e)}

def get_all_tables():
    """
    Retorna a lista de todas as tabelas no banco de dados
    
    Returns:
        Lista com os nomes de todas as tabelas
    """
    query = """
    SELECT name FROM sqlite_master 
    WHERE type='table' 
    ORDER BY name;
    """
    return execute_raw_sql(query)

def get_table_info(table_name):
    """
    Retorna informações sobre a estrutura de uma tabela
    
    Args:
        table_name: Nome da tabela
        
    Returns:
        Lista de colunas e seus tipos
    """
    query = f"PRAGMA table_info({table_name});"
    return execute_raw_sql(query)

def get_table_data(table_name, limit=100):
    """
    Retorna todos os dados de uma tabela
    
    Args:
        table_name: Nome da tabela
        limit: Número máximo de registros a retornar
        
    Returns:
        Lista com todos os registros da tabela
    """
    query = f"SELECT * FROM {table_name} LIMIT {limit};"
    return execute_raw_sql(query)

def get_best_customer():
    """
    Identifica o melhor cliente com base no valor total de compras
    
    Returns:
        Dicionário com informações do melhor cliente
    """
    query = """
    SELECT 
        u.id, 
        u.username, 
        u.email, 
        u.first_name, 
        u.last_name, 
        COUNT(p.id) as total_purchases, 
        SUM(p.amount) as total_spent
    FROM 
        core_user u
    JOIN 
        payments_paymenttransaction p ON u.id = p.user_id
    WHERE 
        p.status = 'PAID'
    GROUP BY 
        u.id
    ORDER BY 
        total_spent DESC
    LIMIT 1;
    """
    return execute_raw_sql(query)

def get_all_payments():
    """
    Retorna todos os pagamentos do sistema
    
    Returns:
        Lista com todos os pagamentos
    """
    query = """
    SELECT 
        p.id, 
        p.transaction_id, 
        p.status, 
        p.amount, 
        p.payment_method, 
        p.created_at, 
        p.updated_at,
        u.username as user_name,
        u.email as user_email,
        c.title as course_title
    FROM 
        payments_paymenttransaction p
    LEFT JOIN 
        core_user u ON p.user_id = u.id
    LEFT JOIN
        courses_enrollment e ON p.enrollment_id = e.id
    LEFT JOIN
        courses_course c ON e.course_id = c.id
    ORDER BY 
        p.created_at DESC;
    """
    return execute_raw_sql(query)

def get_all_users():
    """
    Retorna todos os usuários do sistema
    
    Returns:
        Lista com todos os usuários
    """
    query = """
    SELECT 
        id, 
        username, 
        email, 
        first_name, 
        last_name, 
        is_active, 
        date_joined,
        user_type
    FROM 
        core_user
    ORDER BY 
        date_joined DESC;
    """
    return execute_raw_sql(query)
