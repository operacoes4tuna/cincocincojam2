#!/bin/bash
# Script para substituir "55Jam" por "55Jam" e "55jam" por "55jam" em todos os arquivos

echo "Iniciando substituição do nome da marca..."

# Lista de arquivos para processar
FILES=$(find . -type f -name "*.html" -o -name "*.py" -o -name "*.md" -o -name "*.css" -o -name "*.sh" -o -name "*.bat" -o -name ".env*" | xargs grep -l "55Jam\|55jam")

# Contador de arquivos processados
COUNT=0

# Processa cada arquivo
for file in $FILES; do
    echo "Processando arquivo: $file"
    # Substitui 55Jam por 55Jam
    sed -i 's/55Jam/55Jam/g' "$file"
    # Substitui 55jam por 55jam
    sed -i 's/55jam/55jam/g' "$file"
    COUNT=$((COUNT+1))
done

echo "Substituição concluída! Processados $COUNT arquivos." 