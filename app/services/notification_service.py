"""Serviço de notificações com arquitetura de canais plugáveis.

Canal ativo: banco de dados (sino na interface).
Canais preparados para o futuro: e-mail, Microsoft Teams e Slack — basta
implementar o método send() e registrar a instância em
NotificationService.channels.
"""
import logging
from abc import ABC, abstractmethod

from app.extensions import db
from app.models.notification import Notification
from app.models.user import Role, User

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Contrato de um canal de envio de notificações."""

    @abstractmethod
    def send(self, user, title, message, link=None):
        ...


class DatabaseChannel(NotificationChannel):
    """Grava a notificação no banco (exibida no sino da interface)."""

    def send(self, user, title, message, link=None):
        db.session.add(
            Notification(user_id=user.id, title=title, message=message, link=link)
        )


class EmailChannel(NotificationChannel):
    """Canal de e-mail (stub).

    Para ativar: configure um servidor SMTP (Flask-Mail) e implemente o
    envio aqui, depois registre em NotificationService.channels.
    """

    def send(self, user, title, message, link=None):
        logger.info("[EMAIL stub] para=%s assunto=%s", user.email, title)


class TeamsChannel(NotificationChannel):
    """Canal Microsoft Teams (stub).

    Para ativar: crie um Incoming Webhook no canal do Teams e poste um
    cartão adaptativo via requests.post(webhook_url, json=card).
    """

    def send(self, user, title, message, link=None):
        logger.info("[TEAMS stub] para=%s assunto=%s", user.email, title)


class SlackChannel(NotificationChannel):
    """Canal Slack (stub).

    Para ativar: crie um Incoming Webhook no workspace e poste um bloco
    de mensagem via requests.post(webhook_url, json=payload).
    """

    def send(self, user, title, message, link=None):
        logger.info("[SLACK stub] para=%s assunto=%s", user.email, title)


class NotificationService:
    """Fachada de envio: distribui a notificação por todos os canais ativos."""

    channels = [DatabaseChannel()]

    @classmethod
    def notify(cls, users, title, message, link=None, exclude=None):
        """Notifica um usuário ou lista de usuários (sem duplicar destinatários)."""
        if not isinstance(users, (list, tuple, set)):
            users = [users]
        seen = set()
        for user in users:
            if not user or not user.active:
                continue
            if exclude is not None and user.id == exclude.id:
                continue
            if user.id in seen:
                continue
            seen.add(user.id)
            for channel in cls.channels:
                channel.send(user, title, message, link)

    @classmethod
    def staff(cls):
        """Todos os admins e analistas ativos (equipe de atendimento)."""
        return (
            User.query.join(Role)
            .filter(Role.name.in_([Role.ADMIN, Role.ANALISTA]), User.active.is_(True))
            .all()
        )
