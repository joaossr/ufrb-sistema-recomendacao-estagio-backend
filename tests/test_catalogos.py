"""
Catálogos públicos de autocomplete (Fase 3 / Fase 10 / passo 28) —
nenhum exige autenticação, todos retornam lista vazia (não erro)
quando o catálogo ainda não tem nenhum item.
"""

import pytest

ENDPOINTS_PUBLICOS = ["/api/centros", "/api/cursos", "/api/areas-interesse", "/api/tecnologias", "/api/areas-projeto", "/api/tipos-projeto"]


@pytest.mark.parametrize("endpoint", ENDPOINTS_PUBLICOS)
def test_endpoint_publico_nao_exige_autenticacao(client, endpoint):
    resp = client.get(endpoint)
    assert resp.status_code == 200
    assert resp.json() == []


def test_centro_e_curso_aparecem_apos_seed(client, curso_ti):
    assert [c["nome"] for c in client.get("/api/centros").json()] == ["Centro de Ciências Exatas e Tecnológicas"]
    assert [c["nome"] for c in client.get("/api/cursos").json()] == ["Engenharia de Computação"]


def test_criar_area_interesse_e_idempotente_por_nome(client):
    resp1 = client.post("/api/areas-interesse", json={"nome": "Inteligência Artificial"})
    assert resp1.status_code == 201
    resp2 = client.post("/api/areas-interesse", json={"nome": "inteligência artificial"})
    assert resp2.status_code == 201
    assert resp1.json()["id"] == resp2.json()["id"]
    assert len(client.get("/api/areas-interesse").json()) == 1
