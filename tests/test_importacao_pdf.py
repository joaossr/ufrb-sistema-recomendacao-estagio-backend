"""
Importador de PDF de convênios/vagas (Fase 5 / passo 12, estendido nas
Fases 16/17). A extração real de tabela via PyMuPDF
(`extract_convenio_rows`) já foi validada manualmente contra PDFs
reais (scripts/test_fase5_pdf_real.py e a investigação da Fase 17) —
aqui, monkeypatchamos exatamente essa fronteira para testar a lógica
de negócio ao redor dela: isolamento de erro por linha (SAVEPOINT),
idempotência do upsert e o relatório final. Mesma técnica de "testar
a orquestração, não a extração PDF em si" usada em
test_recomendacoes_pipeline.py para o Ollama.

`extract_convenio_rows` retorna {"convenios": [...], "vagas": [...]}
— dois formatos de linha "convenio" existem ("antigo" 3 colunas,
"novo" 9 colunas com CNPJ), e um formato "vaga" (9 colunas, ligado ao
convênio só pelo nome da empresa, sem CNPJ/processo).
"""

import app.services.importacao.convenios_pdf as convenios_pdf_module
from app.models.empresa import Convenio, Empresa
from app.models.importacao import Importacao
from app.models.vaga import Vaga


def _fake_extract(monkeypatch, convenios=None, vagas=None):
    """Preenche as chaves do formato novo de convênio com o padrão do
    formato antigo, para os testes que só se importam com o
    comportamento comum não precisarem repetir tudo."""
    linhas_completas = [
        {"formato": "antigo", "data_inicio_original": None, "cnpj": None, "area": None, "cidade": None, **linha}
        for linha in (convenios or [])
    ]
    resultado = {"convenios": linhas_completas, "vagas": vagas or []}
    monkeypatch.setattr(convenios_pdf_module, "extract_convenio_rows", lambda pdf_bytes: resultado)


def test_importacao_com_linhas_validas_cria_empresas_e_convenios(db_session, monkeypatch, mock_ollama):
    _fake_extract(
        monkeypatch,
        convenios=[
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


def test_linha_com_nome_vazio_vira_erro_isolado_sem_derrubar_as_outras(db_session, monkeypatch, mock_ollama):
    """O SAVEPOINT por linha é o ponto crítico aqui: uma linha ruim não
    pode arrastar o restante da importação (nem a Importacao em si)."""
    _fake_extract(
        monkeypatch,
        convenios=[
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


def test_data_malformada_vira_indeterminado_preservando_original(db_session, monkeypatch, mock_ollama):
    _fake_extract(
        monkeypatch,
        convenios=[{"nome": "Empresa Data Ruim", "processo": None, "data_fim_original": "03/102027", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf falso", fonte="teste.pdf")

    convenio = db_session.query(Convenio).join(Empresa).filter(Empresa.nome == "Empresa Data Ruim").first()
    assert convenio.status == "indeterminado"
    assert convenio.data_fim_original == "03/102027"
    assert convenio.data_fim is None


def test_reimportar_o_mesmo_processo_atualiza_em_vez_de_duplicar(db_session, monkeypatch, mock_ollama):
    _fake_extract(
        monkeypatch,
        convenios=[{"nome": "Empresa Recorrente", "processo": "9/2026", "data_fim_original": "01/01/2020", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf 1", fonte="primeira.pdf")

    _fake_extract(
        monkeypatch,
        convenios=[{"nome": "Empresa Recorrente", "processo": "9/2026", "data_fim_original": "01/01/2030", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf 2", fonte="segunda.pdf")

    convenios = db_session.query(Convenio).join(Empresa).filter(Empresa.nome == "Empresa Recorrente").all()
    assert len(convenios) == 1
    assert convenios[0].status == "vigente"


def test_empresa_pode_ter_varios_convenios_ao_longo_de_reimportacoes(db_session, monkeypatch, mock_ollama):
    """Pedido explícito do usuário: numa nova importação, uma empresa
    que já tinha um convênio vigente pode ganhar um SEGUNDO convênio
    (processo diferente, ex.: renovação com número novo, ou termo
    aditivo separado) — o convênio antigo não pode ser perdido nem
    misturado com o novo, os dois convivem no histórico da empresa."""
    _fake_extract(
        monkeypatch,
        convenios=[{"nome": "Empresa Multi-Convenio", "processo": "100/2024", "data_fim_original": "01/01/2020", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf antigo", fonte="pdf_antigo.pdf")

    empresa = db_session.query(Empresa).filter(Empresa.nome == "Empresa Multi-Convenio").first()
    convenio_antigo = db_session.query(Convenio).filter(Convenio.empresa_id == empresa.id).first()
    assert convenio_antigo.status == "vencido"
    assert convenio_antigo.processo == "100/2024"

    # PDF novo: mesma empresa, processo NOVO (não é atualização do
    # antigo — é um convênio adicional, com sua própria vigência).
    _fake_extract(
        monkeypatch,
        convenios=[{"nome": "Empresa Multi-Convenio", "processo": "200/2026", "data_fim_original": "01/01/2030", "pagina": 1}],
    )
    convenios_pdf_module.import_convenios_pdf(db_session, b"pdf novo", fonte="pdf_novo.pdf")

    convenios = (
        db_session.query(Convenio).filter(Convenio.empresa_id == empresa.id).order_by(Convenio.processo).all()
    )
    assert len(convenios) == 2, "o convenio antigo nao pode ter sido perdido/sobrescrito"
    assert convenios[0].processo == "100/2024"
    assert convenios[0].status == "vencido"  # continua vencido, intocado
    assert convenios[1].processo == "200/2026"
    assert convenios[1].status == "vigente"


def test_linha_formato_novo_extrai_os_campos_certos_da_tabela_de_9_colunas():
    """Reproduz o bug relatado pelo usuário: um PDF com uma tabela de
    9 colunas (ID | Empresa | Área | Cidade | CNPJ | Processo |
    Situação | Início | Término) estava sendo lida como se fosse o
    formato antigo de 3 colunas — a coluna 'ID' virava o nome da
    empresa (por isso apareciam empresas com nome '1', '10', '11'...).
    Testa direto a função que decide os índices de coluna."""
    linha_da_tabela = [
        "1", "Clínica Vet Prime", "Medicina Veterinária", "Feira de Santana",
        "00.100.001/0001-01", "CONV-UFRB-2001", "Ativo", "2026-02-01", "2027-01-31",
    ]

    linha = convenios_pdf_module._linha_formato_novo(linha_da_tabela, pagina=1)

    assert linha["formato"] == "novo"
    assert linha["nome"] == "Clínica Vet Prime"  # NUNCA "1" (a coluna ID)
    assert linha["cnpj"] == "00.100.001/0001-01"
    assert linha["area"] == "Medicina Veterinária"
    assert linha["cidade"] == "Feira de Santana"
    assert linha["processo"] == "CONV-UFRB-2001"
    assert linha["data_inicio_original"] == "2026-02-01"
    assert linha["data_fim_original"] == "2027-01-31"


def test_classificar_cabecalho_distingue_os_tres_formatos():
    """As tabelas 'empresa+convênio' e 'vaga' desta fonte real têm as
    DUAS 9 colunas — não dá pra distinguir só pela contagem, tem que
    olhar o texto do cabeçalho."""
    cab_convenio = ["ID", "Empresa", "Área", "Cidade", "CNPJ TESTE", "Nº Convênio/Processo", "Situação", "Início", "Término"]
    cab_vaga = ["Empresa", "Área", "Vaga", "Requisitos", "Tecnologias/Ferramentas", "Modalidade", "Carga", "Bolsa", "Qtd."]
    cab_antigo = ["PRÓ-REITORIA DE PLANEJAMENTO, EXPANSÃO..."]

    assert convenios_pdf_module._classificar_cabecalho(cab_convenio) == "empresa_convenio"
    assert convenios_pdf_module._classificar_cabecalho(cab_vaga) == "vaga"
    assert convenios_pdf_module._classificar_cabecalho(cab_antigo) == "antigo"


def test_importacao_com_formato_novo_grava_empresa_com_cnpj_area_e_cidade(db_session, monkeypatch, mock_ollama):
    convenio_novo_formato = {
        "formato": "novo",
        "nome": "Clínica Vet Prime",
        "processo": "CONV-UFRB-2001",
        "data_fim_original": "2027-01-31",
        "data_inicio_original": "2026-02-01",
        "cnpj": "00.100.001/0001-01",
        "area": "Medicina Veterinária",
        "cidade": "Feira de Santana",
        "pagina": 1,
    }
    monkeypatch.setattr(
        convenios_pdf_module, "extract_convenio_rows", lambda pdf_bytes: {"convenios": [convenio_novo_formato], "vagas": []}
    )
    importacao = convenios_pdf_module.import_convenios_pdf(db_session, b"pdf falso", fonte="novo.pdf")

    assert importacao.sucesso == 1
    empresa = db_session.query(Empresa).filter(Empresa.nome == "Clínica Vet Prime").first()
    assert empresa is not None
    assert empresa.cnpj == "00100001000101"  # normalizado, só dígitos
    assert empresa.area == "Medicina Veterinária"
    assert empresa.cidade == "Feira de Santana"

    convenio = db_session.query(Convenio).filter(Convenio.empresa_id == empresa.id).first()
    assert convenio.status == "vigente"  # 2027-01-31 é no futuro
    assert str(convenio.data_inicio) == "2026-02-01"


def test_vaga_e_vinculada_a_empresa_ja_criada_pelo_convenio(db_session, monkeypatch, mock_ollama):
    """Reproduz a estrutura real: tabela de convênio (com CNPJ) numa
    página, tabela de vaga (só nome da empresa) noutra — a vaga tem
    que achar a MESMA empresa pelo nome normalizado."""
    convenio = {
        "formato": "novo",
        "nome": "Clínica Vet Prime Ltda",
        "processo": "CONV-UFRB-2001",
        "data_fim_original": "2027-01-31",
        "data_inicio_original": "2026-02-01",
        "cnpj": "00.100.001/0001-01",
        "area": "Medicina Veterinária",
        "cidade": "Feira de Santana",
        "pagina": 1,
    }
    vaga = {
        "tipo": "vaga",
        "empresa_nome": "Clínica Vet Prime",  # sem "Ltda" — normalizado bate igual
        "area": "Medicina Veterinária",
        "titulo": "Estágio em Clínica Veterinária",
        "requisitos": "Semiologia, Clínica Médica",
        "tecnologias": ["Excel", "Sistemas de prontuário"],
        "modalidade": "Híbrido",
        "carga_horaria": "20h semanais",
        "bolsa": "R$ 1.000,00",
        "quantidade": 2,
        "pagina": 3,
    }
    monkeypatch.setattr(
        convenios_pdf_module, "extract_convenio_rows", lambda pdf_bytes: {"convenios": [convenio], "vagas": [vaga]}
    )
    importacao = convenios_pdf_module.import_convenios_pdf(db_session, b"pdf falso", fonte="completo.pdf")

    assert importacao.total_linhas == 2
    assert importacao.sucesso == 2
    assert importacao.erros == []
    assert importacao.relatorio["vagas_criadas"] == 1

    empresa = db_session.query(Empresa).filter(Empresa.nome == "Clínica Vet Prime Ltda").first()
    vaga_criada = db_session.query(Vaga).filter(Vaga.empresa_id == empresa.id).first()
    assert vaga_criada is not None
    assert vaga_criada.titulo == "Estágio em Clínica Veterinária"
    assert vaga_criada.tecnologias == ["Excel", "Sistemas de prontuário"]
    assert vaga_criada.cursos == ["Medicina Veterinária"]


def test_vaga_sem_empresa_correspondente_vira_erro_isolado(db_session, monkeypatch, mock_ollama):
    """Nunca inventa uma empresa nova a partir de uma linha de vaga
    (que não tem CNPJ) — se o nome não bate com nenhuma empresa já
    processada, é erro isolado daquela linha."""
    vaga_orfa = {
        "tipo": "vaga",
        "empresa_nome": "Empresa Que Não Existe",
        "area": None,
        "titulo": "Estágio Fantasma",
        "requisitos": None,
        "tecnologias": [],
        "modalidade": None,
        "carga_horaria": None,
        "bolsa": None,
        "quantidade": None,
        "pagina": 1,
    }
    monkeypatch.setattr(
        convenios_pdf_module, "extract_convenio_rows", lambda pdf_bytes: {"convenios": [], "vagas": [vaga_orfa]}
    )
    importacao = convenios_pdf_module.import_convenios_pdf(db_session, b"pdf falso", fonte="orfa.pdf")

    assert importacao.total_linhas == 1
    assert importacao.sucesso == 0
    assert len(importacao.erros) == 1
    assert "não encontrada" in importacao.erros[0]["erro"]
    assert db_session.query(Vaga).count() == 0


def test_pdf_corrompido_nao_derruba_a_requisicao(db_session, monkeypatch, mock_ollama):
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


def test_endpoint_de_upload_registra_log_de_auditoria(client, admin_headers, monkeypatch, mock_ollama):
    _fake_extract(monkeypatch, convenios=[{"nome": "Empresa Via API", "processo": None, "data_fim_original": None, "pagina": 1}])
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
