"""Notificações internas dos usuários."""
from datetime import datetime

from app.extensions import db


class Notification(db.Model):
    """Notificação exibida no sino da interface."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(500))
    link = db.Column(db.String(255))
    read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    user = db.relationship("User", backref="notifications")

    def __repr__(self):
        return f"<Notification {self.title}>"
