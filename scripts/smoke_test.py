"""Teste de fumaça: percorre os principais fluxos da aplicação.

Uso: .venv\\Scripts\\python scripts\\smoke_test.py
Requer o banco já migrado e populado (flask db upgrade + flask seed).
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

app = create_app()
app.config["WTF_CSRF_ENABLED"] = False  # facilita o POST nos testes
app.config["SERVER_NAME"] = "localhost"

failures = []


def check(condition, label, extra=""):
    status = "OK " if condition else "FALHOU"
    print(f"[{status}] {label}{' — ' + extra if extra and not condition else ''}")
    if not condition:
        failures.append(label)


def login(client, email, password="Senha@123"):
    return client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=True
    )


with app.test_client() as client:
    # ---------- autenticação ----------
    r = client.get("/login")
    check(r.status_code == 200, "GET /login")

    r = client.post("/login", data={"email": "admin@empresa.com", "password": "errada"})
    check(r.status_code == 401, "Login com senha errada retorna 401")

    r = login(client, "admin@empresa.com")
    check(r.status_code == 200 and "Dashboard".encode() in r.data, "Login admin + dashboard")

    # ---------- chamados ----------
    r = client.get("/chamados/")
    check(r.status_code == 200 and b"CH-" in r.data, "Listagem de chamados")

    r = client.get("/chamados/?status=Aberto&prioridade=Cr%C3%ADtica")
    check(r.status_code == 200, "Filtros da listagem")

    r = client.post(
        "/chamados/novo",
        data={
            "title": "Chamado do smoke test",
            "description": "Criado automaticamente pelo teste.",
            "category_id": "1",
            "priority": "Alta",
        },
        follow_redirects=True,
    )
    check(r.status_code == 200 and "Chamado do smoke test".encode() in r.data, "Criar chamado")

    from app.models import Ticket
    from app.extensions import db

    with app.app_context():
        ticket = Ticket.query.order_by(Ticket.id.desc()).first()
        ticket_id = ticket.id
        check(ticket.number is not None, "Número automático gerado", str(ticket.number))
        check(ticket.resolution_due_at is not None, "SLA aplicado na criação")

    r = client.post(
        f"/chamados/{ticket_id}/comentar",
        data={"content": "Comentário interno de teste", "is_internal": "1"},
        follow_redirects=True,
    )
    check(r.status_code == 200 and "Comentário interno de teste".encode() in r.data, "Comentário interno")

    r = client.post(f"/chamados/{ticket_id}/assumir", follow_redirects=True)
    check(r.status_code == 200 and b"assumiu" in r.data, "Assumir chamado")

    r = client.post(
        f"/chamados/{ticket_id}/status",
        data={"status": "Resolvido", "solution": "Resolvido pelo smoke test."},
        follow_redirects=True,
    )
    check(r.status_code == 200 and "Resolvido pelo smoke test".encode() in r.data, "Resolver com solução")

    # ---------- anexo ----------
    r = client.post(
        f"/chamados/{ticket_id}/anexar",
        data={"attachments": (io.BytesIO(b"conteudo de teste"), "evidencia.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    check(r.status_code == 200 and b"evidencia.txt" in r.data, "Upload de anexo")

    # ---------- exportações ----------
    r = client.get("/chamados/exportar/excel")
    check(r.status_code == 200 and len(r.data) > 1000, "Exportar Excel")
    r = client.get("/chamados/exportar/pdf")
    check(r.status_code == 200 and r.data[:4] == b"%PDF", "Exportar PDF")

    # ---------- demais módulos ----------
    for url, label in [
        ("/dashboard", "Dashboard"),
        ("/base-conhecimento/", "Base de conhecimento"),
        ("/base-conhecimento/artigo/1", "Artigo da KB"),
        ("/buscar?q=vpn", "Pesquisa global"),
        ("/notificacoes/", "Notificações"),
        ("/laboratorio/", "Laboratório"),
        ("/laboratorio/1", "Detalhe de cenário"),
        ("/admin/usuarios", "Admin: usuários"),
        ("/admin/categorias", "Admin: categorias"),
        ("/admin/departamentos", "Admin: departamentos"),
        ("/admin/sla", "Admin: SLA"),
        ("/admin/auditoria", "Admin: auditoria"),
        ("/api/docs", "Swagger UI"),
    ]:
        r = client.get(url)
        check(r.status_code == 200, f"GET {url} ({label})", f"status {r.status_code}")

    # ---------- laboratório: gerar chamado simulado ----------
    with app.app_context():
        from app.models import Role, User
        analyst = User.query.join(Role).filter(Role.name == "analista").first()
    r = client.post("/laboratorio/1/gerar", data={"analyst_id": analyst.id}, follow_redirects=True)
    check(r.status_code == 200 and b"simulado" in r.data, "Gerar chamado de treinamento")

    client.get("/logout")

    # ---------- permissões: usuário comum ----------
    r = login(client, "maria@empresa.com")
    check(r.status_code == 200, "Login usuário comum")
    r = client.get("/admin/usuarios")
    check(r.status_code == 403, "Usuário comum bloqueado no admin (403)")
    r = client.get(f"/chamados/{ticket_id}")
    check(r.status_code == 403, "Usuário não vê chamado de terceiro (403)")
    r = client.get("/chamados/")
    check(r.status_code == 200, "Usuário vê os próprios chamados")
    client.get("/logout")

# ---------- API REST ----------
with app.test_client() as client:
    r = client.post(
        "/api/v1/auth/token",
        json={"email": "carlos.analista@empresa.com", "password": "Senha@123"},
    )
    check(r.status_code == 200 and "token" in r.get_json(), "API: obter token")
    token = r.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/v1/tickets", headers=headers)
    body = r.get_json()
    check(r.status_code == 200 and body["total"] > 0, "API: listar chamados")

    r = client.get("/api/v1/tickets", headers={"Authorization": "Bearer invalido"})
    check(r.status_code == 401, "API: token inválido retorna 401")

    r = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"title": "Via API", "description": "Chamado criado pela API.", "category_id": 2},
    )
    check(r.status_code == 201 and r.get_json()["number"], "API: criar chamado")

    new_id = r.get_json()["id"]
    r = client.patch(
        f"/api/v1/tickets/{new_id}", headers=headers, json={"status": "Em andamento"}
    )
    check(r.status_code == 200 and r.get_json()["status"] == "Em andamento", "API: alterar status")

    r = client.get("/api/v1/categories", headers=headers)
    check(r.status_code == 200 and len(r.get_json()) > 0, "API: categorias")

    r = client.get("/api/v1/kb?q=vpn", headers=headers)
    check(r.status_code == 200 and len(r.get_json()) > 0, "API: busca na KB")

    r = client.get("/api/v1/openapi.json")
    check(r.status_code == 200 and r.get_json()["openapi"].startswith("3."), "API: OpenAPI spec")

print()
if failures:
    print(f"{len(failures)} verificação(ões) falharam: {failures}")
    sys.exit(1)
print("Todos os fluxos verificados com sucesso.")
