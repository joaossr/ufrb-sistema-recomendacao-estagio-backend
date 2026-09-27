"""
Painel admin enxergando alunos reais (Fase 10 / passo 27).
"""

import uuid


def test_listar_alunos_exige_admin(client, aluno_a):
    resp = client.get("/api/admin/alunos", headers=aluno_a["headers"])
    assert resp.status_code == 403


def test_listar_alunos_sem_token_retorna_401(client):
    resp = client.get("/api/admin/alunos")
    assert resp.status_code == 401


def test_listar_alunos_retorna_o_aluno_cadastrado(client, admin_headers, aluno_a):
    resp = client.get("/api/admin/alunos", headers=admin_headers)
    assert resp.status_code == 200
    matriculas = [a["matricula"] for a in resp.json()]
    assert aluno_a["usuario"]["matricula"] in matriculas


def test_listar_alunos_reflete_contagens_corretas(client, admin_headers, aluno_a, mock_ollama):
    client.post("/api/perfil/tecnologias", headers=aluno_a["headers"], json={"name": "Go", "level": "Básico"})
    client.post(
        "/api/perfil/projetos", headers=aluno_a["headers"], json={"name": "P1", "description": "", "technologies": []}
    )

    resp = client.get("/api/admin/alunos", headers=admin_headers)
    entrada = next(a for a in resp.json() if a["matricula"] == aluno_a["usuario"]["matricula"])
    assert entrada["num_tecnologias"] == 1
    assert entrada["num_projetos"] == 1
    assert entrada["tem_embedding"] is True  # mock_ollama garante que o embedding foi "gerado"


def test_detalhe_de_aluno_traz_tudo(client, admin_headers, aluno_a, mock_ollama):
    client.post("/api/perfil/tecnologias", headers=aluno_a["headers"], json={"name": "Rust", "level": "Básico"})

    resp = client.get("/api/admin/alunos", headers=admin_headers)
    aluno_id = next(a["id"] for a in resp.json() if a["matricula"] == aluno_a["usuario"]["matricula"])

    resp = client.get(f"/api/admin/alunos/{aluno_id}", headers=admin_headers)
    assert resp.status_code == 200
    detalhe = resp.json()
    assert detalhe["perfil"]["registration_number"] == aluno_a["usuario"]["matricula"]
    assert [t["name"] for t in detalhe["tecnologias"]] == ["Rust"]


def test_detalhe_de_aluno_inexistente_retorna_404(client, admin_headers):
    resp = client.get(f"/api/admin/alunos/{uuid.uuid4()}", headers=admin_headers)
    assert resp.status_code == 404
