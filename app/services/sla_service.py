"""Serviço de SLA: cálculo de prazos e estado dos chamados."""
from datetime import datetime, timedelta

from app.models.sla import SLARule
from app.models.ticket import TicketStatus


def apply_sla(ticket):
    """Define os prazos de resposta e resolução conforme a prioridade.

    Usa a data de abertura do chamado como base; deve ser chamado na
    criação e sempre que a prioridade for alterada.
    """
    rule = SLARule.query.filter_by(priority=ticket.priority, active=True).first()
    if not rule:
        ticket.response_due_at = None
        ticket.resolution_due_at = None
        return
    base = ticket.created_at or datetime.now()
    ticket.response_due_at = base + timedelta(minutes=rule.response_minutes)
    ticket.resolution_due_at = base + timedelta(minutes=rule.resolution_minutes)


def sla_state(ticket):
    """Retorna o estado do SLA de resolução do chamado.

    Códigos possíveis:
        ok       — dentro do prazo
        at_risk  — restam menos de 25% do tempo
        expired  — prazo estourado e chamado ainda aberto
        met      — resolvido dentro do prazo
        breached — resolvido fora do prazo
        none     — sem regra de SLA
    """
    due = ticket.resolution_due_at
    if not due:
        return {"label": "Sem SLA", "css": "secondary", "code": "none"}

    end = ticket.resolved_at or ticket.closed_at
    if end:
        if end <= due:
            return {"label": "SLA cumprido", "css": "success", "code": "met"}
        return {"label": "SLA violado", "css": "danger", "code": "breached"}

    now = datetime.now()
    if now > due:
        return {"label": "SLA vencido", "css": "danger", "code": "expired"}

    total = (due - (ticket.created_at or now)).total_seconds()
    remaining = (due - now).total_seconds()
    if total > 0 and remaining / total <= 0.25:
        return {"label": "SLA em risco", "css": "warning", "code": "at_risk"}
    return {"label": "No prazo", "css": "success", "code": "ok"}


def tickets_at_risk(limit=10):
    """Chamados abertos com SLA vencido ou perto de vencer (para alertas)."""
    from app.models.ticket import Ticket

    open_tickets = (
        Ticket.query.filter(
            Ticket.status.in_(TicketStatus.OPEN_STATES),
            Ticket.resolution_due_at.isnot(None),
        )
        .order_by(Ticket.resolution_due_at)
        .all()
    )
    flagged = [t for t in open_tickets if sla_state(t)["code"] in ("expired", "at_risk")]
    return flagged[:limit]
