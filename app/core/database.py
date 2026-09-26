"""
Conexão com o PostgreSQL e gerenciamento de sessão do SQLAlchemy. Todo
router pega uma sessão via a dependency `get_db` — nunca abre uma
conexão por conta própria, para que o pool de conexões seja único e
compartilhado pela aplicação inteira.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
