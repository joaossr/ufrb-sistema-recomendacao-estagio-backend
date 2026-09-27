"""
CRUD de perfil/tecnologias/projetos/experiências/áreas de interesse
(Fase 3) — e o teste mais importante desta suíte para a Fase 3: que
um aluno NUNCA enxerga nem consegue alterar o dado de outro (isolamento
por conta), já que cada endpoint depende de `get_current_aluno`
resolvido a partir do próprio JWT, nunca de um id vindo do corpo/URL.
"""


def test_get_perfil_retorna_dados_do_proprio_aluno(client, aluno_a, mock_ollama):
    resp = client.get("/api/perfil", headers=aluno_a["headers"])
    assert resp.status_code == 200
    assert resp.json()["registration_number"] == aluno_a["usuario"]["matricula"]


def test_put_perfil_atualiza_campos_parcialmente(client, aluno_a, curso_ti, mock_ollama):
    resp = client.put(
        "/api/perfil",
        headers=aluno_a["headers"],
        json={"course_id": curso_ti.id, "full_name": "Fulano de Tal", "semester": "5"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Fulano de Tal"
    assert data["course"] == "Engenharia de Computação"
    assert data["semester"] == "5"


def test_put_perfil_com_tcc_cria_registro_de_tcc(client, aluno_a, mock_ollama):
    resp = client.put(
        "/api/perfil",
        headers=aluno_a["headers"],
        json={"tcc_status": "em_andamento", "tcc_title": "Sistema de Recomendação"},
    )
    assert resp.status_code == 200
    assert resp.json()["tcc_status"] == "em_andamento"
    assert resp.json()["tcc_title"] == "Sistema de Recomendação"


def test_tecnologia_crud_completo(client, aluno_a, mock_ollama):
    resp = client.post("/api/perfil/tecnologias", headers=aluno_a["headers"], json={"name": "Python", "level": "Avançado"})
    assert resp.status_code == 201
    vinculo_id = resp.json()["id"]

    resp = client.get("/api/perfil/tecnologias", headers=aluno_a["headers"])
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Python"

    resp = client.put(f"/api/perfil/tecnologias/{vinculo_id}", headers=aluno_a["headers"], json={"level": "Básico"})
    assert resp.status_code == 200
    assert resp.json()["level"] == "Básico"

    resp = client.delete(f"/api/perfil/tecnologias/{vinculo_id}", headers=aluno_a["headers"])
    assert resp.status_code == 204
    assert client.get("/api/perfil/tecnologias", headers=aluno_a["headers"]).json() == []


def test_tecnologia_e_reaproveitada_do_catalogo_entre_alunos_diferentes(client, aluno_a, aluno_b, mock_ollama):
    """Duas contas cadastrando a "mesma" tecnologia não devem criar
    duas linhas no catálogo (case-insensitive)."""
    client.post("/api/perfil/tecnologias", headers=aluno_a["headers"], json={"name": "python", "level": "Básico"})
    client.post("/api/perfil/tecnologias", headers=aluno_b["headers"], json={"name": "Python", "level": "Avançado"})

    resp = client.get("/api/tecnologias")
    nomes = [t["nome"] for t in resp.json()]
    assert nomes.count("python") + nomes.count("Python") == 1


def test_projeto_crud_completo(client, aluno_a, mock_ollama):
    payload = {
        "name": "Sistema de Recomendação",
        "description": "TCC",
        "technologies": ["Python", "FastAPI"],
    }
    resp = client.post("/api/perfil/projetos", headers=aluno_a["headers"], json=payload)
    assert resp.status_code == 201
    projeto_id = resp.json()["id"]
    assert set(resp.json()["technologies"]) == {"Python", "FastAPI"}

    resp = client.put(
        f"/api/perfil/projetos/{projeto_id}",
        headers=aluno_a["headers"],
        json={"name": "Novo nome", "description": "Atualizado", "technologies": ["Python"]},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Novo nome"
    assert resp.json()["technologies"] == ["Python"]

    resp = client.delete(f"/api/perfil/projetos/{projeto_id}", headers=aluno_a["headers"])
    assert resp.status_code == 204
    assert client.get("/api/perfil/projetos", headers=aluno_a["headers"]).json() == []


def test_experiencia_crud_completo(client, aluno_a, mock_ollama):
    payload = {"company": "DevSoft", "role": "Estagiário", "technologies": ["SQL"]}
    resp = client.post("/api/perfil/experiencias", headers=aluno_a["headers"], json=payload)
    assert resp.status_code == 201
    exp_id = resp.json()["id"]

    resp = client.delete(f"/api/perfil/experiencias/{exp_id}", headers=aluno_a["headers"])
    assert resp.status_code == 204
    assert client.get("/api/perfil/experiencias", headers=aluno_a["headers"]).json() == []


def test_areas_interesse_selecao_completa(client, aluno_a, mock_ollama):
    resp = client.put("/api/perfil/areas-interesse", headers=aluno_a["headers"], json={"areas": ["Inteligência Artificial", "Redes"]})
    assert resp.status_code == 200
    assert set(resp.json()) == {"Inteligência Artificial", "Redes"}

    resp = client.get("/api/perfil/areas-interesse", headers=aluno_a["headers"])
    assert set(resp.json()) == {"Inteligência Artificial", "Redes"}


# ---------------------------------------------------------------------
# Isolamento entre contas — a parte mais importante deste arquivo.
# ---------------------------------------------------------------------


def test_aluno_nao_ve_tecnologia_de_outro_aluno(client, aluno_a, aluno_b, mock_ollama):
    client.post("/api/perfil/tecnologias", headers=aluno_a["headers"], json={"name": "Java", "level": "Básico"})
    resp = client.get("/api/perfil/tecnologias", headers=aluno_b["headers"])
    assert resp.json() == []


def test_aluno_nao_consegue_editar_tecnologia_de_outro_aluno(client, aluno_a, aluno_b, mock_ollama):
    resp = client.post("/api/perfil/tecnologias", headers=aluno_a["headers"], json={"name": "Java", "level": "Básico"})
    vinculo_id = resp.json()["id"]

    resp = client.put(f"/api/perfil/tecnologias/{vinculo_id}", headers=aluno_b["headers"], json={"level": "Avançado"})
    assert resp.status_code == 404  # nunca 403 revelando que existe — simplesmente não encontra


def test_aluno_nao_consegue_excluir_projeto_de_outro_aluno(client, aluno_a, aluno_b, mock_ollama):
    resp = client.post(
        "/api/perfil/projetos", headers=aluno_a["headers"], json={"name": "Projeto A", "description": "", "technologies": []}
    )
    projeto_id = resp.json()["id"]

    resp = client.delete(f"/api/perfil/projetos/{projeto_id}", headers=aluno_b["headers"])
    assert resp.status_code == 404

    # confirma que o projeto de A continua intacto
    resp = client.get("/api/perfil/projetos", headers=aluno_a["headers"])
    assert len(resp.json()) == 1


def test_perfil_de_um_aluno_nao_vaza_para_o_outro(client, aluno_a, aluno_b, mock_ollama):
    client.put("/api/perfil", headers=aluno_a["headers"], json={"full_name": "Nome do Aluno A"})
    resp = client.get("/api/perfil", headers=aluno_b["headers"])
    assert resp.json()["full_name"] == ""


def test_admin_nao_tem_perfil_de_aluno(client, admin_headers):
    resp = client.get("/api/perfil", headers=admin_headers)
    assert resp.status_code == 404
