"""Serviço de auditoria: registra ações dos usuários."""
from flask import has_request_context, request

from app.extensions import db
from app.models.audit import AuditLog


def log_action(user, action, entity=None, entity_id=None, details=None):
    """Adiciona um registro de auditoria à sessão (commit fica a cargo do chamador)."""
    ip = request.remote_addr if has_request_context() else None
    db.session.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details,
            ip=ip,
        )
    )
