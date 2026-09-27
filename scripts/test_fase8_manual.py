"""
Verificação manual da Fase 8 (regras objetivas + análise com Qwen3 +
recomendação auditável). Usa as vagas já criadas no teste da Fase 7
(uma de TI compatível com o curso do aluno, uma de Agronomia
incompatível) para provar que a regra de curso filtra corretamente
ANTES de qualquer chamada ao LLM — mantém o teste rápido (só 1
chamada ao Qwen3, que leva dezenas de segundos nesta máquina).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

BASE = "http://127.0.0.1:8000/api"


def main():
    aluno_login = requests.post(BASE + "/auth/login", json={"matricula": "2026333444", "password": "senha123"})
    aluno_login.raise_for_status()
    headers = {"Authorization": f"Bearer {aluno_login.json()['access_token']}"}

    from app.core.database import SessionLocal
    from app.models.aluno import Aluno
    from app.services.embeddings.search import buscar_vagas_similares_ao_aluno
    from app.services.recomendacao.regras import filtrar_candidatos_elegiveis

    db = SessionLocal()
    aluno = db.query(Aluno).filter(Aluno.usuario_id == aluno_login.json()["usuario"]["id"]).first()

    print("== 1. Regras objetivas: busca vetorial traz 2 vagas, mas so 1 e elegivel (curso) ==")
    candidatos = buscar_vagas_similares_ao_aluno(db, aluno.id)
    print("   candidatos da busca vetorial:", len(candidatos))
    elegiveis = filtrar_candidatos_elegiveis(db, aluno, candidatos)
    print("   elegiveis apos regras objetivas:", len(elegiveis), "->", [c.vaga.titulo for c in elegiveis])
    assert len(elegiveis) == 1, "esperava so a vaga de TI elegivel (curso bate); Agronomia deveria ser filtrada"
    assert elegiveis[0].vaga.titulo == "Estágio em Desenvolvimento Backend"
    print("   OK: vaga de Agronomia corretamente excluida por incompatibilidade de curso")
    db.close()

    print("\n== 2. POST /perfil/recomendacoes/gerar (Qwen3 em CPU nesta maquina: pode levar varios minutos) ==")
    r = requests.post(BASE + "/perfil/recomendacoes/gerar", headers=headers, timeout=650)
    print("   status:", r.status_code)
    recomendacoes = r.json()
    assert r.status_code == 200
    assert len(recomendacoes) == 1, f"esperava 1 recomendacao, veio {len(recomendacoes)}"

    rec = recomendacoes[0]
    print("   nivel:", rec["nivel"])
    print("   indice_compatibilidade:", rec["indice_compatibilidade"])
    print("   similaridade:", rec["similaridade"])
    print("   pontos_compativeis:", rec["pontos_compativeis"])
    print("   pontos_parciais:", rec["pontos_parciais"])
    print("   lacunas:", rec["lacunas"])
    print("   justificativa:", rec["justificativa"][:300])
    print("   modelo_llm:", rec["modelo_llm"], "| modelo_embedding:", rec["modelo_embedding"])

    assert rec["nivel"] in ("alta", "media", "baixa")
    assert 0 <= rec["indice_compatibilidade"] <= 100
    assert rec["tipo"] == "aluno_para_vaga"
    assert rec["justificativa"]

    print("\n== 3. GET /perfil/recomendacoes (lista as recomendacoes salvas) ==")
    r = requests.get(BASE + "/perfil/recomendacoes", headers=headers)
    print("   total:", len(r.json()))
    assert len(r.json()) == 1

    print("\n== 4. Rodar de novo: deve ATUALIZAR a mesma recomendacao, nao duplicar ==")
    r = requests.post(BASE + "/perfil/recomendacoes/gerar", headers=headers, timeout=650)
    r2 = requests.get(BASE + "/perfil/recomendacoes", headers=headers)
    print("   total apos rodar de novo:", len(r2.json()))
    assert len(r2.json()) == 1, "nao deveria duplicar a recomendacao para a mesma vaga"

    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    main()
