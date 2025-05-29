#!/usr/bin/env bash
# exit on error
set -o errexit

# Comentário adicional para forçar um novo commit
# Script para build no Render - versão atualizada

# Instalação de dependências
pip install --upgrade pip
pip install -r requirements.txt

# Dependências adicionais necessárias que não estavam no requirements.txt
pip install whitenoise openai django-environ dj-database-url gunicorn requests psycopg2-binary

# Criação das pastas necessárias
mkdir -p staticfiles media logs

# Compilar arquivos estáticos
python manage.py collectstatic --no-input

# Criar schema public se não existir (apenas em produção)
if [ "$RENDER" = "true" ]; then
    echo "Criando schema public no banco de dados..."
    
    # Criar schema e configurar permissões usando Python
    python << EOF
import os
import psycopg2
from urllib.parse import urlparse

# Obter URL do banco de dados
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("DATABASE_URL não encontrada")
    exit(1)

# Conectar ao banco de dados
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

# Executar comandos SQL
cur.execute("CREATE SCHEMA IF NOT EXISTS public;")
cur.execute("GRANT ALL ON SCHEMA public TO cincocincojam2;")
cur.execute("ALTER DATABASE cincocincojam2 SET search_path TO public;")

# Fechar conexão
cur.close()
conn.close()
EOF
fi

# Executar migrações
python manage.py migrate

# Criar usuários iniciais em todos os ambientes para teste inicial
python manage.py create_default_users 