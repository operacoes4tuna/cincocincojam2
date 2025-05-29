# Documentação do Deploy no Render - CincoCincoJAM 2.0

Este documento detalha o processo de deploy da plataforma CincoCincoJAM 2.0 no serviço Render, incluindo configurações, etapas realizadas e recursos utilizados.

## 1. Preparação do Projeto para Deploy

**Status: ✅ Implementado**

**Objetivo:** Configurar o projeto Django para execução em ambiente de produção no Render com PostgreSQL.

**Implementação:**
- Criado arquivo `render.yaml` para configuração do serviço e banco de dados
- Atualizado `settings.py` para suportar configurações baseadas em variáveis de ambiente
- Adicionado suporte para PostgreSQL através de `dj-database-url`
- Implementada configuração de whitenoise para servir arquivos estáticos
- Adicionado script `build.sh` para automatizar o processo de deploy

**Recursos Utilizados:**
- WhiteNoise para servir arquivos estáticos
- dj-database-url para configuração dinâmica do banco de dados
- django-environ para gerenciamento de variáveis de ambiente
- Gunicorn como servidor WSGI para produção

## 2. Configuração do Banco de Dados PostgreSQL

**Status: ✅ Implementado**

**Objetivo:** Configurar e utilizar o banco de dados PostgreSQL oferecido pelo Render.

**Implementação:**
- Configurado banco de dados PostgreSQL via render.yaml
- Implementada detecção automática de ambiente para alternar entre SQLite (desenvolvimento) e PostgreSQL (produção)
- Configurados parâmetros de conexão com pool de conexões para melhor desempenho
- Implementadas migrações automáticas durante o processo de deploy

**Configurações:**
```yaml
databases:
  - name: cincocincojam2_db
    databaseName: cincocincojam2
    user: cincocincojam2
    plan: free
```

## 3. Configuração de Variáveis de Ambiente

**Status: ✅ Implementado**

**Objetivo:** Definir e gerenciar variáveis de ambiente seguras para o ambiente de produção.

**Implementação:**
- Configuradas variáveis de ambiente essenciais no render.yaml
- Adicionadas variáveis para APIs externas (OpenAI, OpenPix, etc.)
- Implementado mecanismo de geração automática de SECRET_KEY segura
- Configurada variável RENDER para detecção do ambiente

**Variáveis Configuradas:**
- SECRET_KEY (gerada automaticamente)
- DATABASE_URL (fornecida pelo banco de dados PostgreSQL)
- RENDER (indica ambiente de produção)
- DJANGO_ENVIRONMENT (configurado como "production")
- Chaves de API para serviços externos (OpenAI, OpenPix, FocusNFe, NFE.io)

## 4. Script de Build e Inicialização

**Status: ✅ Implementado**

**Objetivo:** Automatizar o processo de instalação, migração e configuração durante o deploy.

**Implementação:**
- Criado script `build.sh` para automatizar o processo de deploy
- Adicionados comandos para instalação de dependências
- Configurada coleta automática de arquivos estáticos
- Implementada execução automática de migrações
- Adicionada criação automática de usuários padrão para teste

**Componentes do Script:**
```bash
#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalação de dependências
pip install --upgrade pip
pip install -r requirements.txt
pip install whitenoise openai django-environ dj-database-url gunicorn requests

# Criação das pastas necessárias
mkdir -p staticfiles media logs

# Compilar arquivos estáticos
python manage.py collectstatic --no-input

# Executar migrações
python manage.py migrate

# Criar usuários iniciais
python manage.py create_default_users
```

## 5. Configuração para Servir Arquivos Estáticos e Mídia

**Status: ✅ Implementado**

**Objetivo:** Configurar o projeto para servir corretamente arquivos estáticos e mídia no ambiente do Render.

**Implementação:**
- Configurado WhiteNoise para servir arquivos estáticos
- Definida pasta `staticfiles` para armazenamento de arquivos estáticos coletados
- Adicionada configuração para compressão de arquivos estáticos
- Configurada pasta `media` para uploads de usuários

**Configurações:**
```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## Lições Aprendidas e Desafios

1. **Dependências não documentadas:**
   - Algumas dependências como `requests` não estavam explicitamente listadas no requirements.txt
   - Foi necessário identificar e adicionar manualmente estas dependências

2. **Configuração do Webhook OpenPix:**
   - A implementação do webhook para o OpenPix está incompleta e marcada como "para ser implementada posteriormente"
   - A funcionalidade de pagamento via PIX funciona através de polling, sem depender do webhook

3. **Usuários Padrão:**
   - A criação de usuários padrão foi adaptada para funcionar em ambiente de produção
   - Os usuários criados incluem admin, professor e aluno para demonstração

## Próximos Passos

1. **Otimização de performance:**
   - Configurar HTTPS com certificado SSL fornecido pelo Render
   - Implementar cache para reduzir consultas ao banco de dados

2. **Monitoramento:**
   - Configurar serviço de logs e monitoramento
   - Implementar alertas para erros e problemas de performance

3. **Backups:**
   - Configurar backups automáticos do banco de dados PostgreSQL
   - Estabelecer política de retenção de backups

4. **Implementações pendentes:**
   - Completar a implementação do webhook OpenPix
   - Configurar domínio personalizado
   - Implementar página de cadastro para novos usuários 