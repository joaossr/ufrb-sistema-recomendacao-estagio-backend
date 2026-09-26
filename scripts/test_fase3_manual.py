"""
Script de verificação manual da Fase 3 (não é a suíte pytest da Fase
11 — só um roteiro rápido cobrindo perfil/tecnologias/projetos/
experiências/áreas de interesse ponta a ponta contra o servidor local).
"""

import requests

BASE = "http://127.0.0.1:8000/api"


def main():
    login = requests.post(BASE + "/auth/login", json={"matricula": "2026111222", "password": "senha123"})
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Idempotência: roda o script várias vezes sem acumular lixo de runs anteriores.
    for projeto in requests.get(BASE + "/perfil/projetos", headers=headers).json():
        requests.delete(BASE + f"/perfil/projetos/{projeto['id']}", headers=headers)
    for exp in requests.get(BASE + "/perfil/experiencias", headers=headers).json():
        requests.delete(BASE + f"/perfil/experiencias/{exp['id']}", headers=headers)

    print("== PUT /perfil (curso, semestre, previsão) ==")
    r = requests.put(
        BASE + "/perfil",
        headers=headers,
        json={"course_id": 2, "semester": "5º", "expected_graduation": "2028", "linkedin_url": "https://linkedin.com/in/joana"},
    )
    print(r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["course"] == "Engenharia de Computação"

    print("\n== GET /perfil (curso deve refletir o join com cursos.nome) ==")
    r = requests.get(BASE + "/perfil", headers=headers)
    print(r.status_code, r.json())

    print("\n== POST /perfil/projetos ==")
    r = requests.post(
        BASE + "/perfil/projetos",
        headers=headers,
        json={
            "name": "Sistema de Recomendação de Estágio",
            "description": "TCC — recomendador com pgvector + Qwen3.",
            "academic_center": "CETEC",
            "course": "Engenharia de Computação",
            "area": "Inteligência Artificial",
            "type": "TCC",
            "technologies": ["Python", "FastAPI", "PostgreSQL"],
            "link": "https://github.com/joaossr/ufrb-sistema-recomendacao-estagio",
        },
    )
    print(r.status_code, r.json())
    assert r.status_code == 201
    projeto_id = r.json()["id"]

    print("\n== GET /perfil/projetos ==")
    r = requests.get(BASE + "/perfil/projetos", headers=headers)
    print(r.status_code, r.json())
    assert len(r.json()) == 1

    print("\n== DELETE /perfil/projetos/{id} ==")
    r = requests.delete(BASE + f"/perfil/projetos/{projeto_id}", headers=headers)
    print(r.status_code)
    assert r.status_code == 204

    print("\n== POST /perfil/experiencias ==")
    r = requests.post(
        BASE + "/perfil/experiencias",
        headers=headers,
        json={
            "company": "NIT/UFRB",
            "role": "Bolsista de Iniciação Científica",
            "work_area": "Pesquisa e Desenvolvimento",
            "start_date": "2025-03-01",
            "is_current": True,
            "description": "Apoio em projetos de pesquisa aplicada.",
            "technologies": ["Python"],
        },
    )
    print(r.status_code, r.json())
    assert r.status_code == 201

    print("\n== GET /areas-interesse (catálogo, deve ter 73+) ==")
    r = requests.get(BASE + "/areas-interesse")
    print(r.status_code, "total:", len(r.json()), r.json()[:3])
    assert len(r.json()) >= 73

    print("\n== PUT /perfil/areas-interesse ==")
    r = requests.put(
        BASE + "/perfil/areas-interesse", headers=headers, json={"areas": ["Inteligência Artificial", "Ciência de Dados", "Área Nova de Teste"]}
    )
    print(r.status_code, r.json())
    assert r.status_code == 200
    assert "Área Nova de Teste" in r.json()

    print("\n== GET /cursos e /centros ==")
    r = requests.get(BASE + "/cursos")
    print("cursos:", len(r.json()))
    r = requests.get(BASE + "/centros")
    print("centros:", r.json())

    print("\n== Tecnologias: limpar + POST + PUT (nível) + DELETE ==")
    for tec in requests.get(BASE + "/perfil/tecnologias", headers=headers).json():
        requests.delete(BASE + f"/perfil/tecnologias/{tec['id']}", headers=headers)
    r = requests.post(BASE + "/perfil/tecnologias", headers=headers, json={"name": "Python", "level": "Básico"})
    print("POST", r.status_code, r.json())
    tec_id = r.json()["id"]
    r = requests.put(BASE + f"/perfil/tecnologias/{tec_id}", headers=headers, json={"level": "Avançado"})
    print("PUT", r.status_code, r.json())
    assert r.json()["level"] == "Avançado"
    r = requests.get(BASE + "/perfil/tecnologias", headers=headers)
    print("GET", r.status_code, r.json())
    assert len(r.json()) == 1
    r = requests.delete(BASE + f"/perfil/tecnologias/{tec_id}", headers=headers)
    print("DELETE", r.status_code)
    assert r.status_code == 204
    r = requests.get(BASE + "/perfil/tecnologias", headers=headers)
    assert r.json() == []

    print("\n== GET /perfil final (visão consolidada) ==")
    r = requests.get(BASE + "/perfil", headers=headers)
    print(r.status_code, r.json())

    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    main()
