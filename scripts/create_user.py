"""Cria um usuário por linha de comando (útil para testes).

Uso:
    .venv\\Scripts\\python scripts\\create_user.py --nome teste --senha teste
    .venv\\Scripts\\python scripts\\create_user.py --nome "Ana Dias" --email ana@empresa.com --senha 123456 --perfil analista
"""
import argparse
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Role, User  # noqa: E402


def slugify(name):
    """Transforma o nome em um e-mail simples (ana dias -> ana.dias@empresa.com)."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return normalized.strip().lower().replace(" ", ".")


def main():
    parser = argparse.ArgumentParser(description="Cria um usuário no Service Desk.")
    parser.add_argument("--nome", required=True, help="Nome do usuário")
    parser.add_argument("--email", help="E-mail (padrão: <nome>@empresa.com)")
    parser.add_argument("--senha", required=True, help="Senha de acesso")
    parser.add_argument(
        "--perfil",
        choices=[Role.ADMIN, Role.ANALISTA, Role.USUARIO],
        default=Role.USUARIO,
        help="Perfil de acesso (padrão: usuario)",
    )
    args = parser.parse_args()

    email = (args.email or f"{slugify(args.nome)}@empresa.com").lower()

    app = create_app()
    with app.app_context():
        if User.query.filter(db.func.lower(User.email) == email).first():
            print(f"Já existe um usuário com o e-mail {email}.")
            sys.exit(1)
        role = Role.query.filter_by(name=args.perfil).first()
        if not role:
            print("Perfis não encontrados — rode 'flask seed' primeiro.")
            sys.exit(1)

        user = User(name=args.nome, email=email, role=role, active=True)
        user.set_password(args.senha)
        user.generate_api_token()
        db.session.add(user)
        db.session.commit()
        print(f"Usuário criado: {user.name} <{user.email}> — perfil {role.label}")


if __name__ == "__main__":
    main()
