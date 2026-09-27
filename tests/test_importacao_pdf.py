"""
Importador do PDF de convênios (Fase 5 / passo 12). A extração real
de tabela via PyMuPDF (`extract_convenio_rows`) já foi validada
manualmente contra o PDF real da UFRB (scripts/test_fase5_pdf_real.py)
— aqui, monkeypatchamos exatamente essa fronteira para testar a
lógica de negócio ao redor dela: isolamento de erro por linha
(SAVEPOINT), idempotência do upsert e o relatório final. É a mesma
técnica de "testar a orquestração, não a extração PDF em si" usada em
test_recomendacoes_pipeline.py para o Ollama.
"""

import app.services.importacao.convenios_pdf as convenios_pdf_module
from app.models.empresa import Convenio, Empresa
from app.models.importacao import Importacao


def _fake_rows(monkeypatch, rows):
    monkeypatch.setattr(convenios_pdf_module, "extract_convenio_rows", lambda pdf_bytes: rows)


def test_importacao_com_linhas_validas_cria_empresas_e_convenios(db_session, monkeypatch):
    _fake_rows(
        monkeypatch,
        [
            {"nome": "DevSoft Tecnologia Ltda", "processo": "1/2026", "data_fim_original": "20/05/2027", "pagina": 1},
            {"nome": "Fazenda Bela Vista", "processo": "2/2026", "data_fim_original": "01/01/2020", "pagina": 1},
        ],
    )
    importacao = convenios_pdf_module.import_convenios_pdf(db_session, b"pdf falso", fonte="teste.pdf")

    assert importacao.total_linhas == 2
    assert importacao.sucesso == 2
    assert importacao.erros == []
    assert db_session.query(Empresa).count() == 2
    convenio_devsoft = db_session.query(Convenio).join(Empresa).filter(Empresa.nome == "DevSoft Tecnologia Ltda").first()
    assert convenio_devsoft.status == "vigente"
    convenio_fazenda = db_session.query(Convenio).join(Empresa).filter(Empresa.nome == "Fazenda Bela Vista").first()
    assert convenio_fazenda.status == "vencido"


def test_linha_com_nome_vazio_vira_erro_isolado_sem_derrubar_as_outras(db_session, monkeypatch):
    """O SAVEPOINT por linha é o ponto crítico aqui: uma linha ruim não
    pode arrastar o restante da importação (nem a Importacao em si)."""
    _fake_rows(
        monkeypatch,
        [
            {"nome": "", "processo": None, "data_fim_original": None, "pagina": 1},
            {"nome": "Empresa Válida", "processo": "3/2026", "data_fim_original": "01/01/2030", "pagina": 1},
        ],
    )
    importacao = convenios_pdf_module.import_convenios_pdf(db_session, b"pdf falso", fonte="teste.pdf")

    assert importacao.total_linhas == 2
    assert importacao.sucesso == 1
    assert len(importacao.erros) == 1
    assert importacao.erros[0]["linha"] == 1
    assert db_session.query(Empresa).filter(Empresa.nome == "Empresa Válida").first() is not None


def test_data_malformada_vira_indeterminado_preservando_original(db_session, monkeypatch):
    _fake_rows(
        monkeypatch,
        [{"nome": "Empresa Data Ruim", "processo": None, "data_fim_original": "03/102027", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf falso", fonte="teste.pdf")

    convenio = db_session.query(Convenio).join(Empresa).filter(Empresa.nome == "Empresa Data Ruim").first()
    assert convenio.status == "indeterminado"
    assert convenio.data_fim_original == "03/102027"
    assert convenio.data_fim is None


def test_reimportar_o_mesmo_processo_atualiza_em_vez_de_duplicar(db_session, monkeypatch):
    _fake_rows(
        monkeypatch,
        [{"nome": "Empresa Recorrente", "processo": "9/2026", "data_fim_original": "01/01/2020", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf 1", fonte="primeira.pdf")

    _fake_rows(
        monkeypatch,
        [{"nome": "Empresa Recorrente", "processo": "9/2026", "data_fim_original": "01/01/2030", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf 2", fonte="segunda.pdf")

    convenios = db_session.query(Convenio).join(Empresa).filter(Empresa.nome == "Empresa Recorrente").all()
    assert len(convenios) == 1
    assert convenios[0].status == "vigente"


def test_empresa_pode_ter_varios_convenios_ao_longo_de_reimportacoes(db_session, monkeypatch):
    """Pedido explícito do usuário: numa nova importação, uma empresa
    que já tinha um convênio vigente pode ganhar um SEGUNDO convênio
    (processo diferente, ex.: renovação com número novo, ou termo
    aditivo separado) — o convênio antigo não pode ser perdido nem
    misturado com o novo, os dois convivem no histórico da empresa."""
    _fake_rows(
        monkeypatch,
        [{"nome": "Empresa Multi-Convenio", "processo": "100/2024", "data_fim_original": "01/01/2020", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf antigo", fonte="pdf_antigo.pdf")

    empresa = db_session.query(Empresa).filter(Empresa.nome == "Empresa Multi-Convenio").first()
    convenio_antigo = db_session.query(Convenio).filter(Convenio.empresa_id == empresa.id).first()
    assert convenio_antigo.status == "vencido"
    assert convenio_antigo.processo == "100/2024"

    # PDF novo: mesma empresa, processo NOVO (não é atualização do
    # antigo — é um convênio adicional, com sua própria vigência).
    _fake_rows(
        monkeypatch,
        [{"nome": "Empresa Multi-Convenio", "processo": "200/2026", "data_fim_original": "01/01/2030", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf novo", fonte="pdf_novo.pdf")

    convenios = (
        db_session.query(Convenio)
        .filter(Convenio.empresa_id == empresa.id)
        .order_by(Convenio.processo)
        .all()
    )
    assert len(convenios) == 2, "o convenio antigo nao pode ter sido perdido/sobrescrito"
    assert convenios[0].processo == "100/2024"
    assert convenios[0].status == "vencido"  # continua vencido, intocado
    assert convenios[1].processo == "200/2026"
    assert convenios[1].status == "vigente"




def test_pdf_corrompido_nao_derruba_a_requisicao(db_session, monkeypatch):
    def _levanta_erro(pdf_bytes):
        raise RuntimeError("PDF corrompido (simulado)")

    monkeypatch.setattr(convenios_pdf_module, "extract_convenio_rows", _levanta_erro)
    importacao = convenios_pdf_module.import_convenios_pdf(db_session, b"lixo", fonte="corrompido.pdf")

    assert importacao.finalizado_em is not None
    assert "PDF corrompido" in importacao.erros[0]["erro"]


def test_endpoint_de_upload_exige_admin_e_extensao_pdf(client, admin_headers, aluno_a):
    resp = client.post(
        "/api/admin/importacoes/convenios-pdf",
        headers=aluno_a["headers"],
        files={"file": ("teste.pdf", b"conteudo", "application/pdf")},
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/admin/importacoes/convenios-pdf",
        headers=admin_headers,
        files={"file": ("teste.txt", b"conteudo", "text/plain")},
    )
    assert resp.status_code == 422


def test_endpoint_de_upload_registra_log_de_auditoria(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        convenios_pdf_module,
        "extract_convenio_rows",
        lambda pdf_bytes: [{"nome": "Empresa Via API", "processo": None, "data_fim_original": None, "pagina": 1}],
    )
    resp = client.post(
        "/api/admin/importacoes/convenios-pdf",
        headers=admin_headers,
        files={"file": ("convenios.pdf", b"conteudo fake de pdf", "application/pdf")},
    )
    assert resp.status_code == 201
    importacao_id = resp.json()["id"]

    resp = client.get("/api/admin/logs-auditoria?entidade_tipo=importacao", headers=admin_headers)
    logs = [log for log in resp.json() if log["entidade_id"] == importacao_id]
    assert len(logs) == 1
    assert logs[0]["acao"] == "importar_convenios_pdf"
