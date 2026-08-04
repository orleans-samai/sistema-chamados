"""Fábrica da aplicação Flask do Service Desk."""
import os

import markupsafe
from flask import Flask, render_template
from flask_login import current_user

from config import Config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config_class=Config):
    """Cria e configura a instância da aplicação."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Garante os diretórios de dados
    basedir = os.path.dirname(app.root_path)
    os.makedirs(os.path.join(basedir, "instance"), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    # Importa os modelos para que as migrations os enxerguem
    from app import models  # noqa: F401

    _register_blueprints(app)
    _register_template_helpers(app)
    _register_error_handlers(app)

    from app.seed import register_cli
    register_cli(app)

    return app


def _register_blueprints(app):
    from app.api.v1 import api_bp
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.kb import kb_bp
    from app.routes.lab import lab_bp
    from app.routes.main import main_bp
    from app.routes.notifications import notifications_bp
    from app.routes.tickets import tickets_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tickets_bp, url_prefix="/chamados")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(kb_bp, url_prefix="/base-conhecimento")
    app.register_blueprint(notifications_bp, url_prefix="/notificacoes")
    app.register_blueprint(lab_bp, url_prefix="/laboratorio")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    # A API REST usa token Bearer, não sessão — fica fora da proteção CSRF
    csrf.exempt(api_bp)


def _register_template_helpers(app):
    from app.models import Notification, TicketPriority, TicketStatus

    @app.context_processor
    def inject_globals():
        unread = 0
        latest = []
        if current_user.is_authenticated:
            unread = Notification.query.filter_by(
                user_id=current_user.id, read=False
            ).count()
            latest = (
                Notification.query.filter_by(user_id=current_user.id, read=False)
                .order_by(Notification.created_at.desc())
                .limit(5)
                .all()
            )
        return {
            "unread_notifications": unread,
            "latest_notifications": latest,
            "TicketStatus": TicketStatus,
            "TicketPriority": TicketPriority,
        }

    @app.template_filter("dt")
    def format_dt(value):
        """Formata datas no padrão brasileiro."""
        return value.strftime("%d/%m/%Y %H:%M") if value else "—"

    @app.template_filter("d")
    def format_d(value):
        return value.strftime("%d/%m/%Y") if value else "—"

    @app.template_filter("nl2br")
    def nl2br(value):
        """Escapa HTML e converte quebras de linha em <br>."""
        if not value:
            return ""
        escaped = markupsafe.escape(value)
        return markupsafe.Markup(escaped.replace("\n", markupsafe.Markup("<br>")))


def _register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_e):
        db.session.rollback()
        return render_template("errors/500.html"), 500
