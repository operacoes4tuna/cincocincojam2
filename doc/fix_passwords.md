# Guia de Correção de Senhas Após Deploy

Se os usuários padrão do sistema estiverem enfrentando problemas de login após o deploy (mensagens de erro indicando que o email ou senha estão incorretos), siga os passos abaixo para redefinir as senhas.

## O problema

Quando o sistema é implantado em produção, pode haver problemas com as senhas pré-configuradas dos usuários padrão. Isso pode ocorrer por vários motivos:

1. Diferenças nas configurações de hashing de senha entre ambientes
2. Carregamento incorreto de fixtures ou dados iniciais
3. Diferenças na configuração de banco de dados

## Solução: Script de Redefinição de Senhas

Foi criado um script de linha de comando que redefine as senhas dos usuários padrão para '123123'. Este script pode ser executado tanto no ambiente local quanto no ambiente de produção.

### Executando o script localmente:

```bash
python reset_users.py
```

### Executando o script no ambiente Render:

1. Acesse o painel de controle do Render
2. Vá para o serviço "cincocincojam2"
3. Clique em "Shell"
4. Execute o comando:
   ```bash
   python reset_users.py
   ```

## Usuários padrão

Após executar o script, os seguintes usuários estarão disponíveis com a senha `123123`:

| Email                | Senha  | Tipo       |
|----------------------|--------|------------|
| admin@55jam.com     | 123123 | Admin      |
| professor@55jam.com | 123123 | Professor  |
| aluno@55jam.com     | 123123 | Aluno      |

## Verificação

O script também realiza uma verificação para garantir que todos os usuários padrão existem no sistema e possuem os tipos corretos. Se algum usuário estiver faltando, recomenda-se verificar o processo de configuração inicial do banco de dados. 