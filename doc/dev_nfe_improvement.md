# Documentação Técnica: Sistema de Emissão de Notas Fiscais com NFE.io

## 1. Visão Geral

O sistema de emissão de notas fiscais da plataforma CincoCincoJAM integra-se com a API do NFE.io para permitir que professores emitam notas fiscais de serviço (NFS-e) automaticamente para as transações de pagamento realizadas na plataforma. Esta funcionalidade é crítica para garantir a conformidade fiscal e proporcionar uma experiência completa para professores que atuam como pessoas jurídicas.

### 1.1 Recursos Principais

- Gerenciamento de configurações fiscais dos professores
- Emissão automática de notas fiscais para transações pagas
- Consulta de status das notas fiscais em tempo real
- Visualização e download dos PDFs das notas fiscais
- Cancelamento de notas fiscais quando necessário
- Interface administrativa para monitoramento e suporte

### 1.2 Arquitetura do Sistema

```
┌───────────────────┐      ┌───────────────────┐      ┌───────────────────┐
│                   │      │                   │      │                   │
│  CincoCincoJAM    │◄────►│     NFE.io API    │◄────►│    Prefeituras    │
│    Plataforma     │      │  (Gateway NFS-e)  │      │    Municipais     │
│                   │      │                   │      │                   │
└───────────────────┘      └───────────────────┘      └───────────────────┘
```

## 2. Modelos de Dados

### 2.1 CompanyConfig (Configuração da Empresa)

```python
class CompanyConfig(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_config')
    
    # Dados básicos da empresa
    cnpj = models.CharField(max_length=18)
    razao_social = models.CharField(max_length=200)
    nome_fantasia = models.CharField(max_length=200, blank=True)
    
    # Endereço
    cep = models.CharField(max_length=9)
    endereco = models.CharField(max_length=200)
    numero = models.CharField(max_length=10)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    
    # Dados fiscais
    inscricao_municipal = models.CharField(max_length=20)
    regime_tributario = models.CharField(max_length=50)
    
    # Configurações RPS
    rps_serie = models.CharField(max_length=5, default='1')
    rps_numero_atual = models.PositiveIntegerField(default=1)
    rps_lote = models.PositiveIntegerField(default=1)
    
    # Códigos de serviço
    codigo_servico_municipal = models.CharField(max_length=20)
    cnae = models.CharField(max_length=20)
    
    # Alíquotas
    aliquota_iss = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Controle
    enabled = models.BooleanField(default=True)
    
    def is_complete(self):
        """Verifica se todos os campos obrigatórios estão preenchidos"""
        # Implementação da verificação de campos obrigatórios
```

### 2.2 Invoice (Nota Fiscal)

```python
class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Rascunho'),
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('approved', 'Aprovada'),
        ('cancelled', 'Cancelada'),
        ('error', 'Erro')
    ]
    
    # Relacionamentos
    transaction = models.ForeignKey('payments.PaymentTransaction', on_delete=models.CASCADE, related_name='invoices')
    
    # Campos de status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # IDs externos da NFE.io
    external_id = models.CharField(max_length=100, blank=True, null=True)
    focus_status = models.CharField(max_length=50, blank=True, null=True)
    
    # URLs de documentos
    focus_pdf_url = models.URLField(blank=True, null=True)
    focus_xml_url = models.URLField(blank=True, null=True)
    
    # Campos RPS
    rps_serie = models.CharField(max_length=5, blank=True, null=True)
    rps_numero = models.PositiveIntegerField(blank=True, null=True)
    rps_lote = models.PositiveIntegerField(blank=True, null=True)
    
    # Campos técnicos
    response_data = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    emitted_at = models.DateTimeField(blank=True, null=True)
```

## 3. Fluxo de Emissão de Notas Fiscais

### 3.1 Diagrama de Sequência Completo

```
┌─────────┐        ┌─────────┐        ┌─────────┐        ┌─────────┐        ┌─────────┐
│         │        │         │        │         │        │         │        │         │
│ Aluno   │        │ Payment │        │ Invoice │        │ NFEio   │        │Prefeitura│
│         │        │ System  │        │ Service │        │ API     │        │         │
└────┬────┘        └────┬────┘        └────┬────┘        └────┬────┘        └────┬────┘
     │                  │                  │                  │                  │
     │  Realiza         │                  │                  │                  │
     │  pagamento       │                  │                  │                  │
     │─────────────────►│                  │                  │                  │
     │                  │                  │                  │                  │
     │                  │  Pagamento       │                  │                  │
     │                  │  confirmado      │                  │                  │
     │                  │─────────────────►│                  │                  │
     │                  │                  │                  │                  │
     │                  │                  │  Cria objeto     │                  │
     │                  │                  │  Invoice         │                  │
     │                  │                  │───┐              │                  │
     │                  │                  │   │              │                  │
     │                  │                  │◄──┘              │                  │
     │                  │                  │                  │                  │
     │                  │                  │  Prepara dados   │                  │
     │                  │                  │  da requisição   │                  │
     │                  │                  │───┐              │                  │
     │                  │                  │   │              │                  │
     │                  │                  │◄──┘              │                  │
     │                  │                  │                  │                  │
     │                  │                  │  Envia           │                  │
     │                  │                  │  requisição      │                  │
     │                  │                  │─────────────────►│                  │
     │                  │                  │                  │                  │
     │                  │                  │                  │  Processa e      │
     │                  │                  │                  │  envia para      │
     │                  │                  │                  │  prefeitura      │
     │                  │                  │                  │─────────────────►│
     │                  │                  │                  │                  │
     │                  │                  │                  │  Resposta        │
     │                  │                  │                  │◄─────────────────│
     │                  │                  │                  │                  │
     │                  │                  │  Resposta com    │                  │
     │                  │                  │  status e URLs   │                  │
     │                  │                  │◄─────────────────│                  │
     │                  │                  │                  │                  │
     │                  │                  │  Atualiza        │                  │
     │                  │                  │  Invoice no DB   │                  │
     │                  │                  │───┐              │                  │
     │                  │                  │   │              │                  │
     │                  │                  │◄──┘              │                  │
     │                  │                  │                  │                  │
     │  Acesso ao       │  Notificação     │                  │                  │
     │  PDF da nota     │  ao professor    │                  │                  │
     │◄─────────────────┼──────────────────┘                  │                  │
     │                  │                                     │                  │
```

### 3.2 Etapas Detalhadas

#### 3.2.1 Configuração do Professor

1. O professor acessa as configurações fiscais
2. Preenche dados da empresa (CNPJ, razão social, etc.)
3. Configura códigos de serviço e alíquotas
4. Configura números de RPS (Recibo Provisório de Serviços)
5. Sistema valida os dados e ativa a emissão de notas fiscais

#### 3.2.2 Pagamento e Criação da Fatura

1. Aluno realiza um pagamento por um curso
2. Sistema marca o pagamento como confirmado
3. Professor acessa a transação e solicita emissão da nota fiscal
4. Sistema cria um objeto `Invoice` com status "pending"

#### 3.2.3 Emissão da Nota Fiscal

1. O serviço `NFEioService` prepara os dados para a API:
   - Dados da empresa do professor
   - Dados do aluno (cliente)
   - Detalhes do serviço e valor
   - Configurações de impostos
   - Número sequencial do RPS

2. O serviço envia a requisição para a API NFE.io
   ```python
   invoice_data = {
       "borrower": {
           "name": transaction.enrollment.student.get_full_name(),
           "email": transaction.enrollment.student.email,
           "federalTaxNumber": 11122233344,  # CPF do aluno
           "type": "NaturalPerson",  # Pessoa física
           # Outros dados do cliente...
       },
       "cityServiceCode": company_config.codigo_servico_municipal,
       "description": f"Aula de {transaction.enrollment.course.title}",
       "servicesAmount": float(transaction.amount),
       "rpsNumber": company_config.rps_numero_atual,
       "rpsSerie": company_config.rps_serie,
       "environment": settings.NFEIO_ENVIRONMENT,
       # Outros campos necessários...
   }
   ```

3. A API NFE.io recebe a requisição e:
   - Valida os dados
   - Calcula os impostos
   - Gera o número do RPS
   - Comunica-se com a prefeitura municipal
   - Retorna um ID de transação e status inicial

4. O serviço `NFEioService` atualiza o objeto `Invoice`:
   - Status atualizado para "processing"
   - Salva o ID externo recebido da API
   - Atualiza o número do RPS na configuração da empresa

5. Incrementa o número do RPS na configuração da empresa

#### 3.2.4 Verificação de Status

1. O sistema verifica periodicamente o status da nota fiscal:
   ```python
   endpoint = f"companies/{self.company_id}/serviceinvoices/{invoice.external_id}/status"
   response = self._make_request('GET', endpoint)
   ```

2. A API NFE.io retorna o status atual:
   - "WaitingCalculateTaxes": Aguardando cálculo de impostos
   - "WaitingDefineRpsNumber": Aguardando definição do número RPS
   - "WaitingSend": Aguardando envio para prefeitura
   - "WaitingReturn": Aguardando retorno da prefeitura
   - "Authorized": Nota fiscal autorizada pela prefeitura
   - "Error": Erro na emissão da nota fiscal

3. O sistema mapeia o status da API para o status interno:
   ```python
   api_to_system_status = {
       'Authorized': 'approved',
       'Cancelled': 'cancelled',
       'Error': 'error',
       'WaitingCalculateTaxes': 'processing',
       'WaitingDefineRpsNumber': 'processing',
       'WaitingSend': 'processing',
       'WaitingReturn': 'processing',
       'Processing': 'processing'
   }
   ```

4. Quando a nota é aprovada (status = "Authorized"):
   - O sistema recupera a URL do PDF
   - Atualiza o objeto `Invoice` com a URL
   - Notifica o professor sobre a emissão bem-sucedida

#### 3.2.5 Acesso ao PDF da Nota Fiscal

1. O professor acessa o dashboard financeiro
2. Visualiza a lista de notas fiscais emitidas
3. Clica no botão para visualizar ou baixar o PDF
4. O sistema redireciona para a URL do PDF fornecida pela API NFE.io

## 4. Configuração do Sistema

### 4.1 Variáveis de Ambiente

```
# .env
NFEIO_API_KEY=sua_api_key_aqui
NFEIO_COMPANY_ID=seu_company_id_aqui
NFEIO_ENVIRONMENT=Development   # ou Production
```

### 4.2 Configuração em settings.py

```python
# settings.py
NFEIO_API_KEY = os.getenv("NFEIO_API_KEY")
NFEIO_COMPANY_ID = os.getenv("NFEIO_COMPANY_ID")
NFEIO_ENVIRONMENT = os.getenv("NFEIO_ENVIRONMENT", "Development")
NFEIO_API_URL = "https://api.nfe.io"
```

### 4.3 Instalação e Configuração Inicial

1. Adicionar o app 'invoices' em INSTALLED_APPS
2. Executar migrations para criar as tabelas necessárias
3. Configurar as variáveis de ambiente
4. Criar conta e API key na plataforma NFE.io
5. Configurar webhook para receber atualizações de status (opcional)

## 5. Monitoramento e Troubleshooting

### 5.1 Pontos Críticos do Sistema

1. **Geração de Números RPS**:
   - Deve ser sequencial e único
   - Requer sincronização para evitar duplicidades
   - Precisa ser persistido mesmo em caso de falhas

2. **Formatação dos Dados**:
   - CPF/CNPJ deve estar no formato correto (apenas números)
   - Tipo de pessoa deve corresponder ao documento (CPF ou CNPJ)
   - Códigos de serviço devem ser válidos para o município

3. **Tempos de Resposta**:
   - Comunicação com prefeituras pode ser lenta
   - Notas podem ficar presas em "processing" por tempo indeterminado
   - Sistema deve lidar com timeouts e falhas de comunicação

### 5.2 Logs e Monitoramento

O sistema mantém logs detalhados de todas as operações:

```python
# Configuração de logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/invoice_test.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("invoice_test")
```

Os logs incluem:
- Requisições enviadas para a API
- Respostas recebidas
- Alterações de status
- Erros e exceções
- Informações de debugging

### 5.3 Ferramentas de Diagnóstico

O sistema inclui um script de teste para diagnóstico:

```
python test_rps_emission_improved.py [email_do_professor] [id_da_transacao]
```

Este script:
1. Verifica a configuração do ambiente
2. Encontra um professor e sua configuração fiscal
3. Localiza uma transação elegível para emissão
4. Emite uma nota fiscal de teste
5. Verifica o status inicial
6. Gera logs detalhados para análise

### 5.4 Erros Comuns e Soluções

| Erro | Possível Causa | Solução Recomendada |
|------|----------------|---------------------|
| 400 Bad Request | Formato de dados incorreto | Verificar formato do CPF/CNPJ e endereço |
| 401 Unauthorized | API key inválida ou expirada | Revisar e atualizar a API key |
| 404 Not Found | ID de nota fiscal inexistente | Verificar se a nota foi realmente criada |
| WaitingCalculateTaxes (timeout) | Problema no cadastro da empresa | Completar cadastro na plataforma NFE.io |
| Erro na prefeitura | Rejeição pela prefeitura | Verificar código de serviço e alíquotas |

## 6. Segurança e Boas Práticas

### 6.1 Considerações de Segurança

1. **Proteção da API Key**:
   - Nunca expor a API key no frontend
   - Armazenar de forma segura em variáveis de ambiente
   - Usar permissões mínimas necessárias na API NFE.io

2. **Controle de Acesso**:
   - Professores só podem emitir notas de suas próprias transações
   - Apenas administradores podem aprovar manualmente notas (em ambiente de teste)
   - Verificações de permissão em todas as views

3. **Validação de Dados**:
   - Validar todos os dados de entrada
   - Confirmar que o valor da nota corresponde exatamente à transação
   - Prevenir injeção de dados maliciosos

4. **Auditoria**:
   - Registrar todas as operações críticas
   - Manter histórico de alterações de status
   - Rastrear origem de cada ação (IP, usuário, timestamp)

### 6.2 Boas Práticas

1. **Verificação de Status**:
   - Implementar verificação periódica para notas "presas"
   - Notificar administradores sobre falhas recorrentes
   - Criar mecanismo de retry para notas com falha temporária

2. **Transações e Atomicidade**:
   - Usar transações de banco de dados para operações críticas
   - Garantir que o número RPS seja incrementado apenas uma vez
   - Implementar mecanismos de compensação para falhas

3. **Testes em Ambiente de Desenvolvimento**:
   - Sempre usar `NFEIO_ENVIRONMENT=Development` para testes
   - Implementar simulação local para testes sem custo
   - Manter conjunto de dados de teste consistente

4. **Documentação e Treinamento**:
   - Manter documentação atualizada para administradores e suporte
   - Criar guias claros para usuários (professores)
   - Documentar todos os códigos de erro e suas soluções

## 7. Ambiente de Testes e Desenvolvimento

### 7.1 Aprovação Manual (Apenas para Testes)

Para facilitar o teste do sistema sem depender da comunicação com prefeituras, o ambiente de desenvolvimento inclui uma função para aprovar manualmente notas fiscais:

```python
@login_required
@admin_required
def approve_invoice_manually(request, invoice_id):
    """
    Simula a aprovação de uma nota fiscal (apenas para testes).
    IMPORTANTE: Esta função é apenas para testes e não deve ser usada em produção.
    """
    # Verificar se estamos em ambiente de produção
    if not settings.DEBUG:
        messages.error(request, _('Esta funcionalidade só está disponível em ambiente de desenvolvimento.'))
        return redirect('payments:admin_dashboard')
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Atualizar o status para aprovado
    invoice.status = 'approved'
    invoice.focus_status = 'Authorized'
    
    # Gerar uma URL fictícia para o PDF
    invoice.focus_pdf_url = f"https://storage.googleapis.com/cincocincojam-dev/invoices/pdf_simulated/{invoice.id}.pdf"
    
    invoice.save()
    
    return redirect('invoices:invoice_detail', invoice_id=invoice_id)
```

### 7.2 Configuração de Ambiente de Desenvolvimento

1. **Sandbox NFE.io**:
   - Usar o ambiente de sandbox da NFE.io
   - Configurar empresa de teste na plataforma
   - Usar dados fictícios para testes

2. **Dados de Teste**:
   - Criar um conjunto de dados de teste para professores e alunos
   - Usar CPFs e CNPJs válidos mas fictícios
   - Configurar códigos de serviço válidos para testes

3. **Flags de Ambiente**:
   ```python
   # Verificar ambiente
   if settings.DEBUG:
       # Lógica específica para desenvolvimento
   else:
       # Lógica para produção
   ```

## 8. Interfaces do Usuário

### 8.1 Dashboard do Professor

- Lista de transações com opção para emitir nota fiscal
- Lista de notas fiscais já emitidas
- Filtros por status, data e valor
- Links para download de PDFs
- Botões para verificar status ou cancelar notas

### 8.2 Dashboard Administrativo

- Visão geral de todas as notas fiscais no sistema
- Estatísticas por status e valor
- Filtros avançados (professor, aluno, curso, status)
- Ferramentas de diagnóstico e suporte
- No ambiente de desenvolvimento, opção para aprovar manualmente

### 8.3 Página de Detalhes da Nota Fiscal

- Informações completas da nota fiscal
- Status atual e histórico de status
- Dados da transação e do curso
- Botões de ação (verificar status, baixar PDF)
- Mensagens de erro (quando aplicável)

## 9. Referências

1. [Documentação Oficial NFE.io](https://nfe.io/docs/)
2. [API de Notas Fiscais de Serviço](https://nfe.io/docs/api-notas-fiscais-servico/)
3. [Webhooks NFE.io](https://nfe.io/docs/api-webhooks/)
4. [Conceitos de RPS e NFS-e](https://nfe.io/blog/nota-fiscal/o-que-e-rps/)
5. [Legislação sobre Emissão de NFS-e](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/estabelecimentos/nfse-nota-fiscal-de-servicos-eletronices)

## 10. Anexos

### 10.1 Esquema de Banco de Dados

```
+------------------+     +-------------------+     +-----------------+
|     Invoice      |     |  CompanyConfig    |     |  Transaction    |
+------------------+     +-------------------+     +-----------------+
| id               |     | id                |     | id              |
| transaction_id   |<----+ user_id           +---->| enrollment_id   |
| status           |     | cnpj              |     | amount          |
| external_id      |     | razao_social      |     | status          |
| focus_status     |     | inscricao_municipal|     | payment_method  |
| focus_pdf_url    |     | rps_serie         |     | paid_at         |
| rps_serie        |     | rps_numero_atual  |     | created_at      |
| rps_numero       |     | regime_tributario |     +-----------------+
| error_message    |     | enabled           |
| created_at       |     +-------------------+
| updated_at       |
| emitted_at       |
+------------------+
```

### 10.2 Exemplo de Resposta da API

```json
{
  "id": "67f1e6d3094b7d1cb4a1bc75",
  "status": "Issued",
  "environment": "Development",
  "flow_status": "Authorized",
  "flow_message": null,
  "pdf": {
    "url": "https://api.nfe.io/v1/companies/123456/serviceinvoices/67f1e6d3094b7d1cb4a1bc75/pdf"
  },
  "xml": {
    "url": "https://api.nfe.io/v1/companies/123456/serviceinvoices/67f1e6d3094b7d1cb4a1bc75/xml"
  },
  "rps_number": 123,
  "rps_series": "1",
  "created_at": "2025-04-15T10:30:00.000Z",
  "updated_at": "2025-04-15T10:35:00.000Z"
}
``` 