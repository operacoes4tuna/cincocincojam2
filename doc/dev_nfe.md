# Documentação Técnica: Integração com API NFE.io

## Visão Geral

Este documento descreve a integração do CincoCincoJAM com a API NFE.io para emissão de notas fiscais de serviço (NFS-e) para transações realizadas na plataforma. A integração permite que professores emitam automaticamente notas fiscais para os pagamentos recebidos por aulas ministradas.

## Arquitetura da Integração

### Componentes Principais

1. **NFEioService** (`invoices/services.py`): Serviço responsável pela comunicação com a API NFE.io
2. **Invoice** (`invoices/models.py`): Modelo para armazenar informações sobre notas fiscais emitidas
3. **CompanyConfig** (`invoices/models.py`): Configurações da empresa para emissão de notas fiscais
4. **Views** (`invoices/views.py`): Controladores para emissão, verificação e cancelamento de notas

### Configuração do Ambiente

A integração com a NFE.io requer as seguintes variáveis de ambiente:

```
NFEIO_API_KEY=sua_api_key
NFEIO_COMPANY_ID=seu_company_id
NFEIO_ENVIRONMENT=Development ou Production
```

Estas variáveis são definidas no arquivo `.env` e carregadas nas configurações do Django (`config/settings.py`).

## Fluxo de Emissão de Notas Fiscais

### 1. Iniciando a Emissão

A emissão de notas fiscais é iniciada através da view `emit_invoice` em `invoices/views.py`:

1. O usuário (professor) seleciona uma transação para emitir nota fiscal
2. O sistema cria um objeto `Invoice` com status "pending"
3. O sistema chama o método `emit_invoice` do serviço `NFEioService`

### 2. Preparação dos Dados

O método `emit_invoice` do `NFEioService` prepara os dados para envio à API NFE.io:

1. Obtém informações da transação e do estudante
2. Verifica o tipo de pessoa (física ou jurídica) baseado no tamanho do CPF/CNPJ
3. Formata os dados conforme a documentação da API NFE.io
4. Monta o objeto de requisição com todos os campos necessários

### 3. Comunicação com a API

A comunicação com a API é realizada pelo método `_make_request`:

1. Define os cabeçalhos da requisição, incluindo a chave de API
2. Envia a requisição HTTP para o endpoint apropriado
3. Processa a resposta da API

### 4. Verificação de Status

A verificação do status da nota fiscal é realizada através da view `check_invoice_status`:

1. O sistema chama o método `check_invoice_status` do serviço `NFEioService`
2. Obtém o status atual da nota fiscal na API NFE.io
3. Atualiza o objeto `Invoice` com o status e outras informações relevantes

### 5. Cancelamento (quando necessário)

O cancelamento de notas fiscais é realizado através da view `cancel_invoice`:

1. O sistema chama o método `cancel_invoice` do serviço `NFEioService`
2. Envia a requisição de cancelamento para a API NFE.io
3. Atualiza o status do objeto `Invoice` para "cancelled"

## Formato dos Dados

### Estrutura da Requisição para Emissão

```python
invoice_data = {
    "borrower": {
        "type": tipo_de_pessoa,  # "NaturalPerson" ou "LegalEntity"
        "name": nome_do_cliente,
        "email": email_do_cliente,
        "federalTaxNumber": numero_documento_fiscal,  # CPF ou CNPJ como número inteiro
        "address": {
            "country": "BRA",
            "state": estado,
            "city": {
                "code": codigo_ibge_cidade,
                "name": nome_cidade
            },
            "district": bairro,
            "street": logradouro,
            "number": numero,
            "postalCode": cep_sem_formatacao,
            "additionalInformation": complemento
        }
    },
    "cityServiceCode": codigo_servico,  # Exemplo: "0107" para serviços educacionais
    "description": descricao_servico,
    "servicesAmount": valor_em_float,
    "environment": ambiente,  # "Development" ou "Production"
    "reference": referencia_unica,
    "additionalInformation": informacoes_adicionais
}
```

### Pontos Críticos na Formatação

1. **Tipo de Pessoa vs. Documento Fiscal**:
   - Pessoa Física (NaturalPerson): Deve usar CPF (11 dígitos)
   - Pessoa Jurídica (LegalEntity): Deve usar CNPJ (14 dígitos)

2. **Formato do Endereço**:
   - O campo `city` deve ser um objeto com `code` (código IBGE) e `name`
   - O campo `country` deve usar o código ISO de 3 letras (ex: "BRA")

3. **Código de Serviço**:
   - Usar o campo `cityServiceCode` (não `serviceCode`)
   - Verificar o código correto para o tipo de serviço prestado

4. **Formato de Documentos**:
   - Remover pontos, traços e barras dos documentos (CPF/CNPJ)
   - Converter para número inteiro

## Status da Nota Fiscal

As notas fiscais podem ter os seguintes status:

| Status API NFE.io | Status no Sistema | Descrição |
|-------------------|-------------------|-----------|
| WaitingCalculateTaxes | processing | Aguardando cálculo de impostos |
| WaitingSend | processing | Aguardando envio para a prefeitura |
| WaitingReturn | processing | Aguardando retorno da prefeitura |
| Issued | approved | Nota fiscal emitida com sucesso |
| Cancelled | cancelled | Nota fiscal cancelada |
| Error | error | Erro na emissão da nota fiscal |

## Troubleshooting

### Erros Comuns

1. **Erro 400 (Bad Request)**:
   - Verificar formato dos campos (especialmente CPF/CNPJ e endereço)
   - Verificar se o tipo de pessoa está consistente com o documento fiscal

2. **Status "Pending" da Empresa**:
   - Verificar o cadastro da empresa na plataforma NFE.io
   - Completar informações pendentes no cadastro

3. **Nota Presa em WaitingCalculateTaxes**:
   - Verificar status fiscal da empresa na NFE.io
   - Verificar se o ambiente de desenvolvimento está configurado corretamente

4. **Erro sem mensagem detalhada**:
   - Verificar logs do sistema
   - Contactar suporte da NFE.io com detalhes da requisição

### Ferramentas de Diagnóstico

Para diagnosticar problemas na emissão de notas fiscais, os seguintes scripts podem ser utilizados:

- `test_nfeio_connection.py`: Testa conexão básica com a API
- `diagnose_nfeio_invoice.py`: Diagnóstico de problemas na emissão
- `test_nfeio_exact_format.py`: Testa o formato exato da documentação
- `test_nfeio_fixed_fields.py`: Testa correções específicas no formato
- `test_nfeio_final_fix.py`: Implementação final com correções

## Limitações e Recomendações

### Limitações Conhecidas

1. **Status Fiscal "Pending"**:
   - Notas podem ficar presas em "WaitingCalculateTaxes" se o status fiscal da empresa estiver como "Pending"
   - É necessário completar o cadastro da empresa na plataforma NFE.io

2. **Resposta da API sem Detalhes**:
   - Em alguns casos, a API retorna erro 400 sem detalhes sobre o problema
   - Recomenda-se implementar logs detalhados para facilitar diagnóstico

### Recomendações

1. **Teste em Ambiente de Desenvolvimento**:
   - Utilize `NFEIO_ENVIRONMENT=Development` para testes
   - Verifique se o ambiente de desenvolvimento está corretamente configurado na NFE.io

2. **Validação de Documentos**:
   - Implemente validação de CPF/CNPJ no frontend
   - Garanta que os dados do endereço estejam completos

3. **Monitoramento de Status**:
   - Implemente verificação periódica para notas presas em um mesmo status
   - Considere um sistema de timeout para cancelar notas que demoram muito para processar

4. **Cadastro na NFE.io**:
   - Complete todas as informações fiscais da empresa na plataforma NFE.io
   - Verifique regularmente se há mudanças no status fiscal da empresa

## Referências

- [Documentação NFE.io](https://nfe.io/docs/)
- [Conceitos de Notas Fiscais](https://nfe.io/docs/documentacao/conceitos/notas-fiscais/)
- [Campos Obrigatórios](https://nfe.io/docs/documentacao/nota-fiscal-servico-eletronica/duvidas/)
- [Campos de Autorização](https://nfe.io/docs/nota-fiscal-servico-eletronica/duvidas/campos-para-autorizacao-de-nfse/)
