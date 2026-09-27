def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_isolamento_entre_testes_parte_1(client):
    """Cadastra um aluno com uma matrícula fixa — se o isolamento entre
    testes estiver quebrado, o teste 'parte_2' vai encontrar conflito
    de matrícula duplicada."""
    resp = client.post(
        "/api/auth/cadastro",
        json={"matricula": "9999999999", "email": "isolamento@ufrb.edu.br", "password": "Senha@123"},
    )
    assert resp.status_code == 201


def test_isolamento_entre_testes_parte_2(client):
    """Mesma matrícula do teste anterior — só passa se cada teste
    realmente rodar numa transação isolada e desfeita ao final."""
    resp = client.post(
        "/api/auth/cadastro",
        json={"matricula": "9999999999", "email": "outro@ufrb.edu.br", "password": "Senha@123"},
    )
    assert resp.status_code == 201
