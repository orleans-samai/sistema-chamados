"""Configurações da aplicação Service Desk."""
import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuração base (desenvolvimento com SQLite).

    Para migrar para PostgreSQL no futuro, basta definir a variável de
    ambiente DATABASE_URL, por exemplo:
        postgresql+psycopg2://usuario:senha@localhost:5432/servicedesk
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASEDIR, "instance", "servicedesk.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads de anexos
    UPLOAD_FOLDER = os.path.join(BASEDIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB por requisição
    ALLOWED_EXTENSIONS = {
        "png", "jpg", "jpeg", "gif", "pdf", "txt", "log",
        "doc", "docx", "xls", "xlsx", "csv", "zip",
    }

    # Paginação padrão das listagens
    ITEMS_PER_PAGE = 10

    # Validade do token de redefinição de senha (em segundos)
    RESET_TOKEN_MAX_AGE = 3600
