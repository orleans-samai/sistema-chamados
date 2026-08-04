"""Base de conhecimento: artigos, tutoriais e FAQ."""
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Category, KnowledgeArticle
from app.services.audit_service import log_action

kb_bp = Blueprint("kb", __name__)


@kb_bp.route("/")
@login_required
def list_articles():
    page = request.args.get("page", 1, type=int)
    q = (request.args.get("q") or "").strip()
    tipo = request.args.get("tipo") or ""
    categoria = request.args.get("categoria", type=int)
    tag = (request.args.get("tag") or "").strip()

    query = KnowledgeArticle.query
    if not current_user.is_staff:
        query = query.filter(KnowledgeArticle.published.is_(True))
    if q:
        like = f"%{q}%"
        query = query.filter(
            (KnowledgeArticle.title.ilike(like))
            | (KnowledgeArticle.content.ilike(like))
            | (KnowledgeArticle.tags.ilike(like))
        )
    if tipo in KnowledgeArticle.TYPES:
        query = query.filter(KnowledgeArticle.article_type == tipo)
    if categoria:
        query = query.filter(KnowledgeArticle.category_id == categoria)
    if tag:
        query = query.filter(KnowledgeArticle.tags.ilike(f"%{tag}%"))

    pagination = query.order_by(KnowledgeArticle.updated_at.desc()).paginate(
        page=page, per_page=current_app.config["ITEMS_PER_PAGE"], error_out=False
    )
    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    return render_template(
        "kb/list.html",
        pagination=pagination,
        articles=pagination.items,
        categories=categories,
        q=q,
        tipo=tipo,
        categoria=categoria,
        tag=tag,
    )


@kb_bp.route("/artigo/<int:article_id>")
@login_required
def article(article_id):
    item = db.session.get(KnowledgeArticle, article_id) or abort(404)
    if not item.published and not current_user.is_staff:
        abort(404)
    item.views += 1
    db.session.commit()
    return render_template("kb/article.html", article=item)


def _article_form_data():
    return {
        "title": (request.form.get("title") or "").strip(),
        "summary": (request.form.get("summary") or "").strip(),
        "content": (request.form.get("content") or "").strip(),
        "article_type": request.form.get("article_type") or KnowledgeArticle.TIPO_ARTIGO,
        "category_id": request.form.get("category_id", type=int) or None,
        "tags": (request.form.get("tags") or "").strip(),
        "published": bool(request.form.get("published")),
    }


@kb_bp.route("/novo", methods=["GET", "POST"])
@login_required
def new_article():
    if not current_user.is_staff:
        abort(403)
    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    if request.method == "POST":
        data = _article_form_data()
        if not data["title"] or not data["content"]:
            flash("Preencha título e conteúdo.", "warning")
        else:
            item = KnowledgeArticle(author_id=current_user.id, **data)
            db.session.add(item)
            db.session.flush()
            log_action(current_user, "criar", "kb_article", item.id, item.title)
            db.session.commit()
            flash("Artigo publicado na base de conhecimento.", "success")
            return redirect(url_for("kb.article", article_id=item.id))
    return render_template("kb/form.html", article=None, categories=categories)


@kb_bp.route("/<int:article_id>/editar", methods=["GET", "POST"])
@login_required
def edit_article(article_id):
    if not current_user.is_staff:
        abort(403)
    item = db.session.get(KnowledgeArticle, article_id) or abort(404)
    categories = Category.query.filter_by(active=True).order_by(Category.name).all()
    if request.method == "POST":
        data = _article_form_data()
        if not data["title"] or not data["content"]:
            flash("Preencha título e conteúdo.", "warning")
        else:
            for key, value in data.items():
                setattr(item, key, value)
            log_action(current_user, "editar", "kb_article", item.id, item.title)
            db.session.commit()
            flash("Artigo atualizado.", "success")
            return redirect(url_for("kb.article", article_id=item.id))
    return render_template("kb/form.html", article=item, categories=categories)


@kb_bp.route("/<int:article_id>/excluir", methods=["POST"])
@login_required
def delete_article(article_id):
    if not current_user.is_admin:
        abort(403)
    item = db.session.get(KnowledgeArticle, article_id) or abort(404)
    log_action(current_user, "excluir", "kb_article", item.id, item.title)
    db.session.delete(item)
    db.session.commit()
    flash("Artigo excluído.", "success")
    return redirect(url_for("kb.list_articles"))
