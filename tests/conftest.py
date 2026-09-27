"""
Fixtures da suíte de testes automatizados (Fase 11 / passo 31).

Banco de teste: mesmo Postgres do docker-compose, banco separado
("<database>_test"), recriado do zero uma vez por sessão de pytest —
nunca toca no banco de desenvolvimento. Cada teste roda dentro de uma
transação própria que é desfeita (rollback) ao final, então nenhum
teste enxerga dado gravado por outro (isolamento sem precisar recriar
o schema a cada teste, que seria lento).

Chamadas ao Ollama (embeddings/LLM) NUNCA acontecem de verdade nesta
suíte — são sempre monkeypatchadas (fixture `mock_ollama`) para
respostas determinísticas. Depender do Ollama real tornaria os testes
lentos (minutos) e não-reprodutíveis; a lógica que importa aqui é a
do pipeline/regras/serialização, não a qualidade da resposta do LLM
em si (isso é o "passo 32" — avaliação humana, feita à parte).
"""

import uuid
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import Base
from app.models.catalogo import Centro, Curso
from app.models.usuario import Usuario


def _test_database_url() -> str:
    parsed = urlparse(settings.database_url)
    base_db = parsed.path.lstrip("/")
    return urlunparse(parsed._replace(path=f"/{base_db}_test"))


def _admin_connection_url() -> str:
    """URL (driver psycopg puro, autocommit) para o banco `postgres`,
    usada só para DROP/CREATE DATABASE — não dá para recriar o banco
    a partir de uma conexão já aberta nele."""
    parsed = urlparse(settings.database_url)
    return urlunparse(parsed._replace(path="/postgres", scheme="postgresql"))


TEST_DB_NAME = urlparse(_test_database_url()).path.lstrip("/")


@pytest.fixture(scope="session")
def test_engine():
    admin_conn = psycopg.connect(_admin_connection_url(), autocommit=True)
    try:
        admin_conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
        admin_conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        admin_conn.close()

    test_url = _test_database_url().replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(test_url)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()
    admin_conn = psycopg.connect(_admin_connection_url(), autocommit=True)
    try:
        admin_conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
    finally:
        admin_conn.close()


@pytest.fixture()
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    # join_transaction_mode="create_savepoint": a sessão roda dentro da
    # transação externa via SAVEPOINT — um `db.commit()" feito pelo
    # código de produção (routers) libera só o savepoint, nunca a
    # transação externa. Sem isso, o primeiro commit "vazaria" os dados
    # para fora do teste (e o rollback final não desfaria nada real).
    SessionTeste = sessionmaker(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")
    session: Session = SessionTeste()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def curso_ti(db_session):
    """Centro/curso mínimos — o suficiente para os testes que precisam
    de `aluno.curso` (regras de compatibilidade de curso, Fase 8)."""
    centro = Centro(id="cetec", nome="Centro de Ciências Exatas e Tecnológicas")
    db_session.add(centro)
    db_session.flush()
    curso = Curso(centro_id=centro.id, nome="Engenharia de Computação")
    db_session.add(curso)
    db_session.flush()
    return curso


@pytest.fixture()
def admin_user(db_session):
    usuario = Usuario(
        matricula=settings.admin_matricula,
        email=settings.admin_email,
        senha_hash=hash_password("SenhaAdminTeste@123"),
        role="admin",
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario, "SenhaAdminTeste@123"


@pytest.fixture()
def admin_headers(client, admin_user):
    usuario, senha = admin_user
    resp = client.post("/api/auth/login", json={"matricula": usuario.matricula, "password": senha})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _cadastrar_aluno(client, matricula: str, email: str, senha: str = "SenhaAluno@123"):
    resp = client.post(
        "/api/auth/cadastro",
        json={"matricula": matricula, "email": email, "password": senha},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def aluno_a(client):
    """Primeiro aluno de teste — usado sempre que só um basta."""
    data = _cadastrar_aluno(client, "2030000001", "aluno.a@ufrb.edu.br")
    token = data["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "usuario": data["usuario"]}


@pytest.fixture()
def aluno_b(client):
    """Segundo aluno de teste — usado nos testes de isolamento entre
    contas (garantir que um aluno nunca vê dado do outro)."""
    data = _cadastrar_aluno(client, "2030000002", "aluno.b@ufrb.edu.br")
    token = data["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "usuario": data["usuario"]}


@pytest.fixture()
def mock_ollama(monkeypatch):
    """Substitui as duas únicas portas de saída para o Ollama por
    respostas determinísticas. `vetor_fixo` é o mesmo vetor sempre —
    suficiente para exercitar a busca por cosseno (pgvector aceita
    qualquer vetor válido; não estamos testando a QUALIDADE da busca
    semântica aqui, isso já foi validado manualmente na Fase 7 contra
    o Ollama real, ver scripts/test_fase7_manual.py)."""
    import app.services.embeddings.service as embeddings_service
    import app.services.recomendacao.analise as analise_module

    vetor_fixo = [0.01] * settings.embedding_dim

    def _fake_generate_embedding(texto: str):
        return vetor_fixo

    def _fake_generate_completion(prompt, system=None, json_format=False):
        return (
            '{"nivel": "alta", "indice": 88, '
            '"pontos_compativeis": ["Python"], "pontos_parciais": [], '
            '"lacunas": [], "justificativa": "Compatibilidade de teste (mock)."}'
        )

    monkeypatch.setattr(embeddings_service, "generate_embedding", _fake_generate_embedding)
    monkeypatch.setattr(analise_module, "generate_completion", _fake_generate_completion)
    return {"vetor_fixo": vetor_fixo}


@pytest.fixture()
def novo_uuid():
    return uuid.uuid4
