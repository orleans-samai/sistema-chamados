"""Chamados, comentários, histórico e anexos."""
from datetime import datetime

from app.extensions import db


class TicketPriority:
    """Prioridades possíveis de um chamado."""

    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"

    ALL = [BAIXA, MEDIA, ALTA, CRITICA]
    BADGES = {BAIXA: "secondary", MEDIA: "info", ALTA: "warning", CRITICA: "danger"}


class TicketStatus:
    """Status do ciclo de vida de um chamado."""

    ABERTO = "Aberto"
    EM_ANDAMENTO = "Em andamento"
    AGUARDANDO = "Aguardando usuário"
    RESOLVIDO = "Resolvido"
    FECHADO = "Fechado"

    ALL = [ABERTO, EM_ANDAMENTO, AGUARDANDO, RESOLVIDO, FECHADO]
    OPEN_STATES = [ABERTO, EM_ANDAMENTO, AGUARDANDO]
    BADGES = {
        ABERTO: "primary",
        EM_ANDAMENTO: "info",
        AGUARDANDO: "warning",
        RESOLVIDO: "success",
        FECHADO: "secondary",
    }


class Ticket(db.Model):
    """Chamado de suporte."""

    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey("subcategories.id"))
    priority = db.Column(db.String(20), default=TicketPriority.MEDIA, nullable=False)
    status = db.Column(db.String(30), default=TicketStatus.ABERTO, nullable=False, index=True)

    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    first_response_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    # Prazos calculados a partir das regras de SLA
    response_due_at = db.Column(db.DateTime)
    resolution_due_at = db.Column(db.DateTime)

    solution = db.Column(db.Text)
    rating = db.Column(db.Integer)  # 1 a 5
    rating_comment = db.Column(db.String(500))

    # Laboratório de treinamento
    is_training = db.Column(db.Boolean, default=False, nullable=False)
    lab_scenario_id = db.Column(db.Integer, db.ForeignKey("lab_scenarios.id"))

    category = db.relationship("Category")
    subcategory = db.relationship("Subcategory")
    requester = db.relationship("User", foreign_keys=[requester_id], backref="created_tickets")
    assignee = db.relationship("User", foreign_keys=[assignee_id], backref="assigned_tickets")
    lab_scenario = db.relationship("LabScenario", back_populates="tickets")

    comments = db.relationship(
        "TicketComment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at",
    )
    history = db.relationship(
        "TicketHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketHistory.created_at.desc()",
    )
    attachments = db.relationship(
        "Attachment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Attachment.created_at",
    )

    @property
    def is_open(self):
        return self.status in TicketStatus.OPEN_STATES

    @property
    def sla(self):
        """Estado atual do SLA de resolução (dict com label/css/code)."""
        from app.services.sla_service import sla_state

        return sla_state(self)

    @property
    def public_comments(self):
        return [c for c in self.comments if not c.is_internal]

    def __repr__(self):
        return f"<Ticket {self.number}>"


class TicketComment(db.Model):
    """Comentário público ou interno de um chamado."""

    __tablename__ = "ticket_comments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    ticket = db.relationship("Ticket", back_populates="comments")
    user = db.relationship("User")

    def __repr__(self):
        return f"<TicketComment {self.id}>"


class TicketHistory(db.Model):
    """Registro de cada alteração feita em um chamado (timeline)."""

    __tablename__ = "ticket_history"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(120), nullable=False)
    field = db.Column(db.String(60))
    old_value = db.Column(db.String(255))
    new_value = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    ticket = db.relationship("Ticket", back_populates="history")
    user = db.relationship("User")

    def __repr__(self):
        return f"<TicketHistory {self.action}>"


class Attachment(db.Model):
    """Arquivo anexado a um chamado."""

    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)  # nome original
    stored_name = db.Column(db.String(255), nullable=False)  # nome no disco
    size = db.Column(db.Integer, default=0)
    content_type = db.Column(db.String(120))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    ticket = db.relationship("Ticket", back_populates="attachments")
    uploaded_by = db.relationship("User")

    @property
    def size_label(self):
        size = self.size or 0
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.0f} KB"
        return f"{size} B"

    def __repr__(self):
        return f"<Attachment {self.filename}>"
