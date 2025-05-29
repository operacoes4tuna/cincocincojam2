# Ajustes de Menu e Telas - 55Jam

Este documento descreve as melhorias implementadas na interface de usuário da plataforma 55Jam, incluindo a reorganização dos menus, correções de contraste no tema escuro, adaptação de componentes, e adição de transições suaves.

## 1. Visão Geral

As melhorias na interface visam proporcionar uma experiência mais intuitiva e agradável, organizando menus de forma mais lógica, corrigindo problemas de contraste no tema escuro, e adicionando efeitos visuais para melhorar a experiência do usuário.

## 2. Arquivos Modificados

### 2.1. Arquivos CSS
- `static/css/theme.css` - Aprimoramento das variáveis e regras do tema escuro
- `static/css/main.css` - Adição de transições suaves e estilos específicos para tema escuro

### 2.2. Templates
- `templates/base.html` - Reorganização do menu e atualização do sistema de alternância de tema

## 3. Reorganização de Menus

### 3.1. Menu do Professor

O menu do professor foi reorganizado para agrupar funcionalidades relacionadas em dropdowns, melhorando a experiência de navegação:

```html
<!-- Menu para perfil Professor -->
{% if user.is_professor %}
    <li class="nav-item">
        <a class="nav-link" href="{% url 'courses:dashboard' %}">Dashboard</a>
    </li>
    <li class="nav-item dropdown">
        <a class="nav-link dropdown-toggle" href="#" id="agendaDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
            <i class="fas fa-calendar-alt"></i> Agenda
        </a>
        <ul class="dropdown-menu" aria-labelledby="agendaDropdown">
            <li>
                <a class="dropdown-item" href="{% url 'scheduler:calendar' %}">
                    <i class="fas fa-calendar-alt me-2"></i> Calendário
                </a>
            </li>
            <li>
                <a class="dropdown-item" href="{% url 'scheduler:professor_dashboard' %}">
                    <i class="fas fa-chalkboard-teacher me-2"></i> Agendamentos
                </a>
            </li>
        </ul>
    </li>
    <li class="nav-item dropdown">
        <a class="nav-link dropdown-toggle" href="#" id="financasDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
            <i class="fas fa-chart-line"></i> Finanças
        </a>
        <ul class="dropdown-menu" aria-labelledby="financasDropdown">
            <li>
                <a class="dropdown-item" href="{% url 'payments:professor_dashboard' %}">
                    <i class="fas fa-chart-line me-2"></i> Financeiro
                </a>
            </li>
            <li>
                <a class="dropdown-item" href="{% url 'payments:singlesale_list' %}">
                    <i class="fas fa-shopping-cart me-2"></i> Vendas Avulsas
                </a>
            </li>
        </ul>
    </li>
    <li class="nav-item dropdown">
        <a class="nav-link dropdown-toggle" href="#" id="cursosDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
            <i class="fas fa-book"></i> Cursos
        </a>
        <ul class="dropdown-menu" aria-labelledby="cursosDropdown">
            <li>
                <a class="dropdown-item" href="{% url 'courses:course_list' %}">
                    <i class="fas fa-chalkboard me-2"></i> Meus Cursos
                </a>
            </li>
            <li>
                <a class="dropdown-item" href="{% url 'courses:student:course_list' %}">
                    <i class="fas fa-list-alt me-2"></i> Catálogo de Cursos
                </a>
            </li>
        </ul>
    </li>
{% endif %}
```

As principais alterações incluem:

1. **Agrupamento por Função** - Itens relacionados agora estão agrupados em dropdowns
2. **Melhor Hierarquia Visual** - Uso de ícones e organização mais intuitiva
3. **Navegação Simplificada** - Redução do número de itens visíveis no menu principal
4. **Consistência Visual** - Padronização do uso de ícones e estilos

### 3.2. Menu do Aluno

O menu do aluno também foi reorganizado seguindo o mesmo princípio:

```html
{% if user.is_student %}
    <li class="nav-item dropdown">
        <a class="nav-link dropdown-toggle" href="#" id="agendaStudentDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
            <i class="fas fa-calendar-check"></i> Agenda
            {% if pending_invitations_count > 0 %}
            <span class="badge rounded-pill bg-danger">{{ pending_invitations_count }}</span>
            {% endif %}
        </a>
        <ul class="dropdown-menu" aria-labelledby="agendaStudentDropdown">
            <li>
                <a class="dropdown-item" href="{% url 'scheduler:student_notifications' %}">
                    <i class="fas fa-bell me-2"></i> Agendamentos
                    {% if pending_invitations_count > 0 %}
                    <span class="badge rounded-pill bg-danger">{{ pending_invitations_count }}</span>
                    {% endif %}
                </a>
            </li>
        </ul>
    </li>
    <!-- Outros itens do menu do estudante -->
{% endif %}
```

### 3.3. Botão de Tema

O botão de alternância de tema foi simplificado, removendo a funcionalidade de dropdown e transformando-o em um botão de ação direta:

```html
<!-- Botão de alternância de tema -->
<li class="nav-item ms-2">
    <a class="nav-link" href="#" id="theme-toggle-btn" title="Alternar tema claro/escuro">
        <i id="theme-icon-sun" class="fas fa-sun"></i>
        <i id="theme-icon-moon" class="fas fa-moon" style="display: none;"></i>
    </a>
</li>
```

## 4. Melhorias no Tema Escuro

### 4.1. Melhorias no Contraste

Foram implementados ajustes para melhorar o contraste e a legibilidade em modo escuro:

```css
[data-bs-theme="dark"] {
  /* Ajusta as sombras para melhor visibilidade no modo escuro */
  .shadow {
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.5) !important;
  }
  
  /* Garante que badges mantenham bom contraste */
  .badge.bg-warning {
    color: #212529 !important;
  }
  
  .badge.bg-light {
    background-color: #e0e0e0 !important;
    color: #212529 !important;
  }
  
  /* Melhora o contraste de elementos que usam texto preto */
  .text-dark {
    color: #e0e0e0 !important;
  }
}
```

### 4.2. Adaptação de Tabelas

Tabelas foram adaptadas para respeitarem o tema escuro, incluindo cabeçalhos e listagens:

```css
/* Melhora a adaptação de tabelas ao tema escuro */
[data-bs-theme="dark"] th,
[data-bs-theme="dark"] td {
  background-color: var(--card-bg) !important;
  color: var(--body-color) !important;
}

[data-bs-theme="dark"] .table-light,
[data-bs-theme="dark"] thead.table-light,
[data-bs-theme="dark"] .table-light > th,
[data-bs-theme="dark"] .table-light > td {
  background-color: #2d2d2d !important;
  color: var(--body-color) !important;
}
```

### 4.3. Cabeçalhos de Cards Coloridos

Foi melhorada a adaptação de cabeçalhos coloridos no tema escuro:

```css
/* Melhora adaptação de cabeçalhos coloridos */
[data-bs-theme="dark"] .card-header.bg-primary,
[data-bs-theme="dark"] .card-header.bg-success,
[data-bs-theme="dark"] .card-header.bg-info,
[data-bs-theme="dark"] .card-header.bg-warning,
[data-bs-theme="dark"] .card-header.bg-danger {
  color: #fff !important; /* Mantém o texto branco para contraste */
  filter: brightness(0.85); /* Reduz um pouco o brilho para melhorar o conforto visual */
}
```

### 4.4. Adaptação de Modais

Os modais foram aprimorados para funcionarem corretamente no tema escuro:

```css
/* Melhora adaptação de modais ao tema escuro */
[data-bs-theme="dark"] .modal-content {
  background-color: var(--card-bg);
  color: var(--body-color);
  border-color: var(--card-border);
}

[data-bs-theme="dark"] .modal-header,
[data-bs-theme="dark"] .modal-footer {
  background-color: #2b2b2b;
  border-color: var(--card-border);
}
```

## 5. Transições e Efeitos Visuais

### 5.1. Transições Suaves

Foram adicionadas transições suaves para melhorar a experiência de troca de tema:

```css
/* Transições suaves para mudanças de tema */
*, *::before, *::after {
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}

/* Remove transição de elementos específicos que podem causar problemas visuais */
.dropdown-menu, .tooltip, .popover {
  transition: none !important;
}
```

### 5.2. Botão de Alternância de Tema

O botão de alternância de tema foi aprimorado com efeitos visuais e feedback:

```css
/* Personalização para botão de tema */
#theme-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.05);
  color: var(--body-color);
  transition: all 0.3s ease;
}

#theme-toggle-btn:hover {
  background-color: rgba(0, 0, 0, 0.1);
  transform: rotate(15deg);
}

[data-bs-theme="dark"] #theme-toggle-btn {
  background-color: rgba(255, 255, 255, 0.1);
}

[data-bs-theme="dark"] #theme-toggle-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
}
```

## 6. Padronização Visual

### 6.1. Cards e Componentes

Cards e demais componentes foram padronizados para terem comportamento consistente:

```css
/* Melhorias para Cards */
.card {
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
  border-radius: 0.5rem;
  overflow: hidden;
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}

.card-header, .card-footer {
  background-color: rgba(0, 0, 0, 0.03);
  transition: background-color 0.3s ease, color 0.3s ease;
}

[data-bs-theme="dark"] .card-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.125);
  background-color: rgba(255, 255, 255, 0.05);
}
```

### 6.2. Botões e Formulários

Botões e elementos de formulário foram ajustados para manter bom contraste:

```css
/* Personalização de botões */
.btn {
  border-radius: 0.375rem;
}

.btn-sm {
  border-radius: 0.25rem;
}

/* Melhorias para formulários */
.form-control, .form-select {
  border-radius: 0.375rem;
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}
```

## 7. Problemas Corrigidos

### 7.1. Elementos com Fundo Branco Fixo

Foram corrigidos elementos que mantinham fundo branco mesmo no tema escuro:

```css
/* Corrige elementos com fundo forçado no tema escuro */
[data-bs-theme="dark"] .bg-white,
[data-bs-theme="dark"] .card-footer.bg-white,
[data-bs-theme="dark"] .card-header.bg-white {
  background-color: var(--card-bg) !important;
  color: var(--body-color) !important;
}
```

### 7.2. Baixo Contraste em Modais

Foi corrigido o problema de modais com baixo contraste no tema escuro, ajustando cores de fundo e texto.

### 7.3. Inconsistências nos Elementos de Tabela

Corrigidas as inconsistências em tabelas, especialmente naquelas que usam classes como `table-light`.

### 7.4. Navegação Confusa

Solucionado o problema de navegação confusa com muitos itens no menu principal, agrupando-os de forma lógica.

## 8. Boas Práticas Aplicadas

### 8.1. Uso de Variáveis CSS
- Utilização de variáveis CSS para todas as cores e estilos
- Garantia de consistência através de diferentes componentes

### 8.2. Responsividade
- Todos os ajustes mantêm a responsividade da plataforma
- Testados em diferentes tamanhos de tela

### 8.3. Acessibilidade
- Melhorias no contraste para maior acessibilidade
- Atenção ao texto sobre cores de fundo garantindo boa legibilidade

### 8.4. Transições Suaves
- Utilização de transições para melhorar a experiência do usuário
- Prevenção de mudanças abruptas ao alternar o tema

### 8.5. Arquitetura de Informação
- Agrupamento lógico de funcionalidades relacionadas
- Redução da carga cognitiva na navegação

## 9. Guia para Desenvolvedores

Para manter a consistência visual e de navegação, desenvolvedores devem seguir estas orientações:

1. **Evitar cores fixas** - Sempre usar variáveis CSS como `var(--body-bg)`, `var(--card-bg)`, etc.
2. **Testar em ambos os temas** - Verificar se todos os componentes estão visíveis em ambos os temas
3. **Verificar contraste** - Garantir que o texto tenha contraste suficiente com seu fundo
4. **Usar classes adaptáveis** - Preferir classes como `bg-primary` ao invés de cores fixas
5. **Manter a estrutura de menus** - Seguir o padrão de agrupamento lógico de funcionalidades
6. **Usar ícones consistentes** - Manter o padrão de iconografia em toda a aplicação

## 10. Conclusão

As melhorias implementadas na interface de usuário proporcionam uma experiência mais intuitiva, consistente e agradável para os usuários da plataforma 55Jam. A reorganização dos menus, as correções no tema escuro e as transições suaves contribuem para uma plataforma mais profissional e fácil de usar. 