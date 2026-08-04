"""Auditoria: registro de todas as ações relevantes do sistema."""
from datetime import datetime

from app.extensions import db


class AuditLog(db.Model):
    """Log de auditoria de ações dos usuários."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(60), nullable=False, index=True)  # criar, editar, excluir, login...
    entity = db.Column(db.String(60), index=True)  # ticket, user, category...
    entity_id = db.Column(db.Integer)
    details = db.Column(db.String(500))
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)

    user = db.relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} {self.entity}>"
