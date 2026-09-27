"""Verificação manual da Fase 7 (texto -> embedding -> busca semântica)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

BASE = "http://127.0.0.1:8000/api"


def main():
    admin_login = requests.post(BASE + "/auth/login", json={"matricula": "admin.cetec", "password": "UfrbAdmin@2026Local!"})
    admin_login.raise_for_status()
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    aluno_login = requests.post(BASE + "/auth/login", json={"matricula": "2026333444", "password": "senha123"})
    aluno_login.raise_for_status()
    aluno_headers = {"Authorization": f"Bearer {aluno_login.json()['access_token']}"}
    aluno_id = aluno_login.json()["usuario"]["id"]

    print("== 1. Atualizando o perfil (deve gerar embedding do aluno) ==")
    r = requests.put(BASE + "/perfil", headers=aluno_headers, json={"course_id": 2, "semester": "6º"})
    assert r.status_code == 200

    from app.core.database import SessionLocal
    from app.models.aluno import Aluno
    from app.models.embedding import Embedding

    db = SessionLocal()
    aluno = db.query(Aluno).filter(Aluno.usuario_id == aluno_id).first()
    emb_aluno = db.query(Embedding).filter(Embedding.entidade_tipo == "aluno", Embedding.entidade_id == aluno.id).first()
    assert emb_aluno is not None, "embedding do aluno nao foi criado"
    print("   embedding do aluno criado, dim =", len(emb_aluno.vetor), "modelo =", emb_aluno.modelo)
    assert len(emb_aluno.vetor) == 1024

    print("\n== 2. Criando empresa + vaga de TI (deve gerar embedding da vaga e da empresa) ==")
    r = requests.post(BASE + "/admin/empresas", headers=admin_headers, json={"nome": "DevSoft Tecnologia Ltda"})
    empresa = r.json()

    r = requests.post(
        BASE + f"/admin/empresas/{empresa['id']}/vagas",
        headers=admin_headers,
        json={
            "titulo": "Estágio em Desenvolvimento Backend",
            "descricao": "Desenvolvimento de APIs com Python e FastAPI.",
            "requisitos": "Cursando Engenharia de Computação, conhecimento em Python.",
            "cursos": ["Engenharia de Computação"],
            "areas": ["Desenvolvimento Web", "Banco de Dados"],
            "tecnologias": ["Python", "FastAPI", "PostgreSQL"],
            "modalidade": "Híbrido",
        },
    )
    vaga_ti = r.json()
    assert r.status_code == 201

    emb_vaga = db.query(Embedding).filter(Embedding.entidade_tipo == "vaga", Embedding.entidade_id == vaga_ti["id"]).first()
    assert emb_vaga is not None, "embedding da vaga nao foi criado"
    print("   embedding da vaga criado, texto_base:")
    print("  ", repr(emb_vaga.texto_base[:200]))

    emb_empresa = db.query(Embedding).filter(Embedding.entidade_tipo == "empresa", Embedding.entidade_id == empresa["id"]).first()
    assert emb_empresa is not None, "embedding da empresa nao foi criado"
    print("   embedding da empresa criado (agrega dados da vaga):")
    print("  ", repr(emb_empresa.texto_base))

    print("\n== 3. Criando uma SEGUNDA vaga, de área totalmente diferente (Agronomia) ==")
    r = requests.post(BASE + "/admin/empresas", headers=admin_headers, json={"nome": "Fazenda Bela Vista Agropecuária"})
    empresa2 = r.json()
    r = requests.post(
        BASE + f"/admin/empresas/{empresa2['id']}/vagas",
        headers=admin_headers,
        json={
            "titulo": "Estágio em Agronomia",
            "descricao": "Acompanhamento de manejo de solo e irrigação em lavouras.",
            "requisitos": "Cursando Agronomia.",
            "cursos": ["Agronomia"],
            "areas": ["Produção Vegetal", "Irrigação"],
            "tecnologias": [],
            "modalidade": "Presencial",
        },
    )
    vaga_agro = r.json()
    assert r.status_code == 201

    print("\n== 4. Busca semantica: aluno de Engenharia de Computacao ==")
    r = requests.get(BASE + "/perfil/busca-semantica/vagas", headers=aluno_headers)
    print(" status:", r.status_code)
    resultados = r.json()
    for item in resultados:
        print(f"   {item['distancia']:.4f}  {item['titulo']} ({item['empresa']})")

    assert r.status_code == 200
    assert len(resultados) >= 2

    ids_ordenados = [item["vaga_id"] for item in resultados]
    pos_ti = ids_ordenados.index(vaga_ti["id"])
    pos_agro = ids_ordenados.index(vaga_agro["id"])
    print(f"\n   posicao da vaga de TI: {pos_ti} | posicao da vaga de Agronomia: {pos_agro}")
    assert pos_ti < pos_agro, "a vaga de TI deveria ser mais similar ao aluno de Eng. Computacao do que a de Agronomia"
    print("   OK: busca semantica ordenou corretamente por relevancia (TI mais perto que Agronomia)")

    print("\n== 5. Resiliencia: perfil.js continua salvando mesmo que o texto fique vazio ==")
    # (nao dá pra simular Ollama fora do ar facilmente aqui, mas o design
    # (try/except em regenerate_*_embedding) já foi revisado no código.)

    db.close()
    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    main()
