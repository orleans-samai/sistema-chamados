"""Laboratório de treinamento para analistas N1/N2."""
from datetime import datetime

from app.extensions import db


class LabScenario(db.Model):
    """Cenário simulado criado por administradores para treinar analistas."""

    __tablename__ = "lab_scenarios"

    AREAS = [
        "Suporte técnico",
        "Redes",
        "Windows",
        "Impressoras",
        "Microsoft 365",
        "Active Directory",
        "Segurança da informação",
    ]
    LEVELS = ["N1", "N2"]

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    area = db.Column(db.String(60), nullable=False)
    level = db.Column(db.String(5), default="N1", nullable=False)
    priority = db.Column(db.String(20), default="Média", nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    description = db.Column(db.Text, nullable=False)  # vira a descrição do chamado simulado
    expected_solution = db.Column(db.Text)  # gabarito visível apenas para admins
    hints = db.Column(db.Text)  # dicas opcionais para o analista
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    category = db.relationship("Category")
    created_by = db.relationship("User")
    tickets = db.relationship("Ticket", back_populates="lab_scenario")

    def __repr__(self):
        return f"<LabScenario {self.title}>"
