#!/bin/bash

# Definir porta padrão
PORT=8000

# Mensagem de cabeçalho
echo "===== Iniciando Servidor CincoCincoJAM 2.0 ====="
echo "Porta: $PORT"

# Função para verificar se um pacote Python está instalado
check_package() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

# Verificar se Django está instalado
echo "🔍 Verificando dependências principais..."
if ! check_package "django"; then
    echo "🚨 Django não está instalado!"
    echo "📦 Instalando Django..."
    python3 -m pip install django
    
    # Verificar novamente
    if ! check_package "django"; then
        echo "❌ ERRO: Não foi possível instalar o Django. Você está em um ambiente virtual?"
        echo "Tente ativar um ambiente virtual ou instalar Django manualmente:"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate  # No Windows: venv\Scripts\activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
fi

# Verificar dependências pendentes
echo "🔍 Instalando todas as dependências do requirements.txt..."
pip_command="python3 -m pip"
$pip_command install -r requirements.txt

# Verificar dependências adicionais não listadas no requirements.txt
echo "🔍 Verificando dependências adicionais..."

# Verifica django-environ
if ! check_package "environ"; then
    echo "📦 Instalando django-environ (dependência necessária)..."
    $pip_command install django-environ
fi

# Verifica openai - precisa ser uma versão específica que suporte 'from openai import OpenAI'
if ! python3 -c "from openai import OpenAI" 2>/dev/null; then
    echo "📦 Instalando versão compatível do OpenAI (dependência necessária)..."
    # Desinstalar qualquer versão existente primeiro
    $pip_command uninstall -y openai 2>/dev/null
    # Instalar versão específica (0.27.0 ou superior que tenha suporte para 'from openai import OpenAI')
    $pip_command install "openai>=1.0.0"
fi

# Verificar e aplicar migrations pendentes
echo "🔄 Verificando migrations pendentes..."
python3 manage.py showmigrations --list 2>/dev/null
migration_check=$?

if [ $migration_check -ne 0 ]; then
    echo "🚨 Erro ao verificar migrations. Verificando se há outros problemas..."
else
    echo "🔄 Aplicando migrations pendentes..."
    python3 manage.py migrate
    
    if [ $? -eq 0 ]; then
        echo "✅ Migrations aplicadas com sucesso!"
    else
        echo "🚨 Erro ao aplicar migrations. Verifique os erros acima."
    fi
fi

# Verificar se há processos usando a porta
echo "🔍 Verificando se a porta $PORT está em uso..."
PID=$(lsof -ti :$PORT)

# Se encontrar algum processo, mata
if [ ! -z "$PID" ]; then
    echo "🔴 Processo $PID encontrado usando a porta $PORT"
    echo "🔄 Encerrando processo anterior..."
    kill -9 $PID
    echo "✅ Processo encerrado!"
fi

# Iniciar o servidor Django
echo "🚀 Iniciando o servidor Django..."
python3 manage.py runserver $PORT
