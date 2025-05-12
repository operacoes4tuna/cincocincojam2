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
    # Extrair informações da URL do banco de dados
    DB_URL=$(echo $DATABASE_URL | sed 's/postgres:///postgresql:\/\//')
    
    # Criar schema e configurar permissões
    psql "$DB_URL" << EOF
    CREATE SCHEMA IF NOT EXISTS public;
    GRANT ALL ON SCHEMA public TO cincocincojam2;
    ALTER DATABASE cincocincojam2 SET search_path TO public;
EOF
fi

# Executar migrações
python manage.py migrate

# Criar usuários iniciais em todos os ambientes para teste inicial
python manage.py create_default_users 