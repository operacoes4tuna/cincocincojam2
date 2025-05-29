# Regras de Desenvolvimento - CincoCincoJAM 2.0

Este documento estabelece as regras e diretrizes que devem ser seguidas por todos os desenvolvedores que trabalham no projeto CincoCincoJAM 2.0, incluindo assistentes de IA. Estas regras devem ser consultadas e respeitadas durante todo o ciclo de desenvolvimento.

## 1. Princípios Fundamentais

### 1.1. Preservação da Estrutura Existente
- **Não modificar** layouts, estruturas ou funcionalidades já implementadas sem solicitação explícita do responsável pelo projeto
- **Evitar refatorações** que possam impactar o comportamento existente sem aprovação prévia
- **Documentar claramente** qualquer modificação necessária em código ou estrutura existente

### 1.2. Consistência Visual e Funcional
- **Seguir rigorosamente** os padrões de design já estabelecidos no projeto
- **Manter uniforme** a experiência do usuário em todas as seções do sistema
- **Reutilizar componentes** visuais e padrões de interação já existentes
- **Respeitar o sistema de temas** (claro/escuro) em qualquer nova interface

### 1.3. Integração Harmoniosa
- **Novas funcionalidades** devem se integrar naturalmente ao fluxo existente
- **Adaptar novos elementos** para parecerem parte original do sistema
- **Evitar disrupções** na experiência do usuário com mudanças bruscas

## 2. Diretrizes Específicas de Desenvolvimento

### 2.1. Estrutura de Templates
- Seguir a hierarquia de templates já estabelecida: `/templates/[app_name]/[template_name].html`
- Manter padrão de extends e includes consistente com os templates existentes
- Preservar a estrutura de blocos (blocks) já definida

### 2.2. Estilo Visual
- Utilizar exclusivamente os componentes Bootstrap já em uso no projeto
- Respeitar as classes CSS personalizadas existentes
- Garantir compatibilidade total com o sistema de alternância de temas
- Não introduzir novas bibliotecas de UI sem aprovação explícita

### 2.3. Modelos e Bancos de Dados
- Seguir convenções de nomenclatura já estabelecidas para modelos, campos e tabelas
- Documentar novas migrações de forma clara e concisa
- Evitar alterações em modelos existentes; quando necessárias, preferir adicionar campos ao invés de modificar

### 2.4. Formulários
- Utilizar crispy-forms com Bootstrap5 para todos os formulários
- Manter consistência na apresentação, validação e feedback de formulários
- Seguir o padrão de mensagens de erro/sucesso já implementado

### 2.5. URLs e Navegação
- Organizar URLs de forma consistente com o padrão existente
- Integrar novas páginas no sistema de navegação atual
- Manter breadcrumbs e hierarquia de navegação coerentes

## 3. Processo de Desenvolvimento

### 3.1. Antes de Implementar
- Analisar o código existente relacionado à funcionalidade a ser desenvolvida
- Identificar padrões e convenções já em uso
- Planejar a implementação respeitando a arquitetura atual

### 3.2. Durante a Implementação
- Consultar frequentemente templates e implementações semelhantes como referência
- Testar compatibilidade com temas claro e escuro
- Verificar responsividade em diferentes tamanhos de tela

### 3.3. Após a Implementação
- Revisar o código para garantir aderência a estas regras
- Testar a integração com funcionalidades existentes
- Documentar novas funcionalidades ou alterações significativas

## 4. Guia de Referência Rápida

- **Templates**: Utilizar base.html e estrutura de blocos existente
- **CSS**: Usar apenas classes Bootstrap e estilos já definidos
- **JavaScript**: Seguir padrões de organização e nomeação existentes
- **Views**: Manter consistência com CBVs ou FBVs conforme o padrão da app
- **Modelos**: Seguir convenções de nomenclatura e relações já estabelecidas
- **Formulários**: Manter aparência e comportamento consistentes com formulários existentes
- **Temas**: Testar e garantir compatibilidade com alternância de temas

---

**Importante**: Estas regras devem ser seguidas estritamente para manter a integridade, coesão e qualidade do projeto. Qualquer exceção deve ser explicitamente aprovada pelo responsável técnico.
