"""Laboratório de treinamento N1/N2.

Administradores criam cenários simulados (redes, Windows, impressoras,
Microsoft 365, Active Directory, segurança...) e geram chamados de
treinamento para analistas. O analista atende pelo fluxo normal de
chamados; o gabarito fica visível apenas para administradores.
"""
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Category, LabScenario, Role, Ticket, TicketPriority, User
from app.services import ticket_service
from app.services.audit_service import log_action

lab_bp = Blueprint("lab", __name__)


def _staff_required():
    if not current_user.is_staff:
        abort(403)


def _admin_required():
    if not current_user.is_admin:
        abort(403)


def _analysts():
    return (
        User.query.join(Role)
        .filter(Role.name == Role.ANALISTA, User.active.is_(True))
        .order_by(User.name)
        .all()
    )


@lab_bp.route("/")
@login_required
def list_scenarios():
    _staff_required()
    scenarios = LabScenario.query.order_by(LabScenario.created_at.desc()).all()
    if not current_user.is_admin:
        scenarios = [s for s in scenarios if s.active]
    my_trainings = (
        Ticket.query.filter_by(is_training=True, assignee_id=current_user.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return render_template(
        "lab/list.html", scenarios=scenarios, my_trainings=my_trainings
    )


def _scenario_form_data():
    return {
        "title": (request.form.get("title") or "").strip(),
        "area": request.form.get("area") or LabScenario.AREAS[0],
        "level": request.form.get("level") or "N1",
        "priority": request.form.get("priority") or TicketPriority.MEDIA,
        "category_id": request.form.get("category_id", type=int) or None,
        "description": (request.form.get("description") or "").strip(),
        "expected_solution": (request.form.get("expected_solution") or "").strip(),
        "hints": (request.form.get("hints") or "").strip(),
        "active": bool(request.form.get("active")),
    }


@lab_bp.route("/novo", methods=["GET", "POST"])
@login_required
def new_scenario():
    _admin_required()
    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    if request.method == "POST":
        data = _scenario_form_data()
        if not data["title"] or not data["description"]:
            flash("Preencha título e descrição do cenário.", "warning")
        else:
            scenario = LabScenario(created_by_id=current_user.id, **data)
            db.session.add(scenario)
            db.session.flush()
            log_action(current_user, "criar", "lab_scenario", scenario.id, scenario.title)
            db.session.commit()
            flash("Cenário de treinamento criado.", "success")
            return redirect(url_for("lab.detail", scenario_id=scenario.id))
    return render_template("lab/form.html", scenario=None, categories=categories)


@lab_bp.route("/<int:scenario_id>")
@login_required
def detail(scenario_id):
    _staff_required()
    scenario = db.session.get(LabScenario, scenario_id) or abort(404)
    if not scenario.active and not current_user.is_admin:
        abort(404)
    generated = (
        Ticket.query.filter_by(lab_scenario_id=scenario.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return render_template(
        "lab/detail.html", scenario=scenario, generated=generated, analysts=_analysts()
    )


@lab_bp.route("/<int:scenario_id>/editar", methods=["GET", "POST"])
@login_required
def edit_scenario(scenario_id):
    _admin_required()
    scenario = db.session.get(LabScenario, scenario_id) or abort(404)
    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    if request.method == "POST":
        data = _scenario_form_data()
        if not data["title"] or not data["description"]:
            flash("Preencha título e descrição do cenário.", "warning")
        else:
            for key, value in data.items():
                setattr(scenario, key, value)
            log_action(current_user, "editar", "lab_scenario", scenario.id, scenario.title)
            db.session.commit()
            flash("Cenário atualizado.", "success")
            return redirect(url_for("lab.detail", scenario_id=scenario.id))
    return render_template("lab/form.html", scenario=scenario, categories=categories)


@lab_bp.route("/<int:scenario_id>/excluir", methods=["POST"])
@login_required
def delete_scenario(scenario_id):
    _admin_required()
    scenario = db.session.get(LabScenario, scenario_id) or abort(404)
    if Ticket.query.filter_by(lab_scenario_id=scenario.id).first():
        scenario.active = False
        db.session.commit()
        flash("Cenário possui chamados gerados e foi desativado em vez de excluído.", "info")
    else:
        log_action(current_user, "excluir", "lab_scenario", scenario.id, scenario.title)
        db.session.delete(scenario)
        db.session.commit()
        flash("Cenário excluído.", "success")
    return redirect(url_for("lab.list_scenarios"))


@lab_bp.route("/<int:scenario_id>/gerar", methods=["POST"])
@login_required
def generate_ticket(scenario_id):
    """Gera um chamado simulado do cenário para um analista treinar."""
    _admin_required()
    scenario = db.session.get(LabScenario, scenario_id) or abort(404)
    analyst = db.session.get(User, request.form.get("analyst_id", type=int) or 0)
    if not analyst or not analyst.is_analyst:
        flash("Selecione um analista válido.", "warning")
        return redirect(url_for("lab.detail", scenario_id=scenario.id))

    category_id = scenario.category_id
    if not category_id:
        fallback = Category.query.filter_by(active=True).first()
        if not fallback:
            flash("Cadastre ao menos uma categoria antes de gerar chamados.", "warning")
            return redirect(url_for("lab.detail", scenario_id=scenario.id))
        category_id = fallback.id

    ticket = ticket_service.create_ticket(
        title=f"[TREINAMENTO {scenario.level}] {scenario.title}",
        description=scenario.description,
        category_id=category_id,
        subcategory_id=None,
        priority=scenario.priority,
        requester=current_user,
        assignee_id=analyst.id,
        is_training=True,
        lab_scenario=scenario,
    )
    flash(
        f"Chamado simulado {ticket.number} gerado para {analyst.name}.", "success"
    )
    return redirect(url_for("lab.detail", scenario_id=scenario.id))
