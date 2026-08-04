"""Rotas dos chamados: listagem, criação, detalhe, anexos e exportação."""
import os
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    Attachment,
    Category,
    Subcategory,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
    Role,
)
from app.repositories.ticket_repository import TicketRepository
from app.services import ticket_service
from app.services.audit_service import log_action
from app.services.export_service import tickets_to_excel, tickets_to_pdf

tickets_bp = Blueprint("tickets", __name__)


# ----------------------------------------------------------------- helpers
def _get_ticket_or_403(ticket_id):
    """Carrega o chamado e valida a permissão de visualização."""
    ticket = db.session.get(Ticket, ticket_id) or abort(404)
    if not current_user.is_staff and ticket.requester_id != current_user.id:
        abort(403)
    return ticket


def _can_manage(ticket):
    """Quem pode atuar no chamado: admin ou analista responsável/sem dono."""
    if current_user.is_admin:
        return True
    if current_user.is_analyst:
        return ticket.assignee_id in (None, current_user.id)
    return False


def _analysts():
    return (
        User.query.join(Role)
        .filter(Role.name.in_([Role.ADMIN, Role.ANALISTA]), User.active.is_(True))
        .order_by(User.name)
        .all()
    )


def _save_attachments(ticket, files):
    """Salva os arquivos enviados validando a extensão permitida."""
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    saved = 0
    for file in files:
        if not file or not file.filename:
            continue
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in allowed:
            flash(f"Extensão não permitida: {file.filename}", "warning")
            continue
        stored = f"{uuid4().hex}_{secure_filename(file.filename)}"
        folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(ticket.id))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, stored)
        file.save(path)
        db.session.add(
            Attachment(
                ticket_id=ticket.id,
                filename=file.filename,
                stored_name=stored,
                size=os.path.getsize(path),
                content_type=file.mimetype,
                uploaded_by_id=current_user.id,
            )
        )
        saved += 1
    if saved:
        db.session.commit()
    return saved


def _filtered_query():
    base = TicketRepository.visible_query(current_user)
    return TicketRepository.apply_filters(base, request.args)


# ----------------------------------------------------------------- listagem
@tickets_bp.route("/")
@login_required
def list_tickets():
    page = request.args.get("page", 1, type=int)
    pagination = _filtered_query().paginate(
        page=page, per_page=current_app.config["ITEMS_PER_PAGE"], error_out=False
    )
    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    return render_template(
        "tickets/list.html",
        pagination=pagination,
        tickets=pagination.items,
        categories=categories,
        analysts=_analysts() if current_user.is_staff else [],
    )


@tickets_bp.route("/exportar/<fmt>")
@login_required
def export(fmt):
    """Exporta a listagem (com os filtros atuais) para Excel ou PDF."""
    tickets = _filtered_query().all()
    if fmt == "excel":
        buffer = tickets_to_excel(tickets)
        return send_file(
            buffer,
            as_attachment=True,
            download_name="chamados.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    if fmt == "pdf":
        buffer = tickets_to_pdf(tickets)
        return send_file(
            buffer, as_attachment=True, download_name="chamados.pdf", mimetype="application/pdf"
        )
    abort(404)


# ------------------------------------------------------------------ criação
@tickets_bp.route("/novo", methods=["GET", "POST"])
@login_required
def new_ticket():
    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        category_id = request.form.get("category_id", type=int)
        priority = request.form.get("priority") or TicketPriority.MEDIA

        if not title or not description or not category_id:
            flash("Preencha título, descrição e categoria.", "warning")
        elif priority not in TicketPriority.ALL:
            flash("Prioridade inválida.", "warning")
        else:
            ticket = ticket_service.create_ticket(
                title=title,
                description=description,
                category_id=category_id,
                subcategory_id=request.form.get("subcategory_id", type=int),
                priority=priority,
                requester=current_user,
            )
            _save_attachments(ticket, request.files.getlist("attachments"))
            flash(f"Chamado {ticket.number} aberto com sucesso.", "success")
            return redirect(url_for("tickets.detail", ticket_id=ticket.id))

    return render_template("tickets/form.html", categories=categories, ticket=None)


@tickets_bp.route("/subcategorias/<int:category_id>")
@login_required
def subcategories(category_id):
    """Retorna as subcategorias de uma categoria (JSON, usado pelo formulário)."""
    subs = Subcategory.query.filter_by(category_id=category_id).order_by(Subcategory.name).all()
    return jsonify([{"id": s.id, "name": s.name} for s in subs])


# ------------------------------------------------------------------ detalhe
@tickets_bp.route("/<int:ticket_id>")
@login_required
def detail(ticket_id):
    ticket = _get_ticket_or_403(ticket_id)
    comments = ticket.comments
    if not current_user.is_staff:
        comments = ticket.public_comments
    return render_template(
        "tickets/detail.html",
        ticket=ticket,
        comments=comments,
        analysts=_analysts() if current_user.is_staff else [],
        can_manage=_can_manage(ticket),
    )


@tickets_bp.route("/<int:ticket_id>/editar", methods=["GET", "POST"])
@login_required
def edit(ticket_id):
    ticket = _get_ticket_or_403(ticket_id)
    is_requester_open = ticket.requester_id == current_user.id and ticket.status == TicketStatus.ABERTO
    if not (_can_manage(ticket) or is_requester_open):
        abort(403)

    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    if request.method == "POST":
        data = {
            "title": (request.form.get("title") or "").strip(),
            "description": (request.form.get("description") or "").strip(),
            "category_id": request.form.get("category_id", type=int),
            "subcategory_id": request.form.get("subcategory_id", type=int),
            "priority": request.form.get("priority"),
        }
        if not data["title"] or not data["description"] or not data["category_id"]:
            flash("Preencha título, descrição e categoria.", "warning")
        else:
            changes = ticket_service.update_ticket(ticket, current_user, data)
            flash("Chamado atualizado." if changes else "Nenhuma alteração detectada.", "success" if changes else "info")
            return redirect(url_for("tickets.detail", ticket_id=ticket.id))

    return render_template("tickets/form.html", categories=categories, ticket=ticket)


# -------------------------------------------------------------------- ações
@tickets_bp.route("/<int:ticket_id>/comentar", methods=["POST"])
@login_required
def comment(ticket_id):
    ticket = _get_ticket_or_403(ticket_id)
    content = (request.form.get("content") or "").strip()
    is_internal = bool(request.form.get("is_internal")) and current_user.is_staff
    if not content:
        flash("Escreva o comentário antes de enviar.", "warning")
    else:
        ticket_service.add_comment(ticket, current_user, content, is_internal)
        flash("Comentário adicionado.", "success")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/status", methods=["POST"])
@login_required
def change_status(ticket_id):
    ticket = _get_ticket_or_403(ticket_id)
    if not _can_manage(ticket):
        abort(403)
    new_status = request.form.get("status")
    solution = (request.form.get("solution") or "").strip() or None
    if new_status not in TicketStatus.ALL:
        flash("Status inválido.", "warning")
    elif new_status == TicketStatus.RESOLVIDO and not (solution or ticket.solution):
        flash("Registre a solução para marcar o chamado como resolvido.", "warning")
    else:
        ticket_service.change_status(ticket, current_user, new_status, solution)
        flash(f"Status alterado para {new_status}.", "success")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/assumir", methods=["POST"])
@login_required
def take(ticket_id):
    ticket = _get_ticket_or_403(ticket_id)
    if not current_user.is_staff:
        abort(403)
    ticket_service.assign_ticket(ticket, current_user, current_user)
    flash(f"Você assumiu o chamado {ticket.number}.", "success")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/atribuir", methods=["POST"])
@login_required
def assign(ticket_id):
    ticket = _get_ticket_or_403(ticket_id)
    if not current_user.is_admin:
        abort(403)
    assignee = db.session.get(User, request.form.get("assignee_id", type=int) or 0)
    if not assignee or not assignee.is_staff:
        flash("Selecione um analista válido.", "warning")
    else:
        ticket_service.assign_ticket(ticket, current_user, assignee)
        flash(f"Chamado atribuído a {assignee.name}.", "success")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/avaliar", methods=["POST"])
@login_required
def rate(ticket_id):
    ticket = _get_ticket_or_403(ticket_id)
    if ticket.requester_id != current_user.id:
        abort(403)
    if ticket.status not in (TicketStatus.RESOLVIDO, TicketStatus.FECHADO):
        flash("Só é possível avaliar chamados resolvidos ou fechados.", "warning")
        return redirect(url_for("tickets.detail", ticket_id=ticket.id))
    rating = request.form.get("rating", type=int)
    if not rating or rating < 1 or rating > 5:
        flash("Escolha uma nota de 1 a 5.", "warning")
    else:
        ticket_service.rate_ticket(
            ticket, current_user, rating, (request.form.get("comment") or "").strip() or None
        )
        flash("Obrigado pela avaliação!", "success")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))


# ------------------------------------------------------------------- anexos
@tickets_bp.route("/<int:ticket_id>/anexar", methods=["POST"])
@login_required
def attach(ticket_id):
    ticket = _get_ticket_or_403(ticket_id)
    saved = _save_attachments(ticket, request.files.getlist("attachments"))
    if saved:
        log_action(current_user, "anexar", "ticket", ticket.id, f"{saved} arquivo(s)")
        db.session.commit()
        flash(f"{saved} arquivo(s) anexado(s).", "success")
    else:
        flash("Nenhum arquivo válido enviado.", "warning")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))


@tickets_bp.route("/anexos/<int:attachment_id>")
@login_required
def download_attachment(attachment_id):
    attachment = db.session.get(Attachment, attachment_id) or abort(404)
    _get_ticket_or_403(attachment.ticket_id)  # valida o acesso ao chamado
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(attachment.ticket_id))
    return send_from_directory(
        folder,
        attachment.stored_name,
        as_attachment=True,
        download_name=attachment.filename,
    )
