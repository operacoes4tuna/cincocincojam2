# Correção do Assistente IA - Erro de Chave API

## Problema Identificado

O erro que está ocorrendo com o assistente IA é devido a um problema de autenticação com a API OpenAI. Os logs mostram claramente:

```
Erro ao chamar a API: Error code: 401 - {'error': {'message': 'Incorrect API key provided: YOUR_OPENAI_API_KEY_GOES_HERE You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'param': None, 'code': 'invalid_api_key'}}
```

## Causa do Problema

A chave API que está configurada no arquivo `.env` está no formato `YOUR_OPENAI_API_KEY_GOES_HERE` que não é compatível com a API da OpenAI. As chaves da OpenAI começam com `sk-` seguido por caracteres alfanuméricos, mas não seguem o padrão `YOUR_OPENAI_API_KEY_GOES_HERE`.

A chave atual no formato `YOUR_OPENAI_API_KEY_GOES_HERE` parece ser de algum outro serviço ou um formato próprio, não da OpenAI.

## Solução

Para corrigir o problema, siga estes passos:

### 1. Obter uma chave API válida da OpenAI

1. Acesse https://platform.openai.com/api-keys
2. Faça login na sua conta OpenAI
3. Clique em "Create new secret key"
4. Adicione uma descrição (ex: "CincoCincoJAM Assistente")
5. Copie a chave gerada (ela começará com `sk-` mas não terá o formato `YOUR_OPENAI_API_KEY_GOES_HERE`)

### 2. Atualizar o arquivo `.env`

1. Abra o arquivo `.env` na raiz do projeto
2. Localize a linha com `OPENAI_API_KEY=`
3. Substitua a chave atual pela nova chave que você acabou de criar
4. Mantenha as outras configurações conforme estão (modelo, tokens, temperatura)

Exemplo de como deve ficar:
```
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_GOES_HERE
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=150
OPENAI_TEMPERATURE=0.7
```

### 3. Reiniciar o servidor Django

1. Pare o servidor atual (Ctrl+C no terminal onde está rodando)
2. Inicie o servidor novamente: `python manage.py runserver`

### 4. Verificar se o problema foi resolvido

1. Acesse a aplicação e teste o assistente
2. Se ainda houver problemas, verifique os logs em `logs/assistant.log`

## Observações Importantes

- A API da OpenAI é um serviço pago. Certifique-se de que sua conta tem créditos disponíveis.
- Se sua conta tiver excedido a cota, você verá um erro diferente (429 - insufficient_quota), como já ocorreu no passado (ver logs de 06/04).
- As chaves no formato correto da OpenAI são diferentes das chaves no formato `YOUR_OPENAI_API_KEY_GOES_HERE`.

## Solução alternativa (caso não tenha acesso à API OpenAI)

Se não for possível obter uma chave API válida da OpenAI, você pode implementar uma solução alternativa de resposta padrão no arquivo `assistant/openai_manager.py`, modificando o método `get_response` para sempre usar as respostas diretas do banco de dados. 