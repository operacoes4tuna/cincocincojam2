# Versão Organizada e Simplificada do Projeto
Este documento tem como objetivo estruturar de forma clara e minimalista as funcionalidades do projeto "CincoCincoJAM 2.0", definindo etapas de desenvolvimento enxutas e incrementais. A ênfase está em lançar uma plataforma extremamente simples, porém funcional, que sirva de base para evoluções futuras.

⸻

## Visão Geral

A plataforma tem três perfis principais de usuários:
1. **Professores**
   - Cadastram seus cursos e aulas (exclusivamente via links de vídeo do YouTube).
   - Gerenciam inscrições de alunos, bem como pagamentos (matrícula, mensalidades) e status financeiro de cada aluno.
   - Podem emitir notas fiscais (quando desejarem) de forma integrada.
   - Têm acesso a uma agenda que pode ser integrada ao Google Calendar.
   - Podem interagir com um chatbot com linguagem natural para consultar informações de cursos, finanças, alunos e agenda.
   - Têm um dashboard com estatísticas gerais (número de cursos, alunos, vendas etc.).
2. **Alunos**
   - Cadastram-se para visualizar os cursos disponíveis.
   - Podem comprar cursos (pagamento de matrícula e mensalidade quando aplicável).
   - Têm um painel com histórico de pagamentos/compras e a possibilidade de cancelar ou pedir estorno.
   - Possuem um dashboard para acessar os cursos já adquiridos.
3. **Administradores**
   - Podem cadastrar, editar e remover professores, alunos e cursos.
   - Possuem um dashboard com informações consolidadas de todos os cadastros e compras.

Além disso, há páginas gerais de interesse:
- Página de Cursos: lista todos os cursos disponíveis, com filtros e buscas, permitindo o acesso à página de venda de cada curso.
- Página de Aplicativos: exibe links, ícones e descrições de aplicativos oficiais e parceiros da plataforma.

⸻

## Princípios de Simplicidade
1. **Cadastro Inicial Simplificado**
   - Para todos os perfis (professor, aluno, administrador), basta nome, e-mail e senha.
   - Sem validações complexas (como confirmação de e-mail) na versão inicial.
2. **Cursos Básicos**
   - Cada curso tem apenas um conjunto de aulas que consistem em links de vídeo do YouTube e um valor de cobrança definido.
   - A página de venda do curso deve ser uma página única (one-page) apresentando as informações cadastrais fornecidas.
3. **Financeiro Essencial**
   - Registro de compras, status de pagamento (em dia, atrasado, previsto), e controle de recebíveis para o professor.
   - Integração simples com um sistema de cobrança (fornecido por um integrador de pagamento).
   - Possibilidade de emitir notas fiscais se o professor desejar.
4. **Agenda Integrada**
   - Campos básicos: dia, horário, nome do compromisso, participantes (alunos) e local (apenas texto).
   - Integração opcional com a agenda do Google (simples sincronização de eventos).
5. **Chatbot/IA**
   - Permitir que o professor consulte informações sobre cursos, finanças, alunos e agenda.
   - Integração com WhatsApp (inicialmente algo simples que possa responder dúvidas sobre dados básicos do sistema).

⸻

## Proposta de Ciclos de Desenvolvimento

A seguir, sugerimos um roadmap dividido em ciclos curtos e funcionais, nos quais cada entrega seja totalmente usável e sirva de alicerce para o próximo ciclo.

### Ciclo 1 – Fundamentos e Cadastro
1. **Cadastro de Usuário (Aluno/Professor/Administrador)**
   - Formulário de registro com nome, e-mail e senha (sem verificação de e-mail).
   - Login básico (usuário/senha).
2. **Gerenciamento de Usuários (Administrador)**
   - Listagem simples para visualizar, editar ou remover usuários (professores e alunos).
3. **Perfil do Usuário (Professor)**
   - Formulário para edição de informações essenciais (dados pessoais, dados para emissão de nota fiscal – opcional, mas já previsto).
4. **Dashboard Inicial (Professor/Aluno)**
   - Exibição de um painel básico com informações mínimas (bem-vindo, número de cursos disponíveis / adquiridos etc.).

**Resultado esperado ao final do Ciclo 1:**
- Professores e Alunos podem se cadastrar e fazer login.
- Administradores podem gerenciar os cadastros.
- Professores têm acesso a um perfil simples.

⸻

### Ciclo 2 – Curso e Conteúdo
1. **Cadastro e Edição de Cursos (Professor)**
   - Nome do curso, valor, descrição curta.
   - Status: rascunho ou publicado.
2. **Cadastro e Edição de Aulas (Professor)**
   - Inclusão de aulas ao curso, definindo título e URL de vídeo do YouTube.
   - Possibilidade de marcar aulas como rascunho ou publicadas (para só serem visíveis no curso final quando publicadas).
3. **Página de Listagem de Cursos (Pública/Aluno)**
   - Listar cursos publicados, com opção de filtro e busca.
   - Exibir título, breve descrição e valor.
4. **Página de Detalhes/Venda do Curso (Pública/Aluno)**
   - Exibir todas as informações do curso.
   - Botão/fluxo de compra inicial (integração básica com o sistema de pagamento).

**Resultado esperado ao final do Ciclo 2:**
- Professores podem criar e publicar cursos com aulas via links de vídeo.
- Alunos podem visualizar e comprar cursos.
- Existe uma página pública de cursos com detalhes e checkout básico.

⸻

### Ciclo 3 – Pagamentos e Financeiro
1. **Integração com Pagamento**
   - Fluxo de compra do curso direcionado para o integrador de pagamento escolhido.
   - Retorno do status de pagamento (sucesso, falha, pendente).
2. **Painel Financeiro do Professor**
   - Listagem de vendas de cursos, valores recebidos, valores pendentes.
   - Lista de alunos matriculados e seu status de pagamento (em dia, atrasado, previsto).
   - Mecanismo básico de gerar cobranças e envio de lembretes automáticos (podendo usar o integrador de pagamento).
3. **Histórico de Pagamentos do Aluno**
   - Visão de todos os cursos adquiridos, status de pagamento, datas e possibilidade de solicitar cancelamento/estorno.
4. **Emissão de Notas Fiscais**
   - Configuração opcional no perfil do professor (CNPJ, dados de emissão).
   - Botão para emissão de nota fiscal de cada venda (quando habilitado).

**Resultado esperado ao final do Ciclo 3:**
- O fluxo de compra está completo, com pagamento real integrado.
- Professores têm um painel para acompanhar o status financeiro.
- Alunos podem visualizar seus pagamentos e gerenciar pedidos de estorno.

⸻

### Ciclo 4 – Agenda e Integração Google
1. **Agenda do Professor**
   - Criação de compromissos básicos: dia, horário, descrição, participantes, local.
2. **Integração com Google Calendar (Opcional)**
   - Sincronizar automaticamente os compromissos para o Google Calendar.
   - Atualizar plataforma quando há modificações no Google Calendar (funcionalidade mínima).
3. **Listagem de Agendas e Compromissos**
   - Visão simples em formato de calendário ou lista para o Professor.

**Resultado esperado ao final do Ciclo 4:**
- Professores conseguem organizar suas aulas/reuniões dentro da plataforma.
- Possibilidade de manter essas agendas sincronizadas com o Google Calendar.

⸻

### Ciclo 5 – Chatbot e IA
1. **Chatbot com Linguagem Natural**
   - Interface mínima para o professor digitar perguntas sobre cursos, status de alunos, finanças e agenda.
   - Retorno do sistema com respostas objetivas, integradas aos dados da plataforma.
2. **Integração com WhatsApp**
   - Permitir que o professor use o WhatsApp para enviar mensagens para o chatbot, e este responder com base nos dados do sistema.
   - Configuração inicial de webhook e rotas de integração.
3. **Treinamento e Melhoria de Respostas**
   - Ajuste de prompts para que o chatbot interprete e retorne informações corretas (Ex.: "Qual o status do pagamento do aluno X?").

**Resultado esperado ao final do Ciclo 5:**
- Professores podem interagir via chatbot (na plataforma ou WhatsApp) para acessar informações.
- O sistema consegue fornecer dados estruturados ou relatórios de forma automática.

⸻

## Jornadas de Usuário (Exemplos)

### Jornada do Professor (Simples)
1. Cadastro / Login
2. Cria seu perfil
3. Cadastra um curso
4. Adiciona aulas (links YouTube)
5. Publica o curso
6. Recebe matrículas
7. Acompanha pagamentos
8. Emite nota fiscal (se desejar)
9. Agenda compromissos de aulas particulares
10. Consulta dados via Chatbot

### Jornada do Aluno (Simples)
1. Cadastro / Login
2. Acessa a página de cursos
3. Visualiza e compra um curso
4. Recebe confirmação de pagamento
5. Acompanha o status do curso no dashboard
6. Assistência via suporte (caso precise)

### Jornada do Administrador (Simples)
1. Login
2. Consulta lista de professores e alunos
3. Edita ou remove usuários
4. Consulta dados consolidados de vendas
5. Gera relatórios ou estatísticas globais

⸻

## Pontos de Atenção e Simplificação
- **Validação de Dados:** Nesta versão inicial, não faremos validação de e-mail, documentos etc. Isso reduz a complexidade e agiliza o lançamento.
- **Interface de Pagamento:** Usar uma única integração de pagamento para todo o projeto, sem criar múltiplas opções no MVP.
- **Emissão de Nota Fiscal:** Se a integração com emissão de notas for complexa, iniciar apenas com um modelo simples de nota ou com campos prontos para exportar para algum sistema de emissão.
- **Chatbot/IA:** Uma primeira versão pode usar apenas uma camada de FAQ ou dados tabulares antes de passar para uma IA mais robusta. A ideia é manter funcional, mas simples.
- **Agenda:** Na primeira entrega, pode ser apenas um CRUD básico de compromissos sem necessidade de sincronização real-time com Google. Posteriormente, refinamos a integração.
- **Design Enxuto:** Manter telas minimalistas, sem sobrecarregar de funcionalidades ou dados irrelevantes.

⸻

## Conclusão

O objetivo é entregar um MVP extremamente simples, validando a necessidade e o interesse dos professores e alunos. Cada ciclo proposto traz uma entrega completa e utilizável, permitindo que o produto seja testado, avaliado e receba feedback real antes de passar ao próximo nível de complexidade.

A plataforma será robusta o bastante para atender às necessidades básicas de um Professor de música que quer hospedar seu curso online, gerenciar alunos e pagamentos, mas sem exagerar nas funcionalidades. A meta é construir uma base sólida e iterar gradualmente.
