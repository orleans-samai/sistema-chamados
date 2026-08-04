"""Rotas administrativas: usuários, categorias, departamentos, SLA e auditoria."""
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    AuditLog,
    Category,
    Department,
    Role,
    SLARule,
    Subcategory,
    Ticket,
    TicketPriority,
    User,
)
from app.services.audit_service import log_action

admin_bp = Blueprint("admin", __name__)


def admin_required(view):
    """Restringe a rota a administradores."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


# ----------------------------------------------------------------- usuários
@admin_bp.route("/usuarios")
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    q = (request.args.get("q") or "").strip()
    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter((User.name.ilike(like)) | (User.email.ilike(like)))
    pagination = query.order_by(User.name).paginate(
        page=page, per_page=current_app.config["ITEMS_PER_PAGE"], error_out=False
    )
    return render_template("admin/users.html", pagination=pagination, q=q)


def _user_form_data():
    return {
        "name": (request.form.get("name") or "").strip(),
        "email": (request.form.get("email") or "").strip().lower(),
        "password": request.form.get("password") or "",
        "role_id": request.form.get("role_id", type=int),
        "department_id": request.form.get("department_id", type=int) or None,
        "active": bool(request.form.get("active")),
    }


@admin_bp.route("/usuarios/novo", methods=["GET", "POST"])
@admin_required
def new_user():
    roles = Role.query.all()
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        data = _user_form_data()
        if not data["name"] or not data["email"] or not data["role_id"]:
            flash("Preencha nome, e-mail e perfil.", "warning")
        elif len(data["password"]) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "warning")
        elif User.query.filter(db.func.lower(User.email) == data["email"]).first():
            flash("Já existe um usuário com este e-mail.", "warning")
        else:
            user = User(
                name=data["name"],
                email=data["email"],
                role_id=data["role_id"],
                department_id=data["department_id"],
                active=data["active"],
            )
            user.set_password(data["password"])
            user.generate_api_token()
            db.session.add(user)
            db.session.flush()
            log_action(current_user, "criar", "user", user.id, f"Usuário {user.email}")
            db.session.commit()
            flash("Usuário criado com sucesso.", "success")
            return redirect(url_for("admin.users"))
    return render_template(
        "admin/user_form.html", user=None, roles=roles, departments=departments
    )


@admin_bp.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    roles = Role.query.all()
    departments = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        data = _user_form_data()
        email_owner = User.query.filter(db.func.lower(User.email) == data["email"]).first()
        if not data["name"] or not data["email"] or not data["role_id"]:
            flash("Preencha nome, e-mail e perfil.", "warning")
        elif email_owner and email_owner.id != user.id:
            flash("Já existe um usuário com este e-mail.", "warning")
        elif data["password"] and len(data["password"]) < 6:
            flash("A nova senha deve ter pelo menos 6 caracteres.", "warning")
        elif user.id == current_user.id and not data["active"]:
            flash("Você não pode desativar a própria conta.", "warning")
        else:
            user.name = data["name"]
            user.email = data["email"]
            user.role_id = data["role_id"]
            user.department_id = data["department_id"]
            user.active = data["active"]
            if data["password"]:
                user.set_password(data["password"])
            log_action(current_user, "editar", "user", user.id, f"Usuário {user.email}")
            db.session.commit()
            flash("Usuário atualizado.", "success")
            return redirect(url_for("admin.users"))
    return render_template(
        "admin/user_form.html", user=user, roles=roles, departments=departments
    )


@admin_bp.route("/usuarios/<int:user_id>/excluir", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("Você não pode excluir a própria conta.", "warning")
        return redirect(url_for("admin.users"))
    has_tickets = Ticket.query.filter(
        (Ticket.requester_id == user.id) | (Ticket.assignee_id == user.id)
    ).first()
    if has_tickets:
        user.active = False
        log_action(current_user, "desativar", "user", user.id, f"Usuário {user.email}")
        db.session.commit()
        flash(
            "Usuário possui chamados vinculados e foi desativado em vez de excluído.",
            "info",
        )
    else:
        log_action(current_user, "excluir", "user", user.id, f"Usuário {user.email}")
        db.session.delete(user)
        db.session.commit()
        flash("Usuário excluído.", "success")
    return redirect(url_for("admin.users"))


# --------------------------------------------------------------- categorias
@admin_bp.route("/categorias", methods=["GET", "POST"])
@admin_required
def categories():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Informe o nome da categoria.", "warning")
        elif Category.query.filter(db.func.lower(Category.name) == name.lower()).first():
            flash("Categoria já existe.", "warning")
        else:
            category = Category(
                name=name, description=(request.form.get("description") or "").strip()
            )
            db.session.add(category)
            db.session.flush()
            log_action(current_user, "criar", "category", category.id, name)
            db.session.commit()
            flash("Categoria criada.", "success")
        return redirect(url_for("admin.categories"))
    items = Category.query.order_by(Category.name).all()
    return render_template("admin/categories.html", categories=items)


@admin_bp.route("/categorias/<int:category_id>/editar", methods=["POST"])
@admin_required
def edit_category(category_id):
    category = db.session.get(Category, category_id) or abort(404)
    name = (request.form.get("name") or "").strip()
    if name:
        category.name = name
        category.description = (request.form.get("description") or "").strip()
        category.active = bool(request.form.get("active"))
        log_action(current_user, "editar", "category", category.id, name)
        db.session.commit()
        flash("Categoria atualizada.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categorias/<int:category_id>/excluir", methods=["POST"])
@admin_required
def delete_category(category_id):
    category = db.session.get(Category, category_id) or abort(404)
    if Ticket.query.filter_by(category_id=category.id).first():
        category.active = False
        db.session.commit()
        flash("Categoria possui chamados e foi desativada em vez de excluída.", "info")
    else:
        log_action(current_user, "excluir", "category", category.id, category.name)
        db.session.delete(category)
        db.session.commit()
        flash("Categoria excluída.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categorias/<int:category_id>/subcategorias", methods=["POST"])
@admin_required
def add_subcategory(category_id):
    category = db.session.get(Category, category_id) or abort(404)
    name = (request.form.get("name") or "").strip()
    if name:
        db.session.add(Subcategory(name=name, category_id=category.id))
        log_action(current_user, "criar", "subcategory", None, f"{category.name} > {name}")
        db.session.commit()
        flash("Subcategoria adicionada.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/subcategorias/<int:subcategory_id>/excluir", methods=["POST"])
@admin_required
def delete_subcategory(subcategory_id):
    sub = db.session.get(Subcategory, subcategory_id) or abort(404)
    Ticket.query.filter_by(subcategory_id=sub.id).update({"subcategory_id": None})
    log_action(current_user, "excluir", "subcategory", sub.id, sub.name)
    db.session.delete(sub)
    db.session.commit()
    flash("Subcategoria excluída.", "success")
    return redirect(url_for("admin.categories"))


# ------------------------------------------------------------ departamentos
@admin_bp.route("/departamentos", methods=["GET", "POST"])
@admin_required
def departments():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Informe o nome do departamento.", "warning")
        elif Department.query.filter(db.func.lower(Department.name) == name.lower()).first():
            flash("Departamento já existe.", "warning")
        else:
            dept = Department(
                name=name, description=(request.form.get("description") or "").strip()
            )
            db.session.add(dept)
            db.session.flush()
            log_action(current_user, "criar", "department", dept.id, name)
            db.session.commit()
            flash("Departamento criado.", "success")
        return redirect(url_for("admin.departments"))
    items = Department.query.order_by(Department.name).all()
    return render_template("admin/departments.html", departments=items)


@admin_bp.route("/departamentos/<int:department_id>/editar", methods=["POST"])
@admin_required
def edit_department(department_id):
    dept = db.session.get(Department, department_id) or abort(404)
    name = (request.form.get("name") or "").strip()
    if name:
        dept.name = name
        dept.description = (request.form.get("description") or "").strip()
        log_action(current_user, "editar", "department", dept.id, name)
        db.session.commit()
        flash("Departamento atualizado.", "success")
    return redirect(url_for("admin.departments"))


@admin_bp.route("/departamentos/<int:department_id>/excluir", methods=["POST"])
@admin_required
def delete_department(department_id):
    dept = db.session.get(Department, department_id) or abort(404)
    if User.query.filter_by(department_id=dept.id).first():
        flash("Departamento possui usuários vinculados e não pode ser excluído.", "warning")
    else:
        log_action(current_user, "excluir", "department", dept.id, dept.name)
        db.session.delete(dept)
        db.session.commit()
        flash("Departamento excluído.", "success")
    return redirect(url_for("admin.departments"))


# --------------------------------------------------------------------- SLA
@admin_bp.route("/sla", methods=["GET", "POST"])
@admin_required
def sla():
    if request.method == "POST":
        rule_id = request.form.get("rule_id", type=int)
        rule = db.session.get(SLARule, rule_id) or abort(404)
        response_minutes = request.form.get("response_minutes", type=int)
        resolution_minutes = request.form.get("resolution_minutes", type=int)
        if not response_minutes or not resolution_minutes:
            flash("Informe os tempos em minutos.", "warning")
        else:
            rule.response_minutes = response_minutes
            rule.resolution_minutes = resolution_minutes
            rule.active = bool(request.form.get("active"))
            log_action(current_user, "editar", "sla_rule", rule.id, f"SLA {rule.priority}")
            db.session.commit()
            flash(f"SLA da prioridade {rule.priority} atualizado.", "success")
        return redirect(url_for("admin.sla"))

    rules = []
    for priority in TicketPriority.ALL:
        rule = SLARule.query.filter_by(priority=priority).first()
        if rule:
            rules.append(rule)
    return render_template("admin/sla.html", rules=rules)


# ---------------------------------------------------------------- auditoria
@admin_bp.route("/auditoria")
@admin_required
def audit():
    page = request.args.get("page", 1, type=int)
    query = AuditLog.query
    if request.args.get("acao"):
        query = query.filter(AuditLog.action == request.args["acao"])
    if request.args.get("entidade"):
        query = query.filter(AuditLog.entity == request.args["entidade"])
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    actions = [r[0] for r in db.session.query(AuditLog.action).distinct().all()]
    entities = [r[0] for r in db.session.query(AuditLog.entity).distinct().all() if r[0]]
    return render_template(
        "admin/audit.html", pagination=pagination, actions=actions, entities=entities
    )
