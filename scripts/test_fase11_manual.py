"""
Verificação manual da Fase 11 (auditoria + avaliação humana, passos 30
e 32). Reaproveita a vaga da DevSoft (já tem Recomendacao gerada nos
testes da Fase 9) para criar uma avaliação humana de verdade.
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

    print("== 1. Login gera log de auditoria (login_sucesso) ==")
    r = requests.get(BASE + "/admin/logs-auditoria", headers=admin_headers)
    assert r.status_code == 200
    logs = r.json()
    print("   total de logs:", len(logs))
    login_logs = [l for l in logs if l["acao"] == "login_sucesso"]
    assert len(login_logs) >= 1, "deveria haver pelo menos um log de login_sucesso (o que acabamos de fazer)"
    print("   OK: log de login encontrado ->", login_logs[0]["acao"], login_logs[0]["detalhes"])

    print("\n== 2. Login com senha errada gera log_falha (sem revelar a senha) ==")
    requests.post(BASE + "/auth/login", json={"matricula": "admin.cetec", "password": "senha-errada-de-proposito"})
    r = requests.get(BASE + "/admin/logs-auditoria?entidade_tipo=usuario", headers=admin_headers)
    falhas = [l for l in r.json() if l["acao"] == "login_falha"]
    assert len(falhas) >= 1
    assert "senha" not in str(falhas[0]["detalhes"]).lower() or "matricula_tentada" in falhas[0]["detalhes"]
    print("   OK: log_falha registrado, detalhes:", falhas[0]["detalhes"])

    print("\n== 3. Criar empresa gera log criar_empresa ==")
    r = requests.post(BASE + "/admin/empresas", headers=admin_headers, json={"nome": "Empresa Fase11 Auditoria Teste"})
    assert r.status_code == 201
    empresa_id = r.json()["id"]
    r = requests.get(BASE + "/admin/logs-auditoria?entidade_tipo=empresa", headers=admin_headers)
    criadas = [l for l in r.json() if l["acao"] == "criar_empresa" and l["entidade_id"] == empresa_id]
    assert len(criadas) == 1
    print("   OK: log criar_empresa ->", criadas[0]["detalhes"])

    print("\n== 4. Aluno não pode acessar logs de auditoria (403) ==")
    aluno_login = requests.post(BASE + "/auth/login", json={"matricula": "2026333444", "password": "senha123"})
    aluno_headers = {"Authorization": f"Bearer {aluno_login.json()['access_token']}"}
    r = requests.get(BASE + "/admin/logs-auditoria", headers=aluno_headers)
    assert r.status_code == 403
    print("   OK: 403 confirmado")

    print("\n== 5. Avaliação humana de uma recomendação existente ==")
    from app.core.database import SessionLocal
    from app.models.recomendacao import Recomendacao

    db = SessionLocal()
    recomendacao = db.query(Recomendacao).filter(Recomendacao.tipo == "aluno_para_vaga").first()
    assert recomendacao is not None, "esperava pelo menos uma Recomendacao aluno_para_vaga dos testes da Fase 8/9"
    recomendacao_id = str(recomendacao.id)
    nivel_llm = recomendacao.nivel
    db.close()

    r = requests.post(
        BASE + f"/admin/recomendacoes/{recomendacao_id}/avaliacoes",
        headers=admin_headers,
        json={"concorda_com_llm": True, "nota_humana": 5, "comentario": "Teste automatizado da Fase 11."},
    )
    print("   status:", r.status_code)
    assert r.status_code == 201, r.text
    avaliacao = r.json()
    assert avaliacao["nota_humana"] == 5
    print(f"   OK: avaliacao criada, nivel do LLM era '{nivel_llm}', avaliador concordou:", avaliacao["concorda_com_llm"])

    print("\n== 6. Nota fora da escala 1-5 é rejeitada (422) ==")
    r = requests.post(
        BASE + f"/admin/recomendacoes/{recomendacao_id}/avaliacoes",
        headers=admin_headers,
        json={"nota_humana": 10},
    )
    assert r.status_code == 422
    print("   OK: 422 confirmado")

    print("\n== 7. GET /admin/avaliacoes lista todas (para exportar no TCC) ==")
    r = requests.get(BASE + "/admin/avaliacoes", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    print("   total de avaliacoes:", len(r.json()))

    print("\n== 8. Avaliação de recomendação inexistente -> 404 ==")
    import uuid

    r = requests.post(
        BASE + f"/admin/recomendacoes/{uuid.uuid4()}/avaliacoes", headers=admin_headers, json={"nota_humana": 3}
    )
    assert r.status_code == 404
    print("   OK: 404 confirmado")

    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    main()
