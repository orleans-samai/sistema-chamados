"""Central de notificações do usuário."""
from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Notification

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/")
@login_required
def list_notifications():
    page = request.args.get("page", 1, type=int)
    pagination = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .paginate(page=page, per_page=current_app.config["ITEMS_PER_PAGE"], error_out=False)
    )
    return render_template("notifications/list.html", pagination=pagination)


@notifications_bp.route("/ler/<int:notification_id>")
@login_required
def read(notification_id):
    """Marca como lida e segue para o link da notificação."""
    notification = db.session.get(Notification, notification_id) or abort(404)
    if notification.user_id != current_user.id:
        abort(403)
    notification.read = True
    db.session.commit()
    if notification.link:
        return redirect(notification.link)
    return redirect(url_for("notifications.list_notifications"))


@notifications_bp.route("/ler-todas", methods=["POST"])
@login_required
def read_all():
    Notification.query.filter_by(user_id=current_user.id, read=False).update({"read": True})
    db.session.commit()
    return redirect(url_for("notifications.list_notifications"))
