"""
Cria (ou atualiza a senha de) o único usuário administrador, a partir
de ADMIN_MATRICULA/ADMIN_EMAIL/ADMIN_PASSWORD no .env. Não existe rota
pública que crie um admin — é sempre este script, rodado por quem tem
acesso ao servidor/ambiente.

Uso: python scripts/seed_admin.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Usuario


def seed():
    if settings.admin_password == "troque-esta-senha-antes-de-rodar-o-seed":
        print("AVISO: ADMIN_PASSWORD ainda está no valor padrão do .env.example.")
        print("Edite o .env com uma senha real antes de continuar em qualquer ambiente compartilhado.")

    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.matricula == settings.admin_matricula).first()
        if usuario:
            usuario.senha_hash = hash_password(settings.admin_password)
            usuario.email = settings.admin_email
            db.commit()
            print(f"OK: senha do admin '{settings.admin_matricula}' atualizada.")
        else:
            usuario = Usuario(
                matricula=settings.admin_matricula,
                email=settings.admin_email,
                senha_hash=hash_password(settings.admin_password),
                role="admin",
            )
            db.add(usuario)
            db.commit()
            print(f"OK: usuário admin '{settings.admin_matricula}' criado.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
