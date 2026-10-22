<div align="center">

# 🎫 Service Desk — Sistema de Chamados

**Plataforma web de Service Desk com SLA, base de conhecimento, API REST e laboratório de treinamento N1/N2.**

Inspirada em GLPI, Freshservice e Jira Service Management.

<br />

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![SQLite](https://img.shields.io/badge/SQLite-PostgreSQL_ready-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](#-migrando-para-postgresql)

[Sobre](#-sobre) •
[Funcionalidades](#-funcionalidades) •
[Tecnologias](#-tecnologias) •
[Como executar](#-como-executar) •
[API REST](#-api-rest) •
[Estrutura](#-estrutura-do-projeto)

</div>

---

## 📌 Sobre

O **Service Desk** é um sistema completo de gestão de chamados de TI, feito em **Python/Flask**. Ele cobre o ciclo inteiro de um atendimento: abertura, triagem, acompanhamento de SLA, resolução, avaliação e auditoria.

Além do uso no dia a dia, o projeto traz um **laboratório de treinamento N1/N2**: o administrador cria cenários simulados (redes, Windows, Microsoft 365, Active Directory, impressoras, segurança) e gera chamados de treino para que analistas pratiquem o fluxo real de suporte.


<table>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/orleans-samai/orleans-samai.github.io/main/img/telas/chamados-painel.webp" width="260" alt="Dashboard" /><br /><sub>Dashboard</sub></td>
<td align="center"><img src="https://raw.githubusercontent.com/orleans-samai/orleans-samai.github.io/main/img/telas/chamados-lista.webp" width="260" alt="Lista de chamados" /><br /><sub>Lista de chamados</sub></td>
<td align="center"><img src="https://raw.githubusercontent.com/orleans-samai/orleans-samai.github.io/main/img/telas/chamados-lab.webp" width="260" alt="Laboratório N1/N2" /><br /><sub>Laboratório N1/N2</sub></td>
</tr>
</table>

---

## ✨ Funcionalidades

| Módulo | O que oferece |
|---|---|
| 🎫 **Chamados** | Numeração automática (`CH-AAAA-00000`), categorias e subcategorias, 4 prioridades, 5 status, comentários públicos e internos, anexos, timeline completa, avaliação por estrelas, filtros, paginação e exportação **Excel/PDF** |
| ⏱️ **SLA** | Tempos de resposta e resolução por prioridade, prazos calculados na abertura e indicadores visuais (no prazo, em risco, vencido, cumprido, violado) |
| 📊 **Dashboard** | Cartões de indicadores, tempo médio de resolução e gráficos interativos com Chart.js (por status, categoria, analista e evolução mensal) |
| 📚 **Base de conhecimento** | Artigos, tutoriais e FAQ com categorias, tags, busca por palavras-chave e contador de visualizações |
| 🔔 **Notificações** | Central de notificações na interface, com arquitetura de canais plugáveis pronta para e-mail, Microsoft Teams e Slack |
| 🔐 **RBAC** | Três perfis (administrador, analista e usuário) com permissões aplicadas em todas as rotas |
| 🧾 **Auditoria** | Registro de todas as ações (login, criação, edição, exclusão) com IP e filtros |
| 🔎 **Pesquisa global** | Busca em chamados, base de conhecimento e usuários direto na barra superior |
| 🔌 **API REST** | Autenticação por token Bearer, CRUD de chamados, categorias e KB, com documentação Swagger em `/api/docs` |
| 🧪 **Laboratório N1/N2** | Cenários simulados com gabarito e dicas, que geram chamados de treinamento |
| 🎨 **Interface** | Sidebar lateral, tema claro/escuro persistente e layout responsivo |
| 🔑 **Recuperação de senha** | Link com token expirável |

---

## 🧰 Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Python, Flask 3, Flask-Login, Flask-WTF (CSRF) |
| Banco de dados | SQLAlchemy + Flask-Migrate (Alembic), SQLite por padrão e pronto para PostgreSQL |
| Frontend | Jinja2, Bootstrap 5, Chart.js |
| Exportação | openpyxl (Excel) e ReportLab (PDF) |
| API | REST v1 com especificação OpenAPI e Swagger UI |

---

## 🚀 Como executar

### Pré-requisitos

- Python 3.10 ou superior
- Git

### Instalação

```powershell
git clone https://github.com/orleans-samai/sistema-chamados.git
cd sistema-chamados

python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

# Cria as tabelas e carrega os dados de demonstração
$env:FLASK_APP = "run.py"
.\.venv\Scripts\python -m flask db upgrade
.\.venv\Scripts\python -m flask seed

# Inicia o servidor
.\.venv\Scripts\python run.py
```

> 💡 No Linux/macOS, ative o ambiente com `source .venv/bin/activate` e use `export FLASK_APP=run.py`.

Acesse **http://127.0.0.1:5000**.

### 👥 Usuários de demonstração

Todos usam a senha `Senha@123`.

| Perfil | E-mail | Permissões |
|---|---|---|
| 🛡️ Administrador | `admin@empresa.com` | Tudo: usuários, categorias, SLA, auditoria e laboratório |
| 🧑‍💻 Analista | `carlos.analista@empresa.com` | Assumir, atualizar, resolver e encerrar chamados |
| 🧑‍💻 Analista | `fernanda.analista@empresa.com` | Idem |
| 🙋 Usuário | `joao@empresa.com` | Abrir chamados, comentar, anexar e avaliar |
| 🙋 Usuário | `maria@empresa.com` | Idem |

### 🔧 Variáveis de ambiente

| Variável | Descrição | Padrão |
|---|---|---|
| `SECRET_KEY` | Chave de sessão do Flask. **Troque em produção.** | valor de desenvolvimento |
| `DATABASE_URL` | String de conexão do banco | SQLite local |

---

## 🔌 API REST

A documentação interativa fica em **`/api/docs`** (Swagger UI).

```powershell
# 1. Obter o token
curl -X POST http://127.0.0.1:5000/api/v1/auth/token `
  -H "Content-Type: application/json" `
  -d '{"email": "carlos.analista@empresa.com", "password": "Senha@123"}'

# 2. Listar chamados
curl http://127.0.0.1:5000/api/v1/tickets -H "Authorization: Bearer <token>"
```

---

## 🐘 Migrando para PostgreSQL

1. Instale o driver: `pip install psycopg2-binary`
2. Defina a conexão antes de iniciar:
   ```
   DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/servicedesk
   ```
3. Rode `flask db upgrade` no banco novo.

---

## 🧪 Testes

```powershell
.\.venv\Scripts\python scripts\smoke_test.py
```

O teste de fumaça percorre cerca de 40 verificações: autenticação, RBAC, criação e resolução de chamados, SLA, anexos, exportações, laboratório e API REST.

Para criar um usuário pela linha de comando, use `scripts/create_user.py`.

---

## 📁 Estrutura do projeto

```
sistema-chamados/
├── run.py                  # Ponto de entrada
├── config.py               # Configurações (SQLite / PostgreSQL via DATABASE_URL)
├── app/
│   ├── __init__.py         # Fábrica da aplicação
│   ├── extensions.py       # db, migrate, login, csrf
│   ├── models/             # Usuários, chamados, SLA, catálogo, KB, laboratório, auditoria...
│   ├── routes/             # Blueprints web (auth, tickets, admin, kb, lab...)
│   ├── api/                # API REST v1 + especificação OpenAPI
│   ├── services/           # Regras de negócio (SLA, notificações, exportação, auditoria)
│   ├── repositories/       # Consultas (filtros e estatísticas do dashboard)
│   ├── templates/          # Jinja2 + Bootstrap 5
│   ├── static/             # CSS (temas) e JavaScript
│   └── seed.py             # Carga de demonstração (flask seed)
├── migrations/             # Alembic / Flask-Migrate
├── scripts/                # smoke_test.py e create_user.py
└── docs/ARQUITETURA.md     # Documentação técnica
```

Para detalhes de arquitetura, veja [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

---

## 👤 Autor

**Orleans Samai**

[![GitHub](https://img.shields.io/badge/GitHub-orleans--samai-181717?style=flat-square&logo=github)](https://github.com/orleans-samai)

<div align="center">

<sub>Feito com 💙 por Orleans Samai</sub>

</div>
