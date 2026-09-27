"""
CRUD administrativo de empresas/convênios (Fase 5) e vagas (Fase 6),
incluindo o cálculo determinístico de status do convênio e a proteção
admin-only de tudo neste módulo.
"""

import uuid
from datetime import date, timedelta


def test_empresa_crud_exige_admin(client, aluno_a):
    resp = client.get("/api/admin/empresas", headers=aluno_a["headers"])
    assert resp.status_code == 403
    resp = client.post("/api/admin/empresas", headers=aluno_a["headers"], json={"nome": "X"})
    assert resp.status_code == 403


def test_criar_empresa_e_listar(client, admin_headers, mock_ollama):
    resp = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "DevSoft Tecnologia Ltda", "cnpj": "11.111.111/0001-11"})
    assert resp.status_code == 201
    empresa_id = resp.json()["id"]

    resp = client.get("/api/admin/empresas", headers=admin_headers)
    assert any(e["id"] == empresa_id for e in resp.json())


def test_criar_convenio_com_data_futura_fica_vigente(client, admin_headers, mock_ollama):
    empresa_id = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa Convenio"}).json()["id"]
    data_futura = (date.today() + timedelta(days=365)).strftime("%d/%m/%Y")

    resp = client.post(
        f"/api/admin/empresas/{empresa_id}/convenios",
        headers=admin_headers,
        json={"processo": "123/2026", "data_fim_original": data_futura},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "vigente"


def test_criar_convenio_com_data_passada_fica_vencido(client, admin_headers, mock_ollama):
    empresa_id = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa Convenio Vencido"}).json()["id"]
    resp = client.post(
        f"/api/admin/empresas/{empresa_id}/convenios",
        headers=admin_headers,
        json={"processo": "1/2020", "data_fim_original": "01/01/2020"},
    )
    assert resp.json()["status"] == "vencido"


def test_criar_convenio_com_data_malformada_fica_indeterminado_e_preserva_original(client, admin_headers, mock_ollama):
    empresa_id = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa Data Ruim"}).json()["id"]
    resp = client.post(
        f"/api/admin/empresas/{empresa_id}/convenios",
        headers=admin_headers,
        json={"processo": "2/2020", "data_fim_original": "03/102027"},
    )
    assert resp.json()["status"] == "indeterminado"
    assert resp.json()["data_fim_original"] == "03/102027"
    assert resp.json()["data_fim"] is None


def test_criar_vaga_vinculada_a_empresa(client, admin_headers, mock_ollama):
    empresa_id = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa Vaga"}).json()["id"]
    resp = client.post(
        f"/api/admin/empresas/{empresa_id}/vagas",
        headers=admin_headers,
        json={"titulo": "Estágio Backend", "cursos": ["Engenharia de Computação"], "tecnologias": ["Python"]},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "ativa"
    assert resp.json()["empresa_id"] == empresa_id


def test_vaga_com_convenio_de_outra_empresa_e_rejeitada(client, admin_headers, mock_ollama):
    empresa_1 = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa 1"}).json()["id"]
    empresa_2 = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa 2"}).json()["id"]
    convenio_1 = client.post(
        f"/api/admin/empresas/{empresa_1}/convenios", headers=admin_headers, json={"processo": "1/2026"}
    ).json()["id"]

    resp = client.post(
        f"/api/admin/empresas/{empresa_2}/vagas",
        headers=admin_headers,
        json={"titulo": "Vaga", "convenio_id": convenio_1},
    )
    assert resp.status_code == 422


def test_atualizar_status_da_vaga(client, admin_headers, mock_ollama):
    empresa_id = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa Status"}).json()["id"]
    vaga_id = client.post(
        f"/api/admin/empresas/{empresa_id}/vagas", headers=admin_headers, json={"titulo": "Vaga Status"}
    ).json()["id"]

    resp = client.put(f"/api/admin/vagas/{vaga_id}/status", headers=admin_headers, json={"status": "encerrada"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "encerrada"


def test_excluir_vaga(client, admin_headers, mock_ollama):
    empresa_id = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa Excluir"}).json()["id"]
    vaga_id = client.post(
        f"/api/admin/empresas/{empresa_id}/vagas", headers=admin_headers, json={"titulo": "Vaga a excluir"}
    ).json()["id"]

    resp = client.delete(f"/api/admin/vagas/{vaga_id}", headers=admin_headers)
    assert resp.status_code == 204
    assert client.get(f"/api/admin/vagas/{vaga_id}", headers=admin_headers).status_code == 404


def test_listar_vagas_filtra_por_status(client, admin_headers, mock_ollama):
    empresa_id = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa Filtro"}).json()["id"]
    vaga_id = client.post(
        f"/api/admin/empresas/{empresa_id}/vagas", headers=admin_headers, json={"titulo": "Vaga Ativa"}
    ).json()["id"]
    client.put(f"/api/admin/vagas/{vaga_id}/status", headers=admin_headers, json={"status": "encerrada"})

    resp = client.get("/api/admin/vagas?status_filtro=ativa", headers=admin_headers)
    assert vaga_id not in [v["id"] for v in resp.json()]

    resp = client.get("/api/admin/vagas?status_filtro=encerrada", headers=admin_headers)
    assert vaga_id in [v["id"] for v in resp.json()]


def test_vaga_gera_log_de_auditoria_ao_criar_atualizar_e_excluir(client, admin_headers, mock_ollama):
    empresa_id = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": "Empresa Auditoria"}).json()["id"]
    vaga_id = client.post(
        f"/api/admin/empresas/{empresa_id}/vagas", headers=admin_headers, json={"titulo": "Vaga Auditada"}
    ).json()["id"]
    client.put(f"/api/admin/vagas/{vaga_id}/status", headers=admin_headers, json={"status": "encerrada"})
    client.delete(f"/api/admin/vagas/{vaga_id}", headers=admin_headers)

    resp = client.get(f"/api/admin/logs-auditoria?entidade_tipo=vaga", headers=admin_headers)
    acoes = [log["acao"] for log in resp.json() if log["entidade_id"] == vaga_id]
    assert "criar_vaga" in acoes
    assert "atualizar_status_vaga" in acoes
    assert "excluir_vaga" in acoes
