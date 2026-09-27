"""
Verificação manual da Fase 9 (prospecção + caminho inverso). Reaproveita
o aluno e as vagas (DevSoft = TI, Fazenda Bela Vista = Agronomia) já
criados nos testes das Fases 7/8.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

BASE = "http://127.0.0.1:8000/api"


def main():
    admin_login = requests.post(BASE + "/auth/login", json={"matricula": "admin.cetec", "password": "UfrbAdmin@2026Local!"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    aluno_login = requests.post(BASE + "/auth/login", json={"matricula": "2026333444", "password": "senha123"})
    aluno_headers = {"Authorization": f"Bearer {aluno_login.json()['access_token']}"}
    aluno_usuario_id = aluno_login.json()["usuario"]["id"]

    from app.core.database import SessionLocal
    from app.models.aluno import Aluno
    from app.models.empresa import Empresa
    from app.models.vaga import Vaga
    from app.routers.vagas import empresa_tem_vaga_ativa

    db = SessionLocal()
    aluno = db.query(Aluno).filter(Aluno.usuario_id == aluno_usuario_id).first()
    devsoft = db.query(Empresa).filter(Empresa.nome_normalizado.like("DEVSOFT%")).first()
    devsoft_vaga = db.query(Vaga).filter(Vaga.empresa_id == devsoft.id).first()
    print("== Contexto ==")
    print("   aluno:", aluno.matricula, "curso:", aluno.curso.nome if aluno.curso else None)
    print("   DevSoft tem vaga ativa?", empresa_tem_vaga_ativa(db, devsoft.id))

    print("\n== 1. Caminho inverso: admin busca alunos compativeis com a vaga da DevSoft ==")
    r = requests.post(BASE + f"/admin/vagas/{devsoft_vaga.id}/recomendacoes/gerar", headers=admin_headers, timeout=300)
    print("   status:", r.status_code)
    resultados = r.json()
    assert r.status_code == 200
    assert len(resultados) >= 1, "esperava pelo menos o aluno de Eng. Computacao como compativel"
    encontrado = next((x for x in resultados if x["aluno"]["matricula"] == "2026333444"), None)
    assert encontrado is not None, "aluno de Eng. Computacao deveria aparecer como compativel com a vaga da DevSoft"
    print("   OK: aluno encontrado ->", encontrado["aluno"]["nome_completo"], "| nivel:", encontrado["nivel"], "| tipo:", encontrado["tipo"])
    assert encontrado["tipo"] == "vaga_para_aluno"

    print("\n== 2. Aluno tentando acessar rota de admin do caminho inverso (esperado 403) ==")
    r = requests.post(BASE + f"/admin/vagas/{devsoft_vaga.id}/recomendacoes/gerar", headers=aluno_headers)
    print("   status:", r.status_code)
    assert r.status_code == 403

    print("\n== 3. Prospecção: empresa com vaga ativa NUNCA deve aparecer como prospecção ==")
    r = requests.post(BASE + "/perfil/recomendacoes/gerar", headers=aluno_headers, timeout=600)
    print("   status:", r.status_code)
    combinadas = r.json()
    assert r.status_code == 200
    tipos = {c["tipo"] for c in combinadas}
    print("   tipos retornados:", tipos)

    prospeccoes = [c for c in combinadas if c["tipo"] == "aluno_para_empresa"]
    for p in prospeccoes:
        assert p["vaga"] is None, "prospecção nunca deve ter vaga associada"
    nomes_prospeccao = [p["empresa"]["nome"] for p in prospeccoes]
    print("   empresas em prospecção:", nomes_prospeccao)
    assert devsoft.nome not in nomes_prospeccao, "DevSoft tem vaga ativa - nao pode aparecer como prospecção"
    print("   OK: nenhuma empresa com vaga ativa apareceu como prospecção")

    recomendacoes_vaga = [c for c in combinadas if c["tipo"] == "aluno_para_vaga"]
    print("   recomendacoes de vaga:", [(r["vaga"]["titulo"], r["nivel"]) for r in recomendacoes_vaga])
    assert len(recomendacoes_vaga) >= 1

    print("\n== 4. GET /perfil/recomendacoes (lista combinada, igual ao que a pagina vai consumir) ==")
    r = requests.get(BASE + "/perfil/recomendacoes", headers=aluno_headers)
    print("   total:", len(r.json()))
    assert r.status_code == 200

    db.close()
    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    main()
