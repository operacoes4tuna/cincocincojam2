"""
Solução temporária para o assistente funcionar sem a API OpenAI.
Crie um arquivo chamado openai_fallback.py no diretório /assistant e adicione este código.
"""

from assistant.db_query import process_db_query, get_financial_data, get_course_students, get_all_students

def get_fallback_response(user_message):
    """
    Função que fornece respostas locais sem depender da API OpenAI.
    Pode ser usada como substituta temporária até que a chave API seja corrigida.
    
    Args:
        user_message: A mensagem enviada pelo usuário
        
    Returns:
        Uma resposta adequada gerada localmente
    """
    # Converter para minúsculas para facilitar a comparação
    message = user_message.lower()
    
    # Verificar se é uma saudação ou mensagem simples
    if any(word in message for word in ['olá', 'oi', 'hey', 'eai', 'e ai', 'bom dia', 'boa tarde', 'boa noite']):
        return """Olá! Sou o assistente virtual da plataforma CincoCincoJAM. Como posso ajudar?
        
Posso fornecer informações sobre:
- Cursos disponíveis
- Matrículas e pagamentos
- Dados financeiros
- Funcionalidades da plataforma

O que você gostaria de saber?"""

    # Verificar se é agradecimento
    if any(word in message for word in ['obrigado', 'obrigada', 'valeu', 'agradeço', 'agradecido']):
        return "Por nada! Estou sempre à disposição para ajudar. Há mais alguma coisa em que eu possa te auxiliar?"
    
    # Verificar se está perguntando sobre cursos
    if any(word in message for word in ['curso', 'cursos', 'aula', 'aulas', 'disciplina']):
        return process_db_query(user_message)
    
    # Verificar se está perguntando sobre finanças
    if any(word in message for word in ['financeiro', 'pagamento', 'dinheiro', 'valor', 'preço', 'faturamento']):
        return get_financial_data()
    
    # Verificar se está perguntando sobre alunos
    if any(word in message for word in ['aluno', 'alunos', 'estudante', 'estudantes', 'cliente', 'clientes']):
        if 'curso' in message:
            # Se mencionar curso, retorna alunos por curso
            return get_course_students()
        else:
            # Senão, retorna todos os alunos
            return get_all_students()
    
    # Resposta padrão para qualquer outra pergunta
    return """Agradeço seu contato. No momento, estou funcionando com recursos limitados devido a uma manutenção na conexão com a API.

Posso ajudar com informações básicas sobre:
- Lista de cursos disponíveis
- Dados financeiros da plataforma
- Informações sobre alunos e matrículas

Para outras perguntas mais específicas, por favor, aguarde até que minha funcionalidade completa seja restaurada. Ou tente reformular sua pergunta focando em um dos tópicos acima."""


# COMO IMPLEMENTAR ESTA SOLUÇÃO:
# 
# 1. Salve este arquivo como 'openai_fallback.py' no diretório /assistant/
# 
# 2. Edite o arquivo /assistant/openai_manager.py e modifique o método get_response para usar esta solução:
# 
# def get_response(self, formatted_messages):
#     """
#     Obtém uma resposta (versão temporária usando fallback local)
#     """
#     # Verifica a última mensagem do usuário
#     user_message = ""
#     for msg in reversed(formatted_messages):
#         if msg.get("role") == "user":
#             user_message = msg.get("content", "")
#             break
#             
#     # Usa a solução de fallback local em vez da API OpenAI
#     from .openai_fallback import get_fallback_response
#     return get_fallback_response(user_message)
# 
# 3. Reinicie o servidor Django
#
# Esta solução vai permitir que o assistente funcione mesmo sem uma chave API válida da OpenAI. 