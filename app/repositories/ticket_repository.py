"""Consultas de chamados: visibilidade, filtros e estatísticas do dashboard."""
from datetime import datetime, timedelta

from sqlalchemy import func, or_

from app.models import Category, Ticket, TicketStatus, User

MONTHS_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


class TicketRepository:
    """Consultas reutilizáveis sobre chamados."""

    # ------------------------------------------------------------ visibilidade
    @staticmethod
    def visible_query(user):
        """Chamados que o usuário pode ver, conforme o perfil.

        - admin/analista: todos os chamados;
        - usuário comum: apenas os próprios.
        """
        query = Ticket.query
        if not user.is_staff:
            query = query.filter(Ticket.requester_id == user.id)
        return query

    # ----------------------------------------------------------------- filtros
    @staticmethod
    def apply_filters(query, args):
        """Aplica os filtros da listagem (querystring) sobre a consulta."""
        q = (args.get("q") or "").strip()
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    Ticket.title.ilike(like),
                    Ticket.description.ilike(like),
                    Ticket.number.ilike(like),
                )
            )
        if args.get("status"):
            query = query.filter(Ticket.status == args["status"])
        if args.get("prioridade"):
            query = query.filter(Ticket.priority == args["prioridade"])
        if args.get("categoria"):
            query = query.filter(Ticket.category_id == int(args["categoria"]))
        if args.get("analista"):
            query = query.filter(Ticket.assignee_id == int(args["analista"]))
        if args.get("de"):
            try:
                start = datetime.strptime(args["de"], "%Y-%m-%d")
                query = query.filter(Ticket.created_at >= start)
            except ValueError:
                pass
        if args.get("ate"):
            try:
                end = datetime.strptime(args["ate"], "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(Ticket.created_at < end)
            except ValueError:
                pass
        return query.order_by(Ticket.created_at.desc())

    # ------------------------------------------------------------- estatísticas
    @staticmethod
    def dashboard_cards(base_query):
        """Indicadores numéricos dos cartões do dashboard."""
        total = base_query.count()
        abertos = base_query.filter(Ticket.status.in_(TicketStatus.OPEN_STATES)).count()
        fechados = base_query.filter(
            Ticket.status.in_([TicketStatus.RESOLVIDO, TicketStatus.FECHADO])
        ).count()
        criticos = base_query.filter(
            Ticket.priority == "Crítica",
            Ticket.status.in_(TicketStatus.OPEN_STATES),
        ).count()
        return {
            "total": total,
            "abertos": abertos,
            "fechados": fechados,
            "criticos": criticos,
            "tempo_medio": TicketRepository.avg_resolution_label(base_query),
        }

    @staticmethod
    def avg_resolution_label(base_query):
        """Tempo médio de resolução em texto legível, ou None se não houver dados."""
        resolved = base_query.filter(Ticket.resolved_at.isnot(None)).all()
        if not resolved:
            return None
        total_seconds = sum(
            (t.resolved_at - t.created_at).total_seconds() for t in resolved
        )
        avg_hours = total_seconds / len(resolved) / 3600
        if avg_hours >= 24:
            return f"{avg_hours / 24:.1f} dias"
        if avg_hours >= 1:
            return f"{avg_hours:.1f} h"
        return f"{avg_hours * 60:.0f} min"

    @staticmethod
    def count_by_status(base_query):
        rows = (
            base_query.with_entities(Ticket.status, func.count(Ticket.id))
            .group_by(Ticket.status)
            .all()
        )
        counts = dict(rows)
        labels = [s for s in TicketStatus.ALL if s in counts]
        return {"labels": labels, "data": [counts[s] for s in labels]}

    @staticmethod
    def count_by_category(base_query):
        rows = (
            base_query.join(Category, Ticket.category_id == Category.id)
            .with_entities(Category.name, func.count(Ticket.id))
            .group_by(Category.name)
            .order_by(func.count(Ticket.id).desc())
            .all()
        )
        return {"labels": [r[0] for r in rows], "data": [r[1] for r in rows]}

    @staticmethod
    def count_by_assignee(base_query):
        rows = (
            base_query.join(User, Ticket.assignee_id == User.id)
            .with_entities(User.name, func.count(Ticket.id))
            .group_by(User.name)
            .order_by(func.count(Ticket.id).desc())
            .limit(8)
            .all()
        )
        return {"labels": [r[0] for r in rows], "data": [r[1] for r in rows]}

    @staticmethod
    def monthly_series(base_query, months=6):
        """Série mensal de chamados abertos x resolvidos (últimos N meses).

        Agregação feita em Python para manter compatibilidade entre
        SQLite e PostgreSQL.
        """
        now = datetime.now()
        buckets = []
        year, month = now.year, now.month
        for _ in range(months):
            buckets.append((year, month))
            month -= 1
            if month == 0:
                month, year = 12, year - 1
        buckets.reverse()

        start = datetime(buckets[0][0], buckets[0][1], 1)
        tickets = base_query.filter(Ticket.created_at >= start).all()

        created = {b: 0 for b in buckets}
        resolved = {b: 0 for b in buckets}
        for t in tickets:
            key = (t.created_at.year, t.created_at.month)
            if key in created:
                created[key] += 1
            if t.resolved_at:
                rkey = (t.resolved_at.year, t.resolved_at.month)
                if rkey in resolved:
                    resolved[rkey] += 1

        labels = [f"{MONTHS_PT[m]}/{str(y)[2:]}" for y, m in buckets]
        return {
            "labels": labels,
            "abertos": [created[b] for b in buckets],
            "resolvidos": [resolved[b] for b in buckets],
        }
