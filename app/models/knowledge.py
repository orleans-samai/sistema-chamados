"""Base de conhecimento: artigos, tutoriais e FAQ."""
from datetime import datetime

from app.extensions import db


class KnowledgeArticle(db.Model):
    """Artigo da base de conhecimento."""

    __tablename__ = "knowledge_base"

    TIPO_ARTIGO = "Artigo"
    TIPO_TUTORIAL = "Tutorial"
    TIPO_FAQ = "FAQ"
    TYPES = [TIPO_ARTIGO, TIPO_TUTORIAL, TIPO_FAQ]

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(500))
    content = db.Column(db.Text, nullable=False)
    article_type = db.Column(db.String(20), default=TIPO_ARTIGO, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    tags = db.Column(db.String(255))  # separadas por vírgula
    views = db.Column(db.Integer, default=0, nullable=False)
    published = db.Column(db.Boolean, default=True, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    category = db.relationship("Category")
    author = db.relationship("User")

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def __repr__(self):
        return f"<KnowledgeArticle {self.title}>"
