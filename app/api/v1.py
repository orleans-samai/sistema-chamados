"""API REST v1 — autenticação por token Bearer.

Fluxo:
    1. POST /api/v1/auth/token com {"email": ..., "password": ...}
    2. Use o token retornado no header: Authorization: Bearer <token>

Documentação interativa: /api/docs (Swagger UI).
"""
from functools import wraps

from flask import Blueprint, g, jsonify, request

from app.extensions import db
from app.models import (
    Category,
    KnowledgeArticle,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
)
from app.repositories.ticket_repository import TicketRepository
from app.services import ticket_service
from app.api.openapi import build_spec

api_bp = Blueprint("api", __name__)


# ------------------------------------------------------------- autenticação
def token_required(view):
    """Exige o header Authorization: Bearer <api_token>."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Token ausente. Use Authorization: Bearer <token>."}), 401
        token = auth.removeprefix("Bearer ").strip()
        user = User.query.filter_by(api_token=token, active=True).first()
        if not user:
            return jsonify({"error": "Token inválido."}), 401
        g.api_user = user
        return view(*args, **kwargs)

    return wrapped


@api_bp.route("/auth/token", methods=["POST"])
def get_token():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter(db.func.lower(User.email) == email).first()
    if not user or not user.check_password(password) or not user.active:
        return jsonify({"error": "Credenciais inválidas."}), 401
    if not user.api_token:
        user.generate_api_token()
        db.session.commit()
    return jsonify({"token": user.api_token, "user": _user_dict(user)})


# ------------------------------------------------------------ serializadores
def _user_dict(user):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.name if user.role else None,
    }


def _ticket_dict(ticket, full=False):
    data = {
        "id": ticket.id,
        "number": ticket.number,
        "title": ticket.title,
        "category": ticket.category.name if ticket.category else None,
        "subcategory": ticket.subcategory.name if ticket.subcategory else None,
        "priority": ticket.priority,
        "status": ticket.status,
        "requester": _user_dict(ticket.requester) if ticket.requester else None,
        "assignee": _user_dict(ticket.assignee) if ticket.assignee else None,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "sla": ticket.sla["code"],
        "is_training": ticket.is_training,
    }
    if full:
        data.update({
            "description": ticket.description,
            "solution": ticket.solution,
            "rating": ticket.rating,
            "response_due_at": ticket.response_due_at.isoformat() if ticket.response_due_at else None,
            "resolution_due_at": ticket.resolution_due_at.isoformat() if ticket.resolution_due_at else None,
            "comments": [
                {
                    "id": c.id,
                    "author": c.user.name if c.user else None,
                    "content": c.content,
                    "is_internal": c.is_internal,
                    "created_at": c.created_at.isoformat(),
                }
                for c in ticket.comments
                if g.api_user.is_staff or not c.is_internal
            ],
        })
    return data


# ----------------------------------------------------------------- chamados
@api_bp.route("/tickets", methods=["GET"])
@token_required
def list_tickets():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    query = TicketRepository.apply_filters(
        TicketRepository.visible_query(g.api_user), request.args
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [_ticket_dict(t) for t in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    })


@api_bp.route("/tickets", methods=["POST"])
@token_required
def create_ticket():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category_id = data.get("category_id")
    priority = data.get("priority") or TicketPriority.MEDIA

    if not title or not description or not category_id:
        return jsonify({"error": "Campos obrigatórios: title, description, category_id."}), 400
    if priority not in TicketPriority.ALL:
        return jsonify({"error": f"Prioridade inválida. Use: {TicketPriority.ALL}"}), 400
    if not db.session.get(Category, category_id):
        return jsonify({"error": "Categoria inexistente."}), 400

    ticket = ticket_service.create_ticket(
        title=title,
        description=description,
        category_id=category_id,
        subcategory_id=data.get("subcategory_id"),
        priority=priority,
        requester=g.api_user,
    )
    return jsonify(_ticket_dict(ticket, full=True)), 201


@api_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@token_required
def get_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({"error": "Chamado não encontrado."}), 404
    if not g.api_user.is_staff and ticket.requester_id != g.api_user.id:
        return jsonify({"error": "Sem permissão para este chamado."}), 403
    return jsonify(_ticket_dict(ticket, full=True))


@api_bp.route("/tickets/<int:ticket_id>", methods=["PATCH"])
@token_required
def update_ticket(ticket_id):
    if not g.api_user.is_staff:
        return jsonify({"error": "Apenas analistas e administradores."}), 403
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({"error": "Chamado não encontrado."}), 404

    data = request.get_json(silent=True) or {}
    if "status" in data:
        if data["status"] not in TicketStatus.ALL:
            return jsonify({"error": f"Status inválido. Use: {TicketStatus.ALL}"}), 400
        ticket_service.change_status(ticket, g.api_user, data["status"], data.get("solution"))
    if "assignee_id" in data:
        assignee = db.session.get(User, data["assignee_id"])
        if not assignee or not assignee.is_staff:
            return jsonify({"error": "Analista inválido."}), 400
        ticket_service.assign_ticket(ticket, g.api_user, assignee)
    if "comment" in data and (data["comment"] or "").strip():
        ticket_service.add_comment(
            ticket, g.api_user, data["comment"].strip(), bool(data.get("is_internal"))
        )
    fields = {k: v for k, v in data.items() if k in ("title", "description", "priority")}
    if fields:
        if "priority" in fields and fields["priority"] not in TicketPriority.ALL:
            return jsonify({"error": f"Prioridade inválida. Use: {TicketPriority.ALL}"}), 400
        ticket_service.update_ticket(ticket, g.api_user, fields)
    return jsonify(_ticket_dict(ticket, full=True))


# ---------------------------------------------------------------- catálogo
@api_bp.route("/categories", methods=["GET"])
@token_required
def list_categories():
    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    return jsonify([
        {
            "id": c.id,
            "name": c.name,
            "subcategories": [{"id": s.id, "name": s.name} for s in c.subcategories],
        }
        for c in categories
    ])


@api_bp.route("/kb", methods=["GET"])
@token_required
def list_kb():
    q = (request.args.get("q") or "").strip()
    query = KnowledgeArticle.query.filter_by(published=True)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (KnowledgeArticle.title.ilike(like))
            | (KnowledgeArticle.content.ilike(like))
            | (KnowledgeArticle.tags.ilike(like))
        )
    articles = query.order_by(KnowledgeArticle.updated_at.desc()).limit(50).all()
    return jsonify([
        {
            "id": a.id,
            "title": a.title,
            "type": a.article_type,
            "summary": a.summary,
            "tags": a.tag_list,
            "views": a.views,
        }
        for a in articles
    ])


# ------------------------------------------------------------------ OpenAPI
@api_bp.route("/openapi.json")
def openapi():
    """Especificação OpenAPI 3 consumida pelo Swagger UI em /api/docs."""
    return jsonify(build_spec())
