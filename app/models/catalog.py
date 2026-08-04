"""Catálogo de apoio: departamentos, categorias e subcategorias."""
from datetime import datetime

from app.extensions import db


class Department(db.Model):
    """Departamento da empresa (TI, RH, Financeiro...)."""

    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    users = db.relationship("User", back_populates="department")

    def __repr__(self):
        return f"<Department {self.name}>"


class Category(db.Model):
    """Categoria de chamados (Hardware, Software, Redes...)."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    subcategories = db.relationship(
        "Subcategory",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="Subcategory.name",
    )

    def __repr__(self):
        return f"<Category {self.name}>"


class Subcategory(db.Model):
    """Subcategoria vinculada a uma categoria."""

    __tablename__ = "subcategories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    category = db.relationship("Category", back_populates="subcategories")

    __table_args__ = (db.UniqueConstraint("name", "category_id", name="uq_subcat_name_cat"),)

    def __repr__(self):
        return f"<Subcategory {self.name}>"
