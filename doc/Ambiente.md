# 📄 Documentação do Ambiente de Desenvolvimento

## Projeto: **Plataforma 55JAM cliente Gian Correa**

---

## ⚙️ Tecnologias Usadas

* **Framework:** Django 4.2.10
* **Banco de Dados:** PostgreSQL
* **Hospedagem:** [Render](https://render.com/)
* **Git:** Controle de versão (GitHub)
* **Deploy automático:** Via Render
* **Organização de tarefas:** Monday.com

---

## 🌐 Ambientes do Projeto

### 🔸 Homologação

* **Servidor:** `homolog_cincocincojam2`
* **Banco de dados:** `homolog_cincocincojam2_db`
* **Branch usada:** `develop`
* **Deploy:** Automático ao atualizar a branch `develop`
* **Acesso:** [https://dev-lab7cordas.55jam.com.br/](https://dev-lab7cordas.55jam.com.br/)

### 🔸 Produção

* **Servidor:** `cincocincojam2`
* **Banco de dados:** `cincocincojam2_db`
* **Branch usada:** `main`
* **Deploy:** Automático após merge da `develop` na `main`
* **Acesso:** [https://lab7cordas.55jam.com.br/](https://lab7cordas.55jam.com.br/)

---

## 🔐 Acesso ao Render

* O acesso ao [Render](https://render.com/) é feito com login via GitHub.
* Use a conta da **4Tuna** para acessar.

---

## 🌱 Gitflow (Fluxo com Git)

1. **Criar a branch de desenvolvimento**

   * Sempre comece a partir da `develop`.
   * Nome da branch deve seguir o padrão:

     ```
     feat/nome_da_funcionalidade
     ```

2. **Desenvolvimento da funcionalidade**

   * Quando terminar, avise no Monday que está pronto e informe o nome da branch.

3. **Testes em homologação**

   * Após o merge com a `develop`, o sistema é atualizado automaticamente no ambiente de homologação:
     [https://dev-lab7cordas.55jam.com.br/](https://dev-lab7cordas.55jam.com.br/)

4. **Se estiver tudo certo**, faça o merge da `develop` na `main`.

5. **Produção**

   * O servidor de produção é atualizado automaticamente:
     [https://lab7cordas.55jam.com.br/](https://lab7cordas.55jam.com.br/)

---

## ✅ Dicas Finais

* Nunca suba o arquivo `.env` para o repositório.
 
* As variáveis sensíveis estão configuradas diretamente no Render, temos variáveis diferente para cadas ambiente homologação e produção incluindo banco de dados.

---

* Atualizado 23/07/2025 por Bruno Nascimento 
