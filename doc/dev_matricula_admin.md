# Funcionalidade de Matrícula Direta no Painel Administrativo - 55Jam

## 1. Visão Geral

Esta documentação descreve a implementação de uma funcionalidade administrativa que permite realizar matrículas de alunos em cursos diretamente pelo painel administrativo, sem necessidade de pagamento. Este recurso foi criado principalmente para:

1. **Demonstrações e testes**: Permitir demonstrar o fluxo completo da plataforma para clientes.
2. **Matrículas especiais**: Conceder acesso a cursos para alunos em situações específicas (bolsistas, cortesias, etc).
3. **Solução de problemas**: Alternativa ao simulador de pagamento PIX que pode não funcionar em ambiente de produção.

## 2. Arquivos Implementados/Modificados

### 2.1. Interface Administrativa
- `courses/admin.py` - Implementação da classe `EnrollmentAdmin` com funcionalidades personalizadas.
- `templates/admin/base_site.html` - Template personalizado para o painel administrativo.
- `templates/admin/courses/enrollment/change_list.html` - Template para exibir o botão de matricular aluno.
- `templates/admin/courses/enrollment/create_enrollment.html` - Formulário para criação de matrículas.

### 2.2. Links de Acesso
- `templates/users/dashboard.html` - Adição de link para ver todas as matrículas no dashboard administrativo.

## 3. Detalhes da Implementação

### 3.1. Registro do Modelo no Admin

O modelo `Enrollment` foi registrado no admin do Django com uma interface personalizada:

```python
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo Enrollment.
    Permite matricular alunos em cursos diretamente.
    """
    list_display = ('id', 'student_email', 'course_title', 'status', 'progress', 'enrolled_at')
    list_filter = (EnrollmentStatusFilter, 'enrolled_at', 'course')
    search_fields = ('student__email', 'student__first_name', 'course__title')
    readonly_fields = ('enrolled_at', 'completed_at', 'progress')
    raw_id_fields = ('student', 'course')
    actions = ['activate_enrollment', 'cancel_enrollment']
```

### 3.2. Funcionalidade de Criação de Matrícula

Uma view personalizada foi criada para permitir a criação de matrículas diretamente:

```python
def create_enrollment_view(self, request):
    """View para criar uma matrícula diretamente"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Se for um POST, tenta criar a matrícula
    if request.method == 'POST':
        student_id = request.POST.get('student')
        course_id = request.POST.get('course')
        status = request.POST.get('status', Enrollment.Status.ACTIVE)
        
        if student_id and course_id:
            try:
                student = User.objects.get(id=student_id)
                course = Course.objects.get(id=course_id)
                
                # Verifica se já existe matrícula
                existing = Enrollment.objects.filter(student=student, course=course).first()
                
                if existing:
                    # Atualiza status se já existir
                    existing.status = status
                    existing.save()
                    messages.success(
                        request, 
                        _(f'Matrícula de {student.email} atualizada no curso "{course.title}"!')
                    )
                else:
                    # Cria nova matrícula
                    enrollment = Enrollment.objects.create(
                        student=student,
                        course=course,
                        status=status
                    )
                    messages.success(
                        request, 
                        _(f'Aluno {student.email} matriculado no curso "{course.title}" com sucesso!')
                    )
                    
                return redirect('admin:courses_enrollment_changelist')
            except (User.DoesNotExist, Course.DoesNotExist) as e:
                messages.error(request, _(f'Erro ao criar matrícula: {str(e)}'))
```

### 3.3. Ações em Massa para Matrículas

Foram implementadas ações em massa para ativar ou cancelar várias matrículas simultaneamente:

```python
def activate_enrollment(self, request, queryset):
    """Ativa as matrículas selecionadas"""
    count = 0
    for enrollment in queryset:
        if enrollment.status != Enrollment.Status.ACTIVE:
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()
            count += 1
    
    messages.success(request, _(f'{count} matrículas ativadas com sucesso.'))
activate_enrollment.short_description = _('Ativar matrículas selecionadas')

def cancel_enrollment(self, request, queryset):
    """Cancela as matrículas selecionadas"""
    count = 0
    for enrollment in queryset:
        if enrollment.status != Enrollment.Status.CANCELLED:
            enrollment.status = Enrollment.Status.CANCELLED
            enrollment.save()
            count += 1
    
    messages.success(request, _(f'{count} matrículas canceladas com sucesso.'))
cancel_enrollment.short_description = _('Cancelar matrículas selecionadas')
```

### 3.4. Template Personalizado para Criação de Matrícula

Um template personalizado foi criado para facilitar a criação de matrículas:

```html
<div class="enrollments-form">
    <form method="post">
        {% csrf_token %}
        
        <div class="form-row">
            <div class="field-box">
                <label for="id_student">{% trans 'Aluno:' %}</label>
                <select name="student" id="id_student" required>
                    <option value="">---------</option>
                    {% for student in students %}
                        <option value="{{ student.id }}">{{ student.email }} ({{ student.first_name }} {{ student.last_name }})</option>
                    {% endfor %}
                </select>
            </div>
        </div>
        
        <div class="form-row">
            <div class="field-box">
                <label for="id_course">{% trans 'Curso:' %}</label>
                <select name="course" id="id_course" required>
                    <option value="">---------</option>
                    {% for course in courses %}
                        <option value="{{ course.id }}">{{ course.title }} (R$ {{ course.price }})</option>
                    {% endfor %}
                </select>
            </div>
        </div>
        
        <div class="form-row">
            <div class="field-box">
                <label for="id_status">{% trans 'Status da matrícula:' %}</label>
                <select name="status" id="id_status">
                    {% for status_value, status_label in status_choices %}
                        <option value="{{ status_value }}" {% if status_value == 'ACTIVE' %}selected{% endif %}>{{ status_label }}</option>
                    {% endfor %}
                </select>
            </div>
        </div>
        
        <div class="submit-row">
            <input type="submit" value="{% trans 'Matricular' %}" class="default">
        </div>
    </form>
</div>
```

## 4. Fluxo de Utilização

### 4.1. Acesso à Funcionalidade
1. O administrador acessa o painel administrativo em `/admin/`.
2. Navega até a seção "Matrículas" ou clica em "Ver Todas" no card de matrículas do dashboard.
3. Clica no botão "Matricular aluno" no canto superior direito.

### 4.2. Criação de Matrícula
1. No formulário de criação, o administrador:
   - Seleciona um aluno da lista (apenas usuários do tipo "STUDENT").
   - Seleciona um curso da lista (apenas cursos com status "PUBLISHED").
   - Define o status da matrícula (geralmente "ACTIVE").
2. Ao clicar em "Matricular":
   - Se o aluno já estiver matriculado no curso, seu status é atualizado.
   - Se for uma nova matrícula, ela é criada com o status selecionado.
3. O administrador é redirecionado para a lista de matrículas com uma mensagem de sucesso.

### 4.3. Ações em Massa
1. Na listagem de matrículas, o administrador pode:
   - Selecionar várias matrículas usando as caixas de seleção.
   - Escolher "Ativar matrículas selecionadas" ou "Cancelar matrículas selecionadas" no menu suspenso.
   - Clicar em "Ir" para executar a ação selecionada.
2. As matrículas são atualizadas em lote e uma mensagem de sucesso é exibida.

## 5. Permissões e Segurança

### 5.1. Requisitos de Acesso
Para acessar esta funcionalidade, o usuário precisa ter:
- Acesso ao painel administrativo do Django (`is_staff=True`).
- Permissões para visualizar e editar objetos do modelo `Enrollment`.

### 5.2. Considerações de Segurança
- A funcionalidade é restrita apenas a usuários administradores.
- Todas as ações são registradas no log de administração para auditoria.
- As matrículas criadas por este método são claramente identificáveis (não possuem transação de pagamento associada).

## 6. Casos de Uso

### 6.1. Demonstração para Clientes
Um dos principais casos de uso é para demonstrações do sistema:
1. Criar usuários de teste (professor e aluno).
2. Criar um curso de teste com o professor.
3. Matricular o aluno de teste no curso utilizando esta funcionalidade.
4. Demonstrar o fluxo completo, incluindo acesso ao conteúdo e emissão de nota fiscal.

### 6.2. Concessão de Bolsas e Cortesias
A funcionalidade também pode ser usada para conceder acesso gratuito:
1. Para alunos que receberam bolsa de estudos.
2. Para funcionários e parceiros como cortesia.
3. Para professores que desejam experimentar outros cursos da plataforma.

### 6.3. Resolução de Problemas
Em situações onde o processamento de pagamento apresenta problemas:
1. Verificar o problema relatado pelo aluno.
2. Se houver comprovação de pagamento, utilizar esta funcionalidade para garantir acesso imediato.
3. Resolver as questões financeiras posteriormente sem prejudicar a experiência do aluno.

## 7. Considerações Finais

### 7.1. Manutenção
- A funcionalidade não requer manutenção específica além das atualizações gerais do sistema.
- Ao modificar o modelo `Enrollment`, garantir que os campos relevantes para esta funcionalidade permaneçam acessíveis.

### 7.2. Possíveis Melhorias Futuras
- Adicionar campos para registrar a justificativa da concessão da matrícula.
- Implementar um sistema de aprovação em dois níveis para matrículas administrativas.
- Criar relatórios específicos para matrículas concedidas administrativamente.
- Adicionar opção para enviar e-mail de notificação ao aluno sobre a matrícula concedida. 