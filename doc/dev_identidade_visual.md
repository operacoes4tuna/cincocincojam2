# Implementação de Identidade Visual - 55Jam

Este documento descreve a implementação da identidade visual da marca "Baile 55" na plataforma 55Jam, incluindo as adaptações realizadas para exibição adequada do logo em diferentes contextos e temas.

## 1. Visão Geral

A implementação consiste na integração do logo "Baile 55" como parte da identidade visual da plataforma 55Jam, com suporte completo para os temas claro e escuro, responsividade em diferentes dispositivos, e adaptações adequadas na interface.

## 2. Arquivos Implementados

### 2.1. Arquivos de Imagem
- `static/img/logo/logo-baile55-branco.png` - Versão branca do logo para uso em fundos escuros
- `static/img/logo/logo-baile55-preto.png` - Versão preta do logo para uso em fundos claros

### 2.2. Modificações em Arquivos Existentes
- `templates/base.html` - Inserção do logo na barra de navegação
- `static/css/main.css` - Estilos para exibição adequada do logo nos diferentes temas
- `templates/home.html` - Ajustes na página inicial
- `scheduler/templates/scheduler/participant_list.html` - Adaptação dos modais para suportar temas

## 3. Detalhes da Implementação

### 3.1. Barra de Navegação

A barra de navegação foi modificada para incluir o logo com troca automática entre versões clara e escura:

```html
<a class="navbar-brand" href="{% url 'home' %}">
    <img src="{% static 'img/logo/logo-baile55-branco.png' %}" alt="55Jam" class="logo-light">
    <img src="{% static 'img/logo/logo-baile55-preto.png' %}" alt="55Jam" class="logo-dark">
</a>
```

### 3.2. Estilos CSS

Foram adicionados estilos específicos para controlar a exibição do logo:

```css
/* Ajuste da navbar para acomodar logo */
.navbar {
    min-height: 100px;
    padding-top: 20px;
    padding-bottom: 20px;
}

/* Logo BAILE 55 versões claro/escuro */
.navbar-brand {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    margin-right: 1.5rem;
}

.navbar-brand img {
    height: 90px;
    width: auto;
    max-width: 100%;
    object-fit: contain;
}

.logo-dark {
    display: none;
}

.logo-light {
    display: block;
}

/* Na navbar escura, use o logo claro */
.navbar-dark .logo-light {
    display: block;
}

.navbar-dark .logo-dark {
    display: none;
}

/* Na navbar clara, use o logo escuro */
.navbar-light .logo-light {
    display: none;
}

.navbar-light .logo-dark {
    display: block;
}

@media (prefers-color-scheme: dark) {
    body:not(.navbar-dark):not(.navbar-light) .logo-dark {
        display: block;
    }
    
    body:not(.navbar-dark):not(.navbar-light) .logo-light {
        display: none;
    }
}
```

### 3.3. Responsividade para Dispositivos Móveis

Foram adicionadas regras específicas para adaptar o logo em telas menores:

```css
@media (max-width: 767px) {
    .navbar {
        min-height: 80px;
        padding-top: 15px;
        padding-bottom: 15px;
    }
    
    .navbar-brand img {
        height: 70px;
    }
}
```

### 3.4. Adaptação de Modais para Temas

Os modais na aplicação foram adaptados para respeitar os temas claro e escuro:

```css
/* Compatibilidade de modais com temas */
.modal-header {
    border-bottom: 1px solid var(--bs-border-color);
    color: var(--bs-body-color);
    background-color: var(--bs-body-bg);
}

.modal-content {
    background-color: var(--bs-body-bg);
    color: var(--bs-body-color);
}

.modal-body {
    background-color: var(--bs-body-bg);
}

.modal-footer {
    border-top: 1px solid var(--bs-border-color);
    background-color: var(--bs-body-bg);
}

.list-group-item {
    background-color: var(--bs-body-bg);
    color: var(--bs-body-color);
    border-color: var(--bs-border-color);
}

.list-group {
    background-color: var(--bs-body-bg);
    color: var(--bs-body-color);
}
```

Os botões de fechamento dos modais também foram ajustados para usar a classe `btn-close` sem a especificação de cor `btn-close-white`, permitindo que o Bootstrap aplique automaticamente a cor correta com base no tema atual.

## 4. Distinção entre Marca e Plataforma

É importante notar a distinção implementada entre:

1. **"Baile 55"** - A marca visual representada pelo logo
2. **"55Jam"** - O nome da plataforma utilizado em textos, títulos e referências

Esta distinção foi cuidadosamente mantida em toda a implementação, assegurando que o logo "Baile 55" seja usado como elemento visual, enquanto as referências textuais continuam utilizando o nome "55Jam".

## 5. Sistema de Troca de Temas

A implementação garante compatibilidade total com o sistema de troca de temas (claro/escuro) da plataforma:

- **Tema Claro**: Exibe automaticamente o logo preto e elementos de interface em tons claros
- **Tema Escuro**: Exibe automaticamente o logo branco e elementos de interface em tons escuros
- **Modo Automático**: Detecta a preferência do sistema operacional e aplica o tema adequado
- **Componentes Dinâmicos**: Modais, listagens e botões se adaptam automaticamente ao tema atual

## 6. Boas Práticas Aplicadas

### 6.1. Preservação da Estrutura
- Mantida a estrutura básica da barra de navegação e modais
- Ajustes realizados sem alterar o comportamento ou funcionalidade existente

### 6.2. Consistência Visual
- Logo e componentes adaptados para manter harmonia com o design existente
- Espaçamentos e proporções ajustados para integração natural

### 6.3. Responsividade
- Implementação com adaptação para diferentes tamanhos de tela
- Testes realizados em resoluções desktop e mobile

### 6.4. Variáveis CSS
- Utilização de variáveis CSS do Bootstrap (`--bs-body-bg`, `--bs-body-color`, etc.) para consistência com o tema
- Evitando cores fixas para garantir compatibilidade com ambos os temas

## 7. Considerações Técnicas

### 7.1. Formato de Imagem
- Utilizado formato PNG com transparência para melhor integração visual
- Manutenção da nitidez em diferentes escalas e resoluções

### 7.2. Estrutura de Diretórios
- Criado diretório específico `static/img/logo/` para organização das imagens de identidade visual
- Facilidade para futuras atualizações ou extensões da identidade visual

### 7.3. Compatibilidade de Modais
- Removidas classes fixas de cor (`bg-primary`, `text-white`) dos cabeçalhos de modais
- Substituídas por variáveis CSS que se adaptam ao tema atual
- Botões de fechamento (`btn-close`) adaptados para detectar automaticamente o tema

---

**Importante**: Quaisquer modificações futuras na identidade visual e temas devem seguir o padrão estabelecido nesta implementação, usando variáveis CSS do Bootstrap em vez de cores fixas, para manter a consistência visual e a compatibilidade com o sistema de temas. 