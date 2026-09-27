"""
Testes de autenticação (Fase 2): cadastro, login, /me e o efeito
colateral novo da Fase 11 (log de auditoria de login sucesso/falha).
"""


def test_cadastro_cria_usuario_e_retorna_token(client):
    resp = client.post(
        "/api/auth/cadastro",
        json={"matricula": "2027000001", "email": "novo@ufrb.edu.br", "password": "SenhaForte@123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["access_token"]
    assert data["usuario"]["matricula"] == "2027000001"
    assert data["usuario"]["role"] == "aluno"


def test_cadastro_com_matricula_duplicada_retorna_409(client, aluno_a):
    resp = client.post(
        "/api/auth/cadastro",
        json={"matricula": aluno_a["usuario"]["matricula"], "email": "outro@ufrb.edu.br", "password": "Senha@123"},
    )
    assert resp.status_code == 409


def test_cadastro_com_matricula_do_admin_e_bloqueado(client):
    resp = client.post(
        "/api/auth/cadastro",
        json={"matricula": "admin.cetec", "email": "fake-admin@ufrb.edu.br", "password": "Senha@123"},
    )
    assert resp.status_code == 409


def test_login_com_credenciais_corretas_funciona(client, aluno_a):
    resp = client.post(
        "/api/auth/login", json={"matricula": aluno_a["usuario"]["matricula"], "password": "SenhaAluno@123"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_com_senha_errada_retorna_401(client, aluno_a):
    resp = client.post(
        "/api/auth/login", json={"matricula": aluno_a["usuario"]["matricula"], "password": "senha-errada"}
    )
    assert resp.status_code == 401


def test_login_com_matricula_inexistente_retorna_401(client):
    resp = client.post("/api/auth/login", json={"matricula": "0000000000", "password": "qualquer"})
    assert resp.status_code == 401


def test_me_sem_token_retorna_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_com_token_valido_retorna_dados_do_usuario(client, aluno_a):
    resp = client.get("/api/auth/me", headers=aluno_a["headers"])
    assert resp.status_code == 200
    assert resp.json()["matricula"] == aluno_a["usuario"]["matricula"]


def test_me_com_token_invalido_retorna_401(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer token-invalido"})
    assert resp.status_code == 401


def test_login_bem_sucedido_gera_log_de_auditoria(client, admin_headers, aluno_a):
    resp = client.get("/api/admin/logs-auditoria?entidade_tipo=usuario", headers=admin_headers)
    assert resp.status_code == 200
    logs = resp.json()
    acoes = {log["acao"] for log in logs}
    assert "login_sucesso" in acoes


def test_login_falho_gera_log_sem_expor_a_senha(client, admin_headers, aluno_a):
    client.post("/api/auth/login", json={"matricula": aluno_a["usuario"]["matricula"], "password": "errada-de-novo"})
    resp = client.get("/api/admin/logs-auditoria?entidade_tipo=usuario", headers=admin_headers)
    falhas = [log for log in resp.json() if log["acao"] == "login_falha"]
    assert len(falhas) >= 1
    assert "errada-de-novo" not in str(falhas[0]["detalhes"])
