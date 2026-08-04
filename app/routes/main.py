"""Rotas principais: dashboard, pesquisa global e documentação da API."""
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import KnowledgeArticle, User
from app.repositories.ticket_repository import TicketRepository
from app.services.sla_service import tickets_at_risk

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    base = TicketRepository.visible_query(current_user)
    cards = TicketRepository.dashboard_cards(base)
    charts = {
        "status": TicketRepository.count_by_status(base),
        "categoria": TicketRepository.count_by_category(base),
        "analista": TicketRepository.count_by_assignee(base),
        "mensal": TicketRepository.monthly_series(base),
    }
    sla_alerts = tickets_at_risk() if current_user.is_staff else []
    return render_template(
        "dashboard.html", cards=cards, charts=charts, sla_alerts=sla_alerts
    )


@main_bp.route("/buscar")
@login_required
def search():
    """Pesquisa global: chamados, base de conhecimento e usuários (admin)."""
    q = (request.args.get("q") or "").strip()
    tickets, articles, users = [], [], []
    if q:
        tickets = (
            TicketRepository.apply_filters(
                TicketRepository.visible_query(current_user), {"q": q}
            )
            .limit(20)
            .all()
        )
        like = f"%{q}%"
        articles = (
            KnowledgeArticle.query.filter(
                KnowledgeArticle.published.is_(True),
                (KnowledgeArticle.title.ilike(like))
                | (KnowledgeArticle.content.ilike(like))
                | (KnowledgeArticle.tags.ilike(like)),
            )
            .limit(20)
            .all()
        )
        if current_user.is_admin:
            users = User.query.filter(
                (User.name.ilike(like)) | (User.email.ilike(like))
            ).limit(20).all()
    return render_template(
        "search.html", q=q, tickets=tickets, articles=articles, users=users
    )


@main_bp.route("/api/docs")
@login_required
def api_docs():
    """Interface Swagger UI da API REST."""
    return render_template("api_docs.html")
