"""Regras de negócio dos chamados: criação, atualização, status e comentários."""
from datetime import datetime

from flask import url_for

from app.extensions import db
from app.models import Ticket, TicketComment, TicketHistory, TicketStatus
from app.services.audit_service import log_action
from app.services.notification_service import NotificationService
from app.services.sla_service import apply_sla


def _history(ticket, user, action, field=None, old=None, new=None):
    """Registra uma entrada na timeline do chamado."""
    db.session.add(
        TicketHistory(
            ticket=ticket,
            user_id=user.id if user else None,
            action=action,
            field=field,
            old_value=str(old) if old is not None else None,
            new_value=str(new) if new is not None else None,
        )
    )


def _ticket_link(ticket):
    return url_for("tickets.detail", ticket_id=ticket.id)


def _notify_parties(ticket, title, message, exclude=None):
    """Notifica solicitante e analista responsável do chamado."""
    NotificationService.notify(
        [ticket.requester, ticket.assignee],
        title,
        message,
        link=_ticket_link(ticket),
        exclude=exclude,
    )


def create_ticket(
    *,
    title,
    description,
    category_id,
    subcategory_id,
    priority,
    requester,
    assignee_id=None,
    is_training=False,
    lab_scenario=None,
):
    """Cria um chamado com número automático, SLA e notificações."""
    ticket = Ticket(
        title=title,
        description=description,
        category_id=category_id,
        subcategory_id=subcategory_id or None,
        priority=priority,
        status=TicketStatus.ABERTO,
        requester_id=requester.id,
        assignee_id=assignee_id,
        is_training=is_training,
        lab_scenario_id=lab_scenario.id if lab_scenario else None,
        created_at=datetime.now(),
    )
    apply_sla(ticket)
    db.session.add(ticket)
    db.session.flush()  # garante o id para compor o número
    ticket.number = f"CH-{ticket.created_at.year}-{ticket.id:05d}"

    _history(ticket, requester, "Chamado criado")
    if assignee_id:
        _history(ticket, requester, "Analista atribuído", field="Analista",
                 new=ticket.assignee.name if ticket.assignee else assignee_id)

    prefix = "[TREINAMENTO] " if is_training else ""
    if is_training and ticket.assignee:
        NotificationService.notify(
            ticket.assignee,
            f"{prefix}Novo chamado {ticket.number}",
            ticket.title,
            link=_ticket_link(ticket),
        )
    else:
        NotificationService.notify(
            NotificationService.staff(),
            f"Novo chamado {ticket.number}",
            ticket.title,
            link=_ticket_link(ticket),
            exclude=requester,
        )
    log_action(requester, "criar", "ticket", ticket.id, f"Chamado {ticket.number} criado")
    db.session.commit()
    return ticket


def update_ticket(ticket, user, data):
    """Atualiza campos editáveis do chamado registrando o diff no histórico."""
    changes = []
    fields = {
        "title": "Título",
        "description": "Descrição",
        "category_id": "Categoria",
        "subcategory_id": "Subcategoria",
        "priority": "Prioridade",
    }
    for attr, label in fields.items():
        if attr not in data:
            continue
        new_value = data[attr]
        old_value = getattr(ticket, attr)
        if str(new_value) == str(old_value):
            continue
        setattr(ticket, attr, new_value)
        if attr == "description":
            _history(ticket, user, "Descrição atualizada")
        else:
            _history(ticket, user, f"{label} alterada", field=label, old=old_value, new=new_value)
        changes.append(label)

    if "priority" in data and "Prioridade" in changes:
        apply_sla(ticket)  # prioridade nova => prazos novos

    if changes:
        _notify_parties(
            ticket,
            f"Chamado {ticket.number} atualizado",
            f"{user.name} alterou: {', '.join(changes)}",
            exclude=user,
        )
        log_action(user, "editar", "ticket", ticket.id, f"Campos: {', '.join(changes)}")
    db.session.commit()
    return changes


def change_status(ticket, user, new_status, solution=None):
    """Altera o status do chamado, controlando datas e notificações."""
    old_status = ticket.status
    if new_status == old_status:
        return False

    ticket.status = new_status
    now = datetime.now()

    if new_status == TicketStatus.RESOLVIDO:
        ticket.resolved_at = now
        if solution:
            ticket.solution = solution
            _history(ticket, user, "Solução registrada")
    elif new_status == TicketStatus.FECHADO:
        ticket.closed_at = now
        if not ticket.resolved_at:
            ticket.resolved_at = now
        if solution:
            ticket.solution = solution
    elif new_status in TicketStatus.OPEN_STATES:
        # Reabertura: limpa as datas de encerramento
        ticket.resolved_at = None
        ticket.closed_at = None

    _history(ticket, user, "Status alterado", field="Status", old=old_status, new=new_status)

    if new_status == TicketStatus.FECHADO:
        title = f"Chamado {ticket.number} encerrado"
    else:
        title = f"Chamado {ticket.number}: {new_status}"
    _notify_parties(ticket, title, f"Status alterado por {user.name}.", exclude=user)
    log_action(user, "alterar_status", "ticket", ticket.id, f"{old_status} -> {new_status}")
    db.session.commit()
    return True


def assign_ticket(ticket, user, assignee):
    """Atribui (ou assume) um chamado para um analista."""
    old = ticket.assignee.name if ticket.assignee else None
    ticket.assignee_id = assignee.id
    if ticket.status == TicketStatus.ABERTO:
        ticket.status = TicketStatus.EM_ANDAMENTO
        _history(ticket, user, "Status alterado", field="Status",
                 old=TicketStatus.ABERTO, new=TicketStatus.EM_ANDAMENTO)
    _history(ticket, user, "Analista atribuído", field="Analista", old=old, new=assignee.name)
    NotificationService.notify(
        [ticket.requester, assignee],
        f"Chamado {ticket.number} atribuído",
        f"Analista responsável: {assignee.name}.",
        link=_ticket_link(ticket),
        exclude=user,
    )
    log_action(user, "atribuir", "ticket", ticket.id, f"Analista: {assignee.name}")
    db.session.commit()


def add_comment(ticket, user, content, is_internal=False):
    """Adiciona comentário público ou interno e notifica os envolvidos."""
    comment = TicketComment(
        ticket_id=ticket.id, user_id=user.id, content=content, is_internal=is_internal
    )
    db.session.add(comment)

    # Primeira resposta da equipe conta para o SLA de resposta
    if user.is_staff and not ticket.first_response_at and not is_internal:
        ticket.first_response_at = datetime.now()

    kind = "interno" if is_internal else "público"
    _history(ticket, user, f"Comentário {kind} adicionado")

    if is_internal:
        # Comentários internos não chegam ao solicitante
        NotificationService.notify(
            ticket.assignee,
            f"Comentário interno em {ticket.number}",
            f"{user.name} comentou internamente.",
            link=_ticket_link(ticket),
            exclude=user,
        )
    else:
        _notify_parties(
            ticket,
            f"Novo comentário em {ticket.number}",
            f"{user.name} comentou no chamado.",
            exclude=user,
        )
    log_action(user, "comentar", "ticket", ticket.id, f"Comentário {kind}")
    db.session.commit()
    return comment


def rate_ticket(ticket, user, rating, comment=None):
    """Registra a avaliação do atendimento pelo solicitante."""
    ticket.rating = rating
    ticket.rating_comment = comment
    _history(ticket, user, "Atendimento avaliado", field="Nota", new=f"{rating}/5")
    NotificationService.notify(
        ticket.assignee,
        f"Chamado {ticket.number} avaliado",
        f"Nota {rating}/5 dada por {user.name}.",
        link=_ticket_link(ticket),
    )
    log_action(user, "avaliar", "ticket", ticket.id, f"Nota {rating}/5")
    db.session.commit()
