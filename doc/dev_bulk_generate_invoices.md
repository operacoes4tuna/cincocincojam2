# Documentação Técnica: Geração de Notas Fiscais em Massa

## 1. Visão Geral

Esta funcionalidade permite que professores selecionem múltiplas vendas avulsas na interface de listagem e gerem notas fiscais para todas elas de uma só vez, ao invés de ter que processar uma por uma. A feature implementa um sistema de ações em massa que processa múltiplas vendas selecionadas via checkboxes.

### 1.1 Recursos Principais

- Seleção múltipla de vendas avulsas via checkboxes
- Geração em massa de notas fiscais
- Feedback visual durante o processamento
- Relatório detalhado de sucessos e falhas
- Interface AJAX para melhor experiência do usuário

### 1.2 Arquitetura da Implementação

```
┌────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                    │      │                     │      │                     │
│  Template Frontend │────→ │  bulk_generate_     │────→ │  _generate_invoice_ │
│  (JavaScript AJAX) │      │  invoices (View)    │      │  for_sale (Helper)  │
│                    │      │                     │      │                     │
└────────────────────┘      └─────────────────────┘      └─────────────────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │                     │
                            │  invoices.models    │
                            │  (Invoice Creation) │
                            │                     │
                            └─────────────────────┘
```

## 2. Implementação Passo a Passo

### 2.1 Passo 1: Criar a View de Ações em Massa

**Localização:** `payments/views.py`

**Instrução:** Adicionar no final do arquivo (após a linha 1614):

```python
@login_required
def bulk_generate_invoices(request):
    """
    Gera notas fiscais em massa para vendas selecionadas.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    if not request.user.is_professor:
        return JsonResponse({'error': 'Permissão negada'}, status=403)

    try:
        # Obter IDs das vendas selecionadas
        selected_ids = request.POST.getlist('sale_ids[]')

        if not selected_ids:
            return JsonResponse({'error': 'Nenhuma venda selecionada'}, status=400)

        # Validar que todas as vendas pertencem ao usuário
        sales = SingleSale.objects.filter(
            id__in=selected_ids,
            seller=request.user
        )

        if sales.count() != len(selected_ids):
            return JsonResponse({'error': 'Algumas vendas não foram encontradas'}, status=400)

        # Contadores para o resultado
        success_count = 0
        error_count = 0
        already_has_invoice = 0
        errors = []

        for sale in sales:
            try:
                # Verificar se já existe nota fiscal para esta venda
                try:
                    from invoices.models import Invoice
                    existing_invoice = Invoice.objects.filter(singlesale=sale).first()
                    if existing_invoice:
                        already_has_invoice += 1
                        continue
                except ImportError:
                    pass

                # Tentar gerar a nota fiscal
                result = _generate_invoice_for_sale(sale, request.user)

                if result.get('success'):
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"Venda #{sale.id}: {result.get('error', 'Erro desconhecido')}")

            except Exception as e:
                error_count += 1
                errors.append(f"Venda #{sale.id}: {str(e)}")

        # Preparar resposta
        message_parts = []
        if success_count > 0:
            message_parts.append(f"{success_count} nota(s) gerada(s) com sucesso")
        if already_has_invoice > 0:
            message_parts.append(f"{already_has_invoice} venda(s) já possuía(m) nota fiscal")
        if error_count > 0:
            message_parts.append(f"{error_count} erro(s) encontrado(s)")

        response_data = {
            'success': success_count > 0 or already_has_invoice > 0,
            'message': '; '.join(message_parts),
            'details': {
                'success_count': success_count,
                'error_count': error_count,
                'already_has_invoice': already_has_invoice,
                'errors': errors
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        import traceback
        print(f"Erro em bulk_generate_invoices: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)


def _generate_invoice_for_sale(sale, user):
    """
    Função auxiliar para gerar nota fiscal para uma venda específica.
    """
    try:
        # Importar o modelo de Invoice
        from invoices.models import Invoice

        # Verificar se já existe uma nota fiscal para esta venda
        existing_invoice = Invoice.objects.filter(singlesale=sale).first()
        if existing_invoice:
            return {'success': False, 'error': 'Nota fiscal já existe'}

        # Criar nova nota fiscal
        invoice = Invoice.objects.create(
            type='rps',
            singlesale=sale,
            amount=sale.amount,
            customer_name=sale.customer_name,
            customer_email=sale.customer_email,
            customer_tax_id=sale.customer_cpf,
            customer_address=sale.customer_address,
            customer_address_number=sale.customer_address_number,
            customer_address_complement=sale.customer_address_complement,
            customer_neighborhood=sale.customer_neighborhood,
            customer_city=sale.customer_city,
            customer_state=sale.customer_state,
            customer_zipcode=sale.customer_zipcode,
            customer_phone=sale.customer_phone,
            description=sale.description,
            product_code=sale.product_code,
            municipal_service_code=sale.municipal_service_code,
            ncm_code=sale.ncm_code,
            cfop_code=sale.cfop_code,
            quantity=sale.quantity,
            unit_value=sale.unit_value,
            status='pending'
        )

        return {'success': True, 'invoice_id': invoice.id}

    except ImportError:
        return {'success': False, 'error': 'Módulo de notas fiscais não disponível'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

### 2.2 Passo 2: Adicionar URL da Nova View

**Localização:** `payments/urls.py`

**Instrução:** Adicionar na seção `singlesale_patterns` (por volta da linha 68):

```python
# Adicionar esta linha na seção singlesale_patterns
path('api/sales/bulk-generate-invoices/', views.bulk_generate_invoices, name='bulk_generate_invoices'),
```

### 2.3 Passo 3: Modificar o JavaScript no Template

**Localização:** `payments/templates/payments/professor/singlesale_list.html`

**Instrução:** Localizar a seção `// Manipulador para ações em massa` (por volta da linha 426) e substituir o bloco `if (action === 'generate-invoices')` por:

```javascript
if (action === "generate-invoices") {
  if (selectedSales.length === 0) {
    alert("Por favor, selecione pelo menos uma nota para gerar.");
    return;
  }

  // Mostrar indicador de loading
  const originalText = this.innerHTML;
  this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Gerando...';
  this.disabled = true;

  // Fazer requisição AJAX
  const formData = new FormData();
  selectedSales.forEach((id) => {
    formData.append("sale_ids[]", id);
  });

  // Obter CSRF token
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
  formData.append("csrfmiddlewaretoken", csrfToken);

  fetch("/payments/api/sales/bulk-generate-invoices/", {
    method: "POST",
    body: formData,
    headers: {
      "X-CSRFToken": csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      // Restaurar botão
      this.innerHTML = originalText;
      this.disabled = false;

      if (data.success) {
        showStatusMessage("success", data.message);

        // Opcional: recarregar a página após 2 segundos
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } else {
        showStatusMessage(
          "danger",
          data.error || "Erro ao gerar notas fiscais",
        );

        // Mostrar erros detalhados se existirem
        if (data.details && data.details.errors.length > 0) {
          console.error("Erros detalhados:", data.details.errors);
        }
      }
    })
    .catch((error) => {
      console.error("Erro na requisição:", error);

      // Restaurar botão
      this.innerHTML = originalText;
      this.disabled = false;

      showStatusMessage("danger", "Erro de conexão. Tente novamente.");
    });
}
```

### 2.4 Passo 4: Adicionar Token CSRF no Template

**Localização:** `payments/templates/payments/professor/singlesale_list.html`

**Instrução:** Adicionar no início da seção de filtros (por volta da linha 20):

```html
<form method="get" class="row g-3">
  {% csrf_token %}
  <!-- resto do formulário... -->
</form>
```

## 3. Testes para Verificar Funcionamento

### 3.1 Teste 1: Verificar URLs

**Comando:** Execute no terminal Django:

```bash
python manage.py show_urls | grep bulk
```

**Resultado esperado:** Deve mostrar a URL `/payments/api/sales/bulk-generate-invoices/`

### 3.2 Teste 2: Teste Manual da Interface

**Passos:**

1. Acesse `/payments/sales/` como professor
2. Marque alguns checkboxes de vendas
3. Clique em "Ações em massa" → "Gerar notas selecionadas"
4. Verifique se aparece o loading e depois a mensagem de sucesso/erro

### 3.3 Teste 3: Teste da API via cURL

**Comando:** (substituir pelos IDs reais das vendas)

```bash
curl -X POST "http://localhost:8000/payments/api/sales/bulk-generate-invoices/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d "sale_ids[]=1&sale_ids[]=2&sale_ids[]=3"
```

**Resultado esperado:** JSON com status de sucesso e detalhes do processamento

## 4. Resolução de Problemas

### 4.1 Erro 403 (Permissão Negada)

**Causa:** Token CSRF não configurado ou usuário não é professor

**Solução:** Verificar se o token CSRF está sendo enviado corretamente e se o usuário tem permissão de professor

### 4.2 Erro 500 (Erro Interno)

**Causa:** Erro na criação da nota fiscal ou problema com o modelo Invoice

**Solução:** Verificar logs do Django e se o app invoices está funcionando corretamente

### 4.3 Vendas Não Encontradas

**Causa:** IDs das vendas não pertencem ao usuário logado

**Solução:** Verificar se os IDs estão sendo enviados corretamente e se as vendas existem

## 5. Melhorias Futuras

### 5.1 Adicionar Progresso Visual

- Implementar barra de progresso para mostrar o progresso do processamento
- Mostrar quantas vendas foram processadas em tempo real

### 5.2 Processamento Assíncrono

- Implementar usando Celery para processar em background
- Enviar notificações por email quando o processamento terminar

### 5.3 Outras Ações em Massa

- Implementar "Gerar todos os boletos"
- Implementar "Enviar todas as notas por email"
- Implementar "Cancelar notas selecionadas"

## 6. Considerações de Segurança

1. **Validação de Permissões:** Sempre validar se o usuário é professor e se as vendas pertencem a ele
2. **CSRF Protection:** Usar token CSRF em todas as requisições POST
3. **Rate Limiting:** Considerar implementar rate limiting para evitar spam
4. **Logging:** Log detalhado de todas as ações para auditoria

## 7. Arquivos Modificados

- `payments/views.py` - Adicionadas funções `bulk_generate_invoices` e `_generate_invoice_for_sale`
- `payments/urls.py` - Adicionada URL para ações em massa
- `payments/templates/payments/professor/singlesale_list.html` - Modificado JavaScript para fazer requisição AJAX
