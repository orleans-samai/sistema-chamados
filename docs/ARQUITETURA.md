# Arquitetura técnica — Service Desk

## Visão geral

Aplicação Flask organizada em camadas, com separação clara de responsabilidades:

```
Navegador ──► routes/ (blueprints)  ──► services/ (regras de negócio) ──► models/ (SQLAlchemy)
API REST  ──► api/v1 (token Bearer) ──┘            │
                                       repositories/ (consultas e estatísticas)
```

- **routes/** valida entrada, controla permissões e renderiza templates. Não contém regra de negócio.
- **services/** concentra as regras: criação de chamado (número, SLA, histórico, notificação),
  mudança de status, comentários, auditoria, exportações.
- **repositories/** concentra consultas reutilizáveis: visibilidade por perfil, filtros da
  listagem e agregações do dashboard (portáveis entre SQLite e PostgreSQL).
- **models/** define as 12 tabelas e propriedades derivadas (ex.: estado do SLA).

## Banco de dados (12 tabelas)

| Tabela            | Conteúdo                                                        |
|-------------------|-----------------------------------------------------------------|
| `roles`           | Perfis: admin, analista, usuario                                 |
| `users`           | Usuários, hash de senha (Werkzeug), token de API, departamento   |
| `departments`     | Departamentos da empresa                                         |
| `categories`      | Categorias de chamados                                           |
| `subcategories`   | Subcategorias (FK para categories)                               |
| `sla_rules`       | Minutos de resposta/resolução por prioridade                     |
| `tickets`         | Chamados: número, prioridade, status, prazos, solução, avaliação |
| `ticket_comments` | Comentários públicos e internos                                  |
| `ticket_history`  | Timeline de alterações (campo, valor antigo, valor novo)         |
| `attachments`     | Anexos (arquivo no disco em `uploads/<ticket_id>/`)              |
| `knowledge_base`  | Artigos, tutoriais e FAQ com tags                                |
| `notifications`   | Notificações internas por usuário                                |
| `audit_logs`      | Auditoria de todas as ações com IP                               |
| `lab_scenarios`   | Cenários do laboratório de treinamento N1/N2                     |

Migrations gerenciadas pelo Flask-Migrate (Alembic) em `migrations/`.

## Decisões de projeto

### SLA calculado, não agendado
Os prazos (`response_due_at`, `resolution_due_at`) são gravados na abertura do chamado a
partir de `sla_rules`. O **estado** do SLA (no prazo, em risco, vencido, cumprido, violado)
é calculado em tempo de leitura (`sla_service.sla_state`), sem necessidade de jobs em
background. Os alertas do dashboard usam essa mesma função.

### Notificações com canais plugáveis
`NotificationService.channels` é uma lista de implementações de `NotificationChannel`.
Hoje só `DatabaseChannel` está ativo (sino da interface). Para ativar e-mail, Teams ou
Slack, basta implementar `send()` no stub correspondente e registrar o canal — nenhuma
outra parte do código muda.

### RBAC simples e explícito
Três perfis com helpers no modelo (`is_admin`, `is_analyst`, `is_staff`). As rotas
aplicam as regras: usuário comum só enxerga os próprios chamados
(`TicketRepository.visible_query`), analista vê a fila completa e atua nos chamados sem
dono ou atribuídos a ele, admin faz tudo.

### Segurança
- Senhas com hash (Werkzeug, PBKDF2).
- CSRF em todos os formulários (Flask-WTF); a API REST usa token Bearer e fica isenta.
- Tokens de redefinição de senha expiram em 1h (itsdangerous, assinados com SECRET_KEY).
- Upload com lista de extensões permitidas, nome aleatório no disco e limite de 16 MB.
- Download de anexos valida a permissão sobre o chamado.
- Auditoria de login/logout e de todas as operações de escrita.

### Laboratório de treinamento
Cenários (`lab_scenarios`) viram chamados reais com `is_training=True` e FK para o
cenário. O analista atende pelo fluxo normal; o gabarito (`expected_solution`) aparece
apenas para admins, tanto na página do cenário quanto no próprio chamado.

### Compatibilidade SQLite → PostgreSQL
- Conexão definida por `DATABASE_URL` (config.py).
- Agregações do dashboard feitas em Python quando a função SQL não é portável
  (ex.: série mensal), evitando `strftime`/`to_char` específicos de cada banco.

## Fluxo de um chamado

```
Aberto ──assumir──► Em andamento ──► Aguardando usuário ──► Em andamento
                        │
                        └──resolver (exige solução)──► Resolvido ──► Fechado
                                                          │
                                            avaliação (1–5 estrelas)
Reabertura: qualquer status aberto limpa resolved_at/closed_at.
```

Cada transição grava `ticket_history`, dispara notificações ao solicitante e ao analista
e registra auditoria.
