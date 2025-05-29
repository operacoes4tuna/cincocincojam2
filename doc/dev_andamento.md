# Funcionalidades Pendentes de Implementação

Com base no mapeamento do projeto atual e comparando com os escopos de negócio e técnico, as seguintes funcionalidades ainda precisam ser implementadas:

## Ciclo 1 e 2 (Parcialmente Implementados)

- [x] Sistema de usuários (Admin, Professor, Aluno) - **Implementado**
- [x] CRUD de cursos e aulas - **Implementado**
- [x] Cadastro e autenticação - **Implementado**
- [x] Dashboard básico - **Implementado**
- [x] Visualização de cursos - **Implementado**
- [x] Matrícula de alunos (versão simples) - **Implementado**

## Ciclo 3 - Pagamentos e Financeiro (Pendente)

1. **Integração com Gateway de Pagamento**
   - Implementar fluxo de checkout com gateway real (Stripe, PagSeguro, MercadoPago)
   - Criar modelo `PaymentTransaction` relacionado a `Enrollment`
   - Desenvolver sistema de callbacks/webhooks para atualização de status

2. **Painel Financeiro do Professor**
   - Dashboard com métricas financeiras (vendas, valores recebidos e pendentes)
   - Listagem de alunos e status de pagamento
   - Sistema de lembretes e cobranças automáticas

3. **Histórico de Pagamentos do Aluno**
   - Interface para visualização de compras e status
   - Funcionalidade para solicitar cancelamento/estorno
   - Comprovantes de pagamento

4. **Emissão de Notas Fiscais**
   - Configuração de dados fiscais no perfil do professor
   - Integração com serviços de emissão de NF (eNotas, NFE.io)
   - Interface para emissão e download de notas

## Ciclo 4 - Agenda e Integração Google (Pendente)

1. **Sistema de Agenda**
   - Modelo para eventos/compromissos
   - Interface para CRUD de compromissos
   - Associação de eventos com alunos (participantes)

2. **Integração com Google Calendar**
   - Autenticação OAuth com Google
   - Sincronização bidirecional de eventos
   - Notificações de compromissos

3. **Visualização de Agenda**
   - Interface de calendário para professores
   - Visão do aluno para aulas agendadas

## Ciclo 5 - Chatbot e IA (Pendente)

1. **Assistente Virtual com IA**
   - Interface de chat na plataforma
   - Integração com OpenAI ou outro serviço de NLP
   - Consulta de dados do sistema (cursos, finanças, alunos, agenda)

2. **Integração com WhatsApp**
   - Webhook para receber mensagens do WhatsApp
   - Processamento e resposta automática
   - Envio de notificações importantes via WhatsApp

3. **Treinamento e Melhoria**
   - Sistema de feedback para melhorar respostas
   - Histórico de consultas para análise

## Melhorias Gerais Pendentes

1. **Aprimoramento da Interface**
   - Refinamento do tema claro/escuro já implementado
   - Aplicação consistente de estilos em todas as páginas
   - Versão responsiva para dispositivos móveis

2. **Página de Aplicativos**
   - Lista de aplicativos oficiais e parceiros
   - Links para download e informações

3. **Relatórios e Estatísticas**
   - Dashboard avançado para administradores
   - Exportação de dados em formatos como CSV
   - Gráficos e visualizações de métricas

4. **Configuração para Produção**
   - Migração para PostgreSQL (atualmente SQLite)
   - Configuração para deploy em ambiente de produção (Vercel ou similar)
   - Otimização de performance e segurança

## Prioridades Recomendadas

Com base no estágio atual do projeto, recomendo focalizar nas seguintes áreas:

1. **Integração de Pagamento** - Essencial para monetização dos cursos
2. **Painel Financeiro** - Importante para professores gerenciarem suas vendas
3. **Configuração para Produção** - Preparar o projeto para ambiente real
4. **Aprimoramento da Interface** - Melhorar experiência do usuário

As funcionalidades de Agenda, Chatbot e Integração com WhatsApp, embora importantes, podem ser implementadas nos ciclos posteriores, após o estabelecimento sólido das funcionalidades core de pagamento e gestão financeira.
