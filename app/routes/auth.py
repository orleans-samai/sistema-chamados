"""Autenticação: login, logout e recuperação de senha."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User
from app.services.audit_service import log_action

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        user = User.query.filter(db.func.lower(User.email) == email).first()
        if not user or not user.check_password(password):
            flash("E-mail ou senha inválidos.", "danger")
            return render_template("auth/login.html"), 401
        if not user.active:
            flash("Conta desativada. Contate o administrador.", "warning")
            return render_template("auth/login.html"), 403

        login_user(user, remember=remember)
        log_action(user, "login", "user", user.id)
        db.session.commit()
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    log_action(current_user, "logout", "user", current_user.id)
    db.session.commit()
    logout_user()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
def forgot_password():
    """Gera o link de redefinição.

    Em produção o link seria enviado por e-mail (EmailChannel); em
    desenvolvimento ele é exibido na tela para facilitar o teste.
    """
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = User.query.filter(db.func.lower(User.email) == email).first()
        if user and user.active:
            token = user.get_reset_token()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            log_action(user, "solicitar_reset_senha", "user", user.id)
            db.session.commit()
            flash(
                "Em produção, o link seria enviado por e-mail. "
                f"Link de redefinição (válido por 1h): {reset_url}",
                "info",
            )
        else:
            # Mesma mensagem para não revelar se o e-mail existe
            flash("Se o e-mail estiver cadastrado, o link de redefinição será enviado.", "info")
        return redirect(url_for("auth.forgot_password"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash("Link inválido ou expirado. Solicite um novo.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        if len(password) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "warning")
        elif password != confirm:
            flash("As senhas não conferem.", "warning")
        else:
            user.set_password(password)
            log_action(user, "redefinir_senha", "user", user.id)
            db.session.commit()
            flash("Senha redefinida com sucesso. Faça login.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)
