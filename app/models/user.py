"""Usuários e perfis de acesso (RBAC)."""
import secrets
from datetime import datetime

from flask import current_app
from flask_login import UserMixin
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class Role(db.Model):
    """Perfil de acesso: admin, analista ou usuario."""

    __tablename__ = "roles"

    ADMIN = "admin"
    ANALISTA = "analista"
    USUARIO = "usuario"

    LABELS = {ADMIN: "Administrador", ANALISTA: "Analista", USUARIO: "Usuário"}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(255))

    users = db.relationship("User", back_populates="role")

    @property
    def label(self):
        return self.LABELS.get(self.name, self.name)

    def __repr__(self):
        return f"<Role {self.name}>"


class User(UserMixin, db.Model):
    """Usuário do sistema."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    active = db.Column(db.Boolean, default=True, nullable=False)
    api_token = db.Column(db.String(64), unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    role = db.relationship("Role", back_populates="users")
    department = db.relationship("Department", back_populates="users")

    # ------------------------------------------------------------------ senha
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ------------------------------------------------------------------ RBAC
    @property
    def is_admin(self):
        return self.role and self.role.name == Role.ADMIN

    @property
    def is_analyst(self):
        return self.role and self.role.name == Role.ANALISTA

    @property
    def is_staff(self):
        """Admin ou analista (equipe de atendimento)."""
        return self.is_admin or self.is_analyst

    def has_role(self, *names):
        return self.role and self.role.name in names

    # ------------------------------------------------------------- API token
    def generate_api_token(self):
        self.api_token = secrets.token_hex(32)
        return self.api_token

    # ------------------------------------------- redefinição de senha (token)
    def get_reset_token(self):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="reset-senha")
        return s.dumps(self.id)

    @staticmethod
    def verify_reset_token(token):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="reset-senha")
        try:
            user_id = s.loads(token, max_age=current_app.config["RESET_TOKEN_MAX_AGE"])
        except (BadSignature, SignatureExpired):
            return None
        return db.session.get(User, user_id)

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
