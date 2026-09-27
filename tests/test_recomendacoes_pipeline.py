"""
Pipeline completo de recomendação (Fase 8/9), disparado em lote pelo
admin para TODOS os alunos de uma vez (Fase 12 — o aluno não gera mais
a própria recomendação, só visualiza o que já foi gerado). `mock_ollama`
faz todo aluno/vaga/empresa terem o MESMO vetor fixo — suficiente para
testar a ORQUESTRAÇÃO (quem aparece, quem é filtrado, quem vira
prospecção, e principalmente o isolamento entre alunos), não a
qualidade semântica da busca em si (isso já foi validado manualmente
contra o Ollama real, ver scripts/test_fase7_manual.py).
"""


def _preparar_aluno_com_curso(client, aluno, curso_ti, mock_ollama):
    client.put("/api/perfil", headers=aluno["headers"], json={"course_id": curso_ti.id})
    client.post("/api/perfil/tecnologias", headers=aluno["headers"], json={"name": "Python", "level": "Avançado"})


def _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama, nome_empresa="DevSoft", curso_exigido=None):
    empresa_id = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": nome_empresa}).json()["id"]
    payload = {"titulo": "Estágio Backend"}
    if curso_exigido:
        payload["cursos"] = [curso_exigido]
    vaga_id = client.post(f"/api/admin/empresas/{empresa_id}/vagas", headers=admin_headers, json=payload).json()["id"]
    return empresa_id, vaga_id


def _criar_empresa_sem_vaga(client, admin_headers, mock_ollama, nome_empresa="Empresa Prospeccao"):
    resp = client.post("/api/admin/empresas", headers=admin_headers, json={"nome": nome_empresa})
    empresa_id = resp.json()["id"]
    # empresa só existe no índice vetorial se tiver embedding próprio —
    # criado ao registrar a empresa (regenerate_empresa_embedding).
    return empresa_id


def _gerar_para_todos(client, admin_headers):
    resp = client.post("/api/admin/recomendacoes/gerar", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_gerar_para_todos_exige_admin(client, aluno_a):
    resp = client.post("/api/admin/recomendacoes/gerar", headers=aluno_a["headers"])
    assert resp.status_code == 403


def test_aluno_nao_tem_mais_rota_propria_para_gerar(client, aluno_a):
    """Requisito central da Fase 12: o estudante nunca dispara a
    geração — a rota antiga nem existe mais."""
    resp = client.post("/api/perfil/recomendacoes/gerar", headers=aluno_a["headers"])
    assert resp.status_code == 404


def test_gerar_para_todos_retorna_resumo_por_aluno(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama, curso_exigido="Engenharia de Computação")

    resumo = _gerar_para_todos(client, admin_headers)
    assert resumo["alunos_processados"] >= 1
    assert resumo["alunos_com_erro"] == 0
    detalhe = next(d for d in resumo["detalhes"] if d["matricula"] == aluno_a["usuario"]["matricula"])
    assert detalhe["recomendacoes_geradas"] >= 1
    assert detalhe["erro"] is None


def test_gerar_para_todos_retorna_vaga_compativel_com_nivel_do_mock(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama, curso_exigido="Engenharia de Computação")

    _gerar_para_todos(client, admin_headers)

    resultados = client.get("/api/perfil/recomendacoes", headers=aluno_a["headers"]).json()
    assert len(resultados) >= 1
    rec = next(r for r in resultados if r["tipo"] == "aluno_para_vaga")
    assert rec["nivel"] == "alta"  # valor fixo do mock_ollama
    assert rec["indice_compatibilidade"] == 88


def test_vaga_com_curso_incompativel_nunca_aparece(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama, curso_exigido="Agronomia")

    _gerar_para_todos(client, admin_headers)

    resultados = client.get("/api/perfil/recomendacoes", headers=aluno_a["headers"]).json()
    recomendacoes_de_vaga = [r for r in resultados if r["tipo"] == "aluno_para_vaga"]
    assert recomendacoes_de_vaga == []


def test_vaga_encerrada_nunca_aparece(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    """Ao encerrar a vaga, a empresa fica sem vaga ativa — ela pode
    reaparecer como prospecção (Fase 9), mas nunca mais como
    recomendação de vaga concreta (Fase 8)."""
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    _, vaga_id = _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama)
    client.put(f"/api/admin/vagas/{vaga_id}/status", headers=admin_headers, json={"status": "encerrada"})

    _gerar_para_todos(client, admin_headers)

    resultados = client.get("/api/perfil/recomendacoes", headers=aluno_a["headers"]).json()
    recomendacoes_de_vaga = [r for r in resultados if r["tipo"] == "aluno_para_vaga"]
    assert recomendacoes_de_vaga == []


def test_empresa_sem_vaga_ativa_aparece_como_prospeccao(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    _criar_empresa_sem_vaga(client, admin_headers, mock_ollama)

    _gerar_para_todos(client, admin_headers)

    resultados = client.get("/api/perfil/recomendacoes", headers=aluno_a["headers"]).json()
    prospeccoes = [r for r in resultados if r["tipo"] == "aluno_para_empresa"]
    assert len(prospeccoes) == 1
    assert prospeccoes[0]["vaga"] is None


def test_empresa_com_vaga_ativa_nunca_aparece_como_prospeccao(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    """Regra central da Fase 9: quem já tem vaga concreta não pode
    também ser oferecido como 'prospecção' — isso duplicaria e
    confundiria a UI (a mesma empresa em dois lugares)."""
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama, nome_empresa="Empresa Com Vaga", curso_exigido="Engenharia de Computação")

    _gerar_para_todos(client, admin_headers)

    resultados = client.get("/api/perfil/recomendacoes", headers=aluno_a["headers"]).json()
    empresas_em_prospeccao = [r["empresa"]["nome"] for r in resultados if r["tipo"] == "aluno_para_empresa"]
    assert "Empresa Com Vaga" not in empresas_em_prospeccao


def test_listar_recomendacoes_ja_geradas(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama, curso_exigido="Engenharia de Computação")
    _gerar_para_todos(client, admin_headers)

    resp = client.get("/api/perfil/recomendacoes", headers=aluno_a["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_geracao_em_lote_isola_recomendacoes_entre_alunos(client, aluno_a, aluno_b, admin_headers, curso_ti, mock_ollama):
    """O requisito mais importante da Fase 12: processar TODOS os
    alunos de uma vez não pode vazar a recomendação de um para o
    outro — só aluno_a tem o curso exigido pela vaga, então só ele
    pode receber a recomendação de vaga."""
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    # aluno_b existe mas nunca teve o curso/perfil preenchido — não
    # deveria conseguir aparecer em nenhuma recomendação de vaga.
    _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama, curso_exigido="Engenharia de Computação")

    resumo = _gerar_para_todos(client, admin_headers)
    detalhe_b = next(d for d in resumo["detalhes"] if d["matricula"] == aluno_b["usuario"]["matricula"])
    assert detalhe_b["recomendacoes_geradas"] == 0

    resultados_a = client.get("/api/perfil/recomendacoes", headers=aluno_a["headers"]).json()
    resultados_b = client.get("/api/perfil/recomendacoes", headers=aluno_b["headers"]).json()
    assert any(r["tipo"] == "aluno_para_vaga" for r in resultados_a)
    assert resultados_b == []


def test_caminho_inverso_admin_encontra_aluno_compativel_com_vaga(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    _, vaga_id = _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama, curso_exigido="Engenharia de Computação")

    resp = client.post(f"/api/admin/vagas/{vaga_id}/recomendacoes/gerar", headers=admin_headers)
    assert resp.status_code == 200
    resultados = resp.json()
    assert len(resultados) == 1
    assert resultados[0]["tipo"] == "vaga_para_aluno"
    assert resultados[0]["aluno"]["matricula"] == aluno_a["usuario"]["matricula"]


def test_aluno_nao_acessa_rota_de_caminho_inverso(client, aluno_a, admin_headers, mock_ollama):
    empresa_id, vaga_id = _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama)
    resp = client.post(f"/api/admin/vagas/{vaga_id}/recomendacoes/gerar", headers=aluno_a["headers"])
    assert resp.status_code == 403


def test_caminho_inverso_empresa_encontra_aluno_compativel(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    empresa_id = _criar_empresa_sem_vaga(client, admin_headers, mock_ollama)

    resp = client.post(f"/api/admin/empresas/{empresa_id}/recomendacoes/gerar", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["tipo"] == "empresa_para_aluno"


def test_recomendacao_e_avaliavel_por_um_admin(client, aluno_a, admin_headers, curso_ti, mock_ollama):
    """Fecha o laço com a Fase 11 (passo 32): uma Recomendacao gerada
    pelo pipeline pode receber uma avaliação humana."""
    _preparar_aluno_com_curso(client, aluno_a, curso_ti, mock_ollama)
    _criar_empresa_com_vaga_ativa(client, admin_headers, mock_ollama, curso_exigido="Engenharia de Computação")
    _gerar_para_todos(client, admin_headers)

    recomendacao_id = client.get("/api/perfil/recomendacoes", headers=aluno_a["headers"]).json()[0]["id"]

    resp = client.post(
        f"/api/admin/recomendacoes/{recomendacao_id}/avaliacoes",
        headers=admin_headers,
        json={"concorda_com_llm": True, "nota_humana": 4},
    )
    assert resp.status_code == 201
    assert resp.json()["nota_humana"] == 4
