"""Regras de SLA por prioridade."""
from datetime import datetime

from app.extensions import db


class SLARule(db.Model):
    """Tempos de resposta e resolução (em minutos) para cada prioridade."""

    __tablename__ = "sla_rules"

    id = db.Column(db.Integer, primary_key=True)
    priority = db.Column(db.String(20), unique=True, nullable=False)
    response_minutes = db.Column(db.Integer, nullable=False)
    resolution_minutes = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    @staticmethod
    def format_minutes(minutes):
        """Formata minutos como texto legível (ex.: 90 -> '1h 30min')."""
        if minutes is None:
            return "—"
        hours, mins = divmod(int(minutes), 60)
        if hours and mins:
            return f"{hours}h {mins}min"
        if hours:
            return f"{hours}h"
        return f"{mins}min"

    @property
    def response_label(self):
        return self.format_minutes(self.response_minutes)

    @property
    def resolution_label(self):
        return self.format_minutes(self.resolution_minutes)

    def __repr__(self):
        return f"<SLARule {self.priority}>"
