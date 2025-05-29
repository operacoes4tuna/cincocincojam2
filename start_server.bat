@echo off
:: Script para iniciar o servidor CincoCincoJAM 2.0 no Windows
setlocal enabledelayedexpansion

:: Definir porta padrão
set PORT=8000

echo ===== Iniciando Servidor CincoCincoJAM 2.0 =====
echo Porta: %PORT%

:: Verificar e matar processos usando a porta
echo Verificando processos na porta %PORT%...
set "PID="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    set "PID=%%p"
)

if defined PID (
    echo Processo %PID% encontrado usando a porta %PORT%
    echo Encerrando processo anterior...
    taskkill /F /PID %PID% > nul 2>&1
    if !errorlevel! equ 0 (
        echo Processo encerrado com sucesso!
    ) else (
        echo Nao foi possivel encerrar o processo.
    )
    timeout /t 2 /nobreak > nul
)

:: Verificar migrações pendentes
echo Verificando migracoes pendentes...
python manage.py showmigrations --list | findstr "\[ \]" > nul
if !errorlevel! equ 0 (
    echo Existem migracoes pendentes.
    set /p apply_migrations="Deseja aplicar as migracoes agora? (s/n): "
    if /i "!apply_migrations!"=="s" (
        echo Aplicando migracoes...
        python manage.py migrate
        echo Migracoes aplicadas com sucesso!
    ) else (
        echo Migracoes nao aplicadas.
    )
) else (
    echo Nenhuma migracao pendente encontrada.
)

:: Iniciar o servidor Django
echo Iniciando o servidor Django...
python manage.py runserver %PORT%
