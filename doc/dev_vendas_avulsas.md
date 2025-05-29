# Documentação Técnica: Vendas Avulsas

## Visão Geral

Este documento descreve a implementação do sistema de vendas avulsas do 55Jam, que permite aos professores criar e gerenciar vendas de produtos ou serviços não vinculados à matrícula em cursos. O sistema inclui funcionalidades como criação de vendas, pagamento via Pix, e acompanhamento do status das vendas.

## Arquitetura da Implementação

### Componentes Principais

1. **SingleSale** (`payments/models.py`): Modelo para armazenar informações sobre vendas avulsas
2. **OpenPixService** (`payments/openpix_service.py`): Serviço para gerar pagamentos via Pix
3. **Views** (`payments/views.py`): Controladores para gerenciar vendas avulsas
4. **Templates** (`payments/templates/payments/professor/`): Interfaces para gerenciar vendas avulsas

### Modelos e Relações

O modelo principal é o `SingleSale`, que armazena:

- Informações básicas da venda (descrição, valor, status)
- Dados do vendedor (professor)
- Dados do cliente (nome, e-mail, CPF)
- Informações de pagamento (método, dados Pix)
- Datas (criação, atualização, pagamento)

## Funcionalidades Implementadas

### 1. Gerenciamento de Vendas Avulsas

#### 1.1. Listagem de Vendas

Implementada em `SingleSaleListView` e `singlesale_list.html`, permite:

- Visualizar todas as vendas avulsas criadas pelo professor
- Filtrar por status e período
- Visualizar resumo financeiro (total de vendas, total recebido, total pendente)

#### 1.2. Criação de Vendas

Implementada em `SingleSaleCreateView` e `singlesale_form.html`, permite:

- Criar uma nova venda avulsa
- Definir descrição, valor e dados do cliente
- Status inicial é sempre "Pendente"

#### 1.3. Detalhes da Venda

Implementada em `SingleSaleDetailView` e `singlesale_detail.html`, permite:

- Visualizar informações detalhadas da venda
- Acessar ações como atualização e geração de Pix

#### 1.4. Atualização de Vendas

Implementada em `SingleSaleUpdateView`, permite:

- Editar informações da venda (descrição, valor, dados do cliente)
- Alterar o status manualmente se necessário

### 2. Pagamento via Pix

#### 2.1. Geração de Pagamento Pix

Implementada em `create_singlesale_pix`, permite:

- Gerar um QR code e código Pix para uma venda avulsa
- Integração com o serviço OpenPix para geração do Pix
- Armazenamento dos dados do Pix (correlation_id, brcode, qrcode_image)

#### 2.2. Visualização do Pagamento Pix

Implementada em `singlesale_pix_detail`, permite:

- Visualizar o QR code e código copia-e-cola para pagamento
- Verificar o status do pagamento em tempo real

#### 2.3. Verificação de Status

Implementada em `check_singlesale_payment_status`, permite:

- Verificar o status do pagamento Pix através da API OpenPix
- Atualizar automaticamente o status da venda quando o pagamento é confirmado
- Emitir nota fiscal automaticamente após confirmação do pagamento

### 3. Administração

#### 3.1. Visão do Administrador

Implementada em `SingleSaleAdminListView` e `admin/singlesale_list.html`, permite:

- Listar todas as vendas avulsas de todos os professores
- Filtrar por vendedor e status
- Visualizar resumo financeiro geral

## Fluxo de Utilização

### 1. Fluxo de Criação e Pagamento

1. **Criação da Venda**:
   - O professor acessa "Vendas Avulsas"
   - Clica em "Nova Venda" e preenche os dados
   - A venda é criada com status "Pendente"

2. **Geração do Pagamento**:
   - O professor acessa os detalhes da venda ou a lista de vendas
   - Clica em "Gerar Pix"
   - O sistema gera o QR code e código Pix através do OpenPixService

3. **Pagamento pelo Cliente**:
   - O professor compartilha o link de pagamento com o cliente
   - O cliente acessa a página de pagamento Pix e realiza o pagamento
   - O sistema verifica periodicamente o status do pagamento

4. **Confirmação do Pagamento**:
   - Quando o pagamento é confirmado, o status é atualizado para "Pago"
   - O sistema tenta emitir automaticamente uma nota fiscal (se configurado)
   - O professor visualiza a venda com o novo status na listagem

## Aspectos Técnicos

### 1. Segurança

- Verificação de permissões em todas as views
- Professores só podem acessar suas próprias vendas
- Validação de dados em todos os formulários

### 2. OpenPix Integration

A integração com OpenPix foi aprimorada para suportar:

- Pagamentos de vendas avulsas (sem vínculo com matrículas)
- Criação de cobranças a partir de um dicionário de dados genérico
- Armazenamento e verificação de status de pagamentos

```python
def create_charge_dict(self, charge_data, correlation_id=None, use_local_simulation=False):
    """
    Cria uma cobrança Pix a partir de um dicionário de dados
    
    Args:
        charge_data: Dicionário com os dados da cobrança
        correlation_id: ID opcional para correlação
        use_local_simulation: Se True, gera dados localmente sem chamar a API externa
        
    Returns:
        dict: Resposta da API com informações da cobrança
    """
    # Implementação...
```

### 3. Testes e Considerações

- Tratamento de erros em todas as chamadas de API
- Simulação local para desenvolvimento e testes
- Verificação de status em tempo real com atualização automática

## Melhorias Futuras

1. **Notificação ao Cliente**:
   - Envio de e-mail automático com link de pagamento
   - Notificação de pagamento confirmado

2. **Mais Métodos de Pagamento**:
   - Suporte a pagamento por cartão de crédito
   - Suporte a boleto bancário

3. **Relatórios e Análises**:
   - Relatórios detalhados de vendas por período
   - Análise de conversão (pendente para pago)

4. **Integração com Estoque**:
   - Controle de estoque para produtos físicos
   - Baixa automática de estoque após pagamento

## Conclusão

O sistema de vendas avulsas expande as capacidades da plataforma 55Jam, permitindo que professores ofereçam produtos e serviços fora do contexto de matrículas em cursos. A implementação focou na simplicidade de uso para os professores e em uma experiência de pagamento fluida para os clientes, utilizando a integração com o serviço Pix através da API OpenPix.

## Referências

- [Documentação OpenPix](https://developers.openpix.com.br/api)
- [Documentação do Django](https://docs.djangoproject.com/)
- [Documentação do Módulo de Pagamentos do 55Jam](./dev_botao_emitir_cobranca.md) 