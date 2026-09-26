"""Verificação manual da Fase 6 (CRUD de vagas)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

BASE = "http://127.0.0.1:8000/api"


def main():
    admin_login = requests.post(BASE + "/auth/login", json={"matricula": "admin.cetec", "password": "UfrbAdmin@2026Local!"})
    admin_login.raise_for_status()
    headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    aluno_login = requests.post(BASE + "/auth/login", json={"matricula": "2026333444", "password": "senha123"})
    aluno_headers = {"Authorization": f"Bearer {aluno_login.json()['access_token']}"}

    print("== Pegando uma empresa real (do PDF importado na Fase 5) ==")
    empresas = requests.get(BASE + "/admin/empresas", headers=headers).json()
    empresa = empresas[0]
    print("empresa:", empresa["nome"])

    print("\n== Aluno tentando criar vaga (esperado 403) ==")
    r = requests.post(BASE + f"/admin/empresas/{empresa['id']}/vagas", headers=aluno_headers, json={"titulo": "x"})
    print(" ", r.status_code)
    assert r.status_code == 403

    print("\n== Criando vaga ativa ==")
    r = requests.post(
        BASE + f"/admin/empresas/{empresa['id']}/vagas",
        headers=headers,
        json={
            "titulo": "Estágio em Desenvolvimento de Software",
            "descricao": "Apoio no desenvolvimento de sistemas internos.",
            "atividades": "Codificação, testes, documentação.",
            "requisitos": "Cursando Engenharia de Computação ou similar.",
            "cursos": ["Engenharia de Computação"],
            "areas": ["Desenvolvimento Web"],
            "tecnologias": ["Python", "FastAPI"],
            "modalidade": "Híbrido",
            "localizacao": "Cruz das Almas, BA",
            "bolsa": "R$ 700,00",
            "carga_horaria": "20h semanais",
            "quantidade": 2,
        },
    )
    print(" ", r.status_code, r.json())
    assert r.status_code == 201
    vaga = r.json()
    assert vaga["status"] == "ativa"
    vaga_id = vaga["id"]

    print("\n== GET /admin/vagas (todas) ==")
    r = requests.get(BASE + "/admin/vagas", headers=headers)
    print(" total:", len(r.json()))
    assert len(r.json()) >= 1

    print("\n== GET /admin/vagas?status_filtro=ativa ==")
    r = requests.get(BASE + "/admin/vagas", headers=headers, params={"status_filtro": "ativa"})
    assert all(v["status"] == "ativa" for v in r.json())
    print(" OK, todas ativas")

    print("\n== PUT /admin/vagas/{id}/status -> encerrada ==")
    r = requests.put(BASE + f"/admin/vagas/{vaga_id}/status", headers=headers, json={"status": "encerrada"})
    print(" ", r.status_code, r.json()["status"])
    assert r.json()["status"] == "encerrada"

    print("\n== PUT /admin/vagas/{id}/status com valor invalido (esperado 422) ==")
    r = requests.put(BASE + f"/admin/vagas/{vaga_id}/status", headers=headers, json={"status": "cancelada"})
    print(" ", r.status_code)
    assert r.status_code == 422

    print("\n== Criando vaga com convenio de OUTRA empresa (esperado 422) ==")
    outra_empresa = empresas[1]
    convenios_outra = requests.get(BASE + f"/admin/empresas/{outra_empresa['id']}/convenios", headers=headers).json()
    if convenios_outra:
        r = requests.post(
            BASE + f"/admin/empresas/{empresa['id']}/vagas",
            headers=headers,
            json={"titulo": "Vaga invalida", "convenio_id": convenios_outra[0]["id"]},
        )
        print(" ", r.status_code, r.json())
        assert r.status_code == 422

    print("\n== empresa_tem_vaga_ativa (helper interno) ==")
    from app.core.database import SessionLocal
    from app.routers.vagas import empresa_tem_vaga_ativa

    db = SessionLocal()
    tem_ativa = empresa_tem_vaga_ativa(db, empresa["id"])
    db.close()
    print(" empresa tem vaga ativa?", tem_ativa, "(esperado False, pois encerramos a única vaga)")
    assert tem_ativa is False

    print("\n== DELETE /admin/vagas/{id} ==")
    r = requests.delete(BASE + f"/admin/vagas/{vaga_id}", headers=headers)
    print(" ", r.status_code)
    assert r.status_code == 204

    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    main()
