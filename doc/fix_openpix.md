# Solução para o problema "QR Code não disponível" nos pagamentos PIX

## Problema

Após o deploy da aplicação, ao tentar pagar um curso como aluno, o sistema exibe a mensagem "QR code não disponível" na página de pagamento, impossibilitando o pagamento via PIX.

## Causa

Este problema ocorre devido à falta de configuração ou configuração incorreta do token da API OpenPix no ambiente de produção. Especificamente:

1. O token da API OpenPix (`OPENPIX_TOKEN`) não está definido no ambiente de produção do Render.
2. Embora este token esteja especificado no arquivo `render.yaml`, ele está marcado com a flag `sync: false`, o que significa que precisa ser configurado manualmente no painel do Render.

## Solução

### 1. Obter um token válido da API OpenPix

Se você ainda não tem um token da API OpenPix:

1. Acesse [https://app.openpix.com.br/](https://app.openpix.com.br/)
2. Crie uma conta ou faça login
3. Vá para "Configurações" > "API"
4. Gere um novo token para ambiente de produção

### 2. Configurar o token no Render

1. Acesse o painel do Render
2. Navegue até o serviço "cincocincojam2"
3. Vá para a aba "Environment"
4. Adicione ou edite a variável de ambiente:
   - **Key**: `OPENPIX_TOKEN`
   - **Value**: Cole o token gerado na plataforma OpenPix
5. Clique em "Save Changes"

### 3. Reiniciar o serviço

1. No painel do Render, vá para a aba "Manual Deploy"
2. Clique em "Deploy latest commit" para reiniciar o serviço com a nova configuração

## Verificação

Após reiniciar o serviço:

1. Faça login como aluno (`aluno@55jam.com` com a senha `123123`)
2. Tente comprar um curso
3. Verifique se o QR code é exibido na página de pagamento

## Solução alternativa para testes

Se você precisar apenas testar o sistema sem configurar o OpenPix:

1. Edite o arquivo `.env` adicionando:
   ```
   DEBUG_PAYMENTS=True
   ```

2. Isso forçará o sistema a usar o modo de simulação local que gera QR codes fictícios para testes, mesmo em ambiente de produção.

## Suporte técnico

Se o problema persistir, verifique os logs da aplicação no Render para identificar erros específicos relacionados à API OpenPix. O sistema registra informações detalhadas sobre a inicialização do serviço OpenPix e possíveis erros de comunicação com a API. 