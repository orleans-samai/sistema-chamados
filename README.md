# Service Desk — Sistema de Chamados

Sistema web profissional de Service Desk inspirado em GLPI, Freshservice e Jira Service Management.
Feito em **Python/Flask** com **SQLite** (pronto para PostgreSQL), interface **Bootstrap 5** responsiva
com tema claro/escuro, **API REST** documentada com Swagger e **laboratório de treinamento N1/N2**.

## Como rodar

```powershell
cd sistema-chamados
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

# Banco de dados (migrations) + dados de demonstração
$env:FLASK_APP = "run.py"
.\.venv\Scripts\python -m flask db upgrade
.\.venv\Scripts\python -m flask seed

# Iniciar
.\.venv\Scripts\python run.py
```

Acesse **http://127.0.0.1:5000**.

### Usuários de demonstração (senha: `Senha@123`)

| Perfil        | E-mail                          | O que pode fazer                                      |
|---------------|---------------------------------|-------------------------------------------------------|
| Administrador | admin@empresa.com               | Tudo: usuários, categorias, SLA, auditoria, laboratório |
| Analista      | carlos.analista@empresa.com     | Assumir, atualizar, resolver e encerrar chamados       |
| Analista      | fernanda.analista@empresa.com   | Idem                                                   |
| Usuário       | joao@empresa.com                | Abrir chamados, comentar, anexar, avaliar              |
| Usuário       | maria@empresa.com / pedro@...   | Idem                                                   |

## Funcionalidades

- **Chamados**: número automático (`CH-AAAA-00000`), categorias/subcategorias, 4 prioridades,
  5 status, comentários públicos e internos, anexos, histórico completo (timeline),
  avaliação por estrelas, filtros avançados, paginação e exportação **Excel/PDF**.
- **SLA**: tempos de resposta e resolução por prioridade, prazos calculados na abertura,
  indicadores visuais (no prazo / em risco / vencido / cumprido / violado) e alertas no dashboard.
- **Dashboard**: cartões de indicadores, tempo médio de resolução e gráficos interativos
  (Chart.js): por status, por categoria, por analista e evolução mensal.
- **Base de conhecimento**: artigos, tutoriais e FAQ com categorias, tags, busca por
  palavras-chave e contador de visualizações.
- **Notificações**: sino na interface com central de notificações; arquitetura de canais
  plugáveis pronta para **e-mail, Microsoft Teams e Slack** (`app/services/notification_service.py`).
- **RBAC**: três perfis (admin, analista, usuário) com permissões aplicadas em todas as rotas.
- **Auditoria**: log de todas as ações (login, criação, edição, exclusão...) com IP e filtros.
- **Pesquisa global**: chamados, base de conhecimento e usuários (admin) na barra superior.
- **API REST**: token Bearer, CRUD de chamados, categorias e KB — documentação interativa
  em **/api/docs** (Swagger UI).
- **Laboratório N1/N2**: admins criam cenários simulados (redes, Windows, impressoras,
  Microsoft 365, Active Directory, segurança da informação) com gabarito e dicas, e geram
  chamados de treinamento para analistas praticarem o fluxo real de atendimento.
- **Interface**: sidebar lateral, tema claro/escuro persistente, layout responsivo para celular.
- **Recuperação de senha**: link com token expirável (em dev o link aparece na tela;
  em produção seria enviado pelo canal de e-mail).

## Estrutura do projeto

```
sistema-chamados/
├── run.py                  # ponto de entrada
├── config.py               # configurações (SQLite / PostgreSQL via DATABASE_URL)
├── app/
│   ├── __init__.py         # fábrica da aplicação
│   ├── extensions.py       # db, migrate, login, csrf
│   ├── models/             # 12 tabelas (users, roles, tickets, sla_rules...)
│   ├── routes/             # blueprints web (auth, tickets, admin, kb, lab...)
│   ├── api/                # API REST v1 + especificação OpenAPI
│   ├── services/           # regras de negócio (SLA, notificações, exportação...)
│   ├── repositories/       # consultas (filtros, estatísticas do dashboard)
│   ├── templates/          # Jinja2 + Bootstrap 5
│   ├── static/             # CSS (temas) e JS
│   └── seed.py             # carga de demonstração (flask seed)
├── migrations/             # Alembic / Flask-Migrate
├── scripts/smoke_test.py   # teste de fumaça dos fluxos principais
└── docs/ARQUITETURA.md     # documentação técnica
```

## API REST — exemplo rápido

```powershell
# 1. Obter token
curl -X POST http://127.0.0.1:5000/api/v1/auth/token `
  -H "Content-Type: application/json" `
  -d '{"email": "carlos.analista@empresa.com", "password": "Senha@123"}'

# 2. Listar chamados
curl http://127.0.0.1:5000/api/v1/tickets -H "Authorization: Bearer <token>"
```

## Migrando para PostgreSQL

1. Instale o driver: `pip install psycopg2-binary`
2. Defina a variável de ambiente antes de iniciar:
   `DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/servicedesk`
3. Rode `flask db upgrade` no banco novo.

## Testes

```powershell
.\.venv\Scripts\python scripts\smoke_test.py
```

Percorre 40 verificações: autenticação, RBAC, criação/resolução de chamados, SLA,
anexos, exportações, laboratório e API REST.
