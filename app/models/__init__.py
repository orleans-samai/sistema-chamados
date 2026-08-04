"""Modelos do banco de dados (SQLAlchemy)."""
from app.models.audit import AuditLog
from app.models.catalog import Category, Department, Subcategory
from app.models.knowledge import KnowledgeArticle
from app.models.lab import LabScenario
from app.models.notification import Notification
from app.models.sla import SLARule
from app.models.ticket import (
    Attachment,
    Ticket,
    TicketComment,
    TicketHistory,
    TicketPriority,
    TicketStatus,
)
from app.models.user import Role, User

__all__ = [
    "AuditLog",
    "Attachment",
    "Category",
    "Department",
    "KnowledgeArticle",
    "LabScenario",
    "Notification",
    "Role",
    "SLARule",
    "Subcategory",
    "Ticket",
    "TicketComment",
    "TicketHistory",
    "TicketPriority",
    "TicketStatus",
    "User",
]
