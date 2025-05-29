# Módulo de Assistente Virtual do CincoCincoJAM

## Integração com OpenAI

O assistente virtual foi integrado com a API da OpenAI para fornecer respostas contextuais e inteligentes aos usuários.

### Configuração

Para utilizar a integração com a OpenAI, é necessário configurar as seguintes variáveis de ambiente:

1. `OPENAI_API_KEY` - Sua chave de API da OpenAI
2. `OPENAI_MODEL` - Modelo a ser utilizado (padrão: "gpt-3.5-turbo")
3. `OPENAI_MAX_TOKENS` - Número máximo de tokens na resposta (padrão: 150)
4. `OPENAI_TEMPERATURE` - Temperatura para geração de respostas (padrão: 0.7)

### Como configurar

1. Crie um arquivo `.env` na raiz do projeto
2. Adicione as variáveis de ambiente conforme o exemplo `.env.example`
3. Reinicie o servidor Django

### Comportamento

O assistente virtual possui as seguintes características:
- Mantém o contexto da conversa ao fornecer respostas
- Fornece respostas educadas e concisas
- Preserva o histórico de mensagens entre navegações
- Interface expansível que mantém seu estado entre páginas
- Indicador visual de "digitando" com três pontos animados

### Próximos passos

- Integração com o banco de dados para respostas baseadas em dados específicos
- Refinamento do comportamento do assistente
- Integração com WhatsApp
