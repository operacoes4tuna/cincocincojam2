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
    export PGPASSWORD=$DB_PASSWORD
    psql -d $DB_NAME -h $DB_HOST -U $DB_USER -c "CREATE SCHEMA IF NOT EXISTS public;"
    psql -d $DB_NAME -h $DB_HOST -U $DB_USER -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
    psql -d $DB_NAME -h $DB_HOST -U $DB_USER -c "ALTER DATABASE $DB_NAME SET search_path TO public;"
    unset PGPASSWORD
fi

# Executar migrações
python manage.py migrate

# Criar usuários iniciais em todos os ambientes para teste inicial
python manage.py create_default_users 