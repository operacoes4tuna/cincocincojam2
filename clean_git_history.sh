#!/bin/bash
# Script para reescrever o histórico do Git para remover chaves de API da branch feat/teste-deploy
# Mantendo a chave na branch feat/aba-apps-parceiros para a apresentação

set -e  # Encerra o script se qualquer comando falhar

# Cores para melhorar a visualização
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para exibir mensagens com formatação
function print_message() {
    echo -e "${BLUE}$1${NC}"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verifica se estamos no diretório raiz do projeto Git
if [ ! -d ".git" ]; then
    print_error "Erro: Execute este script no diretório raiz do repositório Git."
    exit 1
fi

# Verifica se o script clean_api_key.py existe
if [ ! -f "clean_api_key.py" ]; then
    print_error "Erro: O arquivo clean_api_key.py não foi encontrado."
    print_message "Por favor, crie o arquivo antes de continuar."
    exit 1
fi

# Torna o script clean_api_key.py executável
chmod +x clean_api_key.py

# Salva a branch atual
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
print_message "Branch atual: $CURRENT_BRANCH"

# Verifica se a branch feat/teste-deploy existe
if ! git show-ref --verify --quiet refs/heads/feat/teste-deploy; then
    print_error "Erro: A branch feat/teste-deploy não existe."
    exit 1
fi

# Função para fazer backup do arquivo .env
backup_env_file() {
    if [ -f ".env" ]; then
        print_message "Fazendo backup do arquivo .env..."
        # Substitui a barra (/) por hífen (-) no nome da branch para o nome do arquivo
        SAFE_BRANCH=${CURRENT_BRANCH//\//-}
        cp .env ".env.backup-$(date +%Y%m%d%H%M%S)-$SAFE_BRANCH"
        print_success "Backup criado: .env.backup-$(date +%Y%m%d%H%M%S)-$SAFE_BRANCH"
    fi
}

# Função para restaurar o arquivo .env
restore_env_file() {
    # Substitui a barra (/) por hífen (-) no nome da branch para buscar o backup
    SAFE_BRANCH=${CURRENT_BRANCH//\//-}
    # Encontra o backup mais recente para a branch atual
    local latest_backup=$(ls -t .env.backup-*-$SAFE_BRANCH 2>/dev/null | head -1)
    if [ -n "$latest_backup" ]; then
        print_message "Restaurando arquivo .env a partir de $latest_backup..."
        cp "$latest_backup" .env
        print_success "Arquivo .env restaurado"
    else
        print_warning "Nenhum backup do .env encontrado para restaurar."
    fi
}

# Executa o backup antes de qualquer operação
backup_env_file

echo ""
print_message "===================================================================="
print_warning "ATENÇÃO: Este script vai reescrever o histórico da branch 'feat/teste-deploy'"
print_message "===================================================================="
echo ""
print_warning "Esta é uma operação DESTRUTIVA que NÃO PODE ser desfeita!"
print_message "O script vai:"
print_message "1. Fazer backup do arquivo .env atual"
print_message "2. Mudar para a branch feat/teste-deploy"
print_message "3. Substituir todas as chaves da API por placeholders"
print_message "4. Adicionar um commit com as alterações"
print_message "5. Preparar para o push forçado (que você precisará confirmar manualmente)"
echo ""
print_warning "A branch 'feat/aba-apps-parceiros' NÃO será modificada e manterá a chave da API"
print_warning "funcionando para a sua apresentação."
echo ""
print_message "===================================================================="
read -p "Você quer continuar? (s/n): " CONTINUE

if [ "$CONTINUE" != "s" ]; then
    print_message "Operação cancelada pelo usuário."
    exit 0
fi

echo ""
print_message "Preparando para reescrever o histórico..."

# Verificar se Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    print_error "Erro: Python 3 não encontrado. Instale Python 3 para continuar."
    exit 1
fi

# Cria um arquivo de substituição para o BFG (caso seja usado depois)
print_message "Criando arquivo de configuração para substituição de segredos..."
cat > replace-patterns.txt << 'EOF'
# Padrões de substituição para chaves de API
# Formato: padrão_regex===>substituição
sk-[a-zA-Z0-9]{32,}===>YOUR_OPENAI_API_KEY_GOES_HERE
sk-proj-[a-zA-Z0-9_-]{100,}===>YOUR_OPENAI_API_KEY_GOES_HERE
OPENAI_API_KEY=sk-[^"'\s\n]*===>OPENAI_API_KEY=YOUR_OPENAI_API_KEY_GOES_HERE
EOF
print_success "Arquivo replace-patterns.txt criado"

# Muda para a branch feat/teste-deploy
print_message "Mudando para a branch feat/teste-deploy..."
git checkout feat/teste-deploy
print_success "Agora na branch feat/teste-deploy"

# Executa o script de substituição de chaves
print_message "Executando substituição de chaves de API em arquivos..."
python3 clean_api_key.py
echo ""

# Verifica se há alterações para commitar
if [[ -z $(git status -s) ]]; then
    print_warning "Nenhuma alteração detectada. Nenhuma chave encontrada ou alterações já foram feitas."
else
    print_message "Adicionando alterações ao Git..."
    git add .
    
    print_message "Criando commit com as alterações..."
    git commit -m "Substitui chaves de API por placeholders para segurança"
    print_success "Commit criado com sucesso"
fi

echo ""
print_message "===================================================================="
print_success "Alterações realizadas com sucesso na branch feat/teste-deploy"
print_message "===================================================================="
echo ""
print_message "Para completar o processo, você precisará fazer push forçado para o repositório remoto:"
echo ""
print_message "    git push --force origin feat/teste-deploy"
echo ""
print_warning "IMPORTANTE: NÃO faça push para a branch 'feat/aba-apps-parceiros'!"
print_warning "A branch 'feat/aba-apps-parceiros' deve manter a chave de API para a apresentação."
echo ""

# Restaura a branch original se for diferente
if [ "$CURRENT_BRANCH" != "feat/teste-deploy" ]; then
    print_message "Restaurando a branch original: $CURRENT_BRANCH"
    git checkout "$CURRENT_BRANCH"
    
    # Restaura o arquivo .env original
    restore_env_file
    print_success "Retornado à branch original: $CURRENT_BRANCH"
fi

echo ""
print_message "===================================================================="
print_success "Processo concluído com sucesso!"
print_message "===================================================================="
echo ""
print_message "Para uma limpeza mais profunda do histórico (opcional):"
print_message "1. Instale o BFG Repo-Cleaner (https://rtyley.github.io/bfg-repo-cleaner/)"
print_message "2. Execute: java -jar bfg.jar --replace-text replace-patterns.txt"
print_message "3. Execute: git reflog expire --expire=now --all && git gc --prune=now --aggressive"
print_message "4. Force push: git push --force origin feat/teste-deploy"
echo "" 