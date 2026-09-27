"""
Verificação manual da Fase 10 (passo 27 e 28): painel admin enxerga
alunos reais via /admin/alunos, e os novos catálogos públicos de
autocomplete (/tecnologias, /areas-projeto, /tipos-projeto) respondem.
Reaproveita o aluno "Joana Teste Silva" (matricula 2026333444) já
criado nos testes das Fases 3/7/8/9.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

BASE = "http://127.0.0.1:8000/api"


def main():
    admin_login = requests.post(BASE + "/auth/login", json={"matricula": "admin.cetec", "password": "UfrbAdmin@2026Local!"})
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    aluno_login = requests.post(BASE + "/auth/login", json={"matricula": "2026333444", "password": "senha123"})
    assert aluno_login.status_code == 200, aluno_login.text
    aluno_headers = {"Authorization": f"Bearer {aluno_login.json()['access_token']}"}

    print("== 1. GET /admin/alunos (lista) ==")
    r = requests.get(BASE + "/admin/alunos", headers=admin_headers)
    print("   status:", r.status_code)
    assert r.status_code == 200
    alunos = r.json()
    print("   total de alunos:", len(alunos))
    assert len(alunos) >= 1
    joana = next((a for a in alunos if a["matricula"] == "2026333444"), None)
    assert joana is not None, "Joana Teste Silva deveria aparecer na lista real de alunos"
    print("   OK: encontrada ->", joana["nome_completo"], "| curso:", joana["curso"], "| tem_embedding:", joana["tem_embedding"])
    assert joana["num_tecnologias"] >= 0
    assert joana["tem_embedding"] is True, "Joana deveria ter embedding gerado nos testes da Fase 7"

    print("\n== 2. GET /admin/alunos/{id} (detalhe) ==")
    r = requests.get(BASE + f"/admin/alunos/{joana['id']}", headers=admin_headers)
    print("   status:", r.status_code)
    assert r.status_code == 200
    detalhe = r.json()
    assert detalhe["perfil"]["registration_number"] == "2026333444"
    print("   OK: perfil:", detalhe["perfil"]["full_name"])
    print("   tecnologias:", [t.get("name") or t.get("nome") for t in detalhe["tecnologias"]])
    print("   projetos:", [p.get("name") or p.get("nome") for p in detalhe["projetos"]])
    print("   experiencias:", [e.get("company") or e.get("empresa") for e in detalhe["experiencias"]])
    print("   areas_interesse:", detalhe["areas_interesse"])

    print("\n== 3. Aluno tentando acessar rota de admin (esperado 403) ==")
    r = requests.get(BASE + "/admin/alunos", headers=aluno_headers)
    print("   status:", r.status_code)
    assert r.status_code == 403

    r = requests.get(BASE + f"/admin/alunos/{joana['id']}", headers=aluno_headers)
    print("   status:", r.status_code)
    assert r.status_code == 403

    print("\n== 4. GET /admin/alunos/{id} com id inexistente (esperado 404) ==")
    import uuid

    r = requests.get(BASE + f"/admin/alunos/{uuid.uuid4()}", headers=admin_headers)
    print("   status:", r.status_code)
    assert r.status_code == 404

    print("\n== 5. Catálogos públicos (sem auth) para autocomplete ==")
    r = requests.get(BASE + "/tecnologias")
    print("   /tecnologias status:", r.status_code, "| total:", len(r.json()))
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert all("id" in t and "nome" in t for t in r.json())

    r = requests.get(BASE + "/areas-projeto")
    print("   /areas-projeto status:", r.status_code, "| total:", len(r.json()))
    assert r.status_code == 200

    r = requests.get(BASE + "/tipos-projeto")
    print("   /tipos-projeto status:", r.status_code, "| total:", len(r.json()))
    assert r.status_code == 200

    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    main()
