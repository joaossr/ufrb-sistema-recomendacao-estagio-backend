"""
Importador de planilha CSV/XLSX de empresas+convênios+vagas (Fase 12).
Foco aqui: garantir que uma empresa pode acumular VÁRIOS convênios ao
longo de reimportações sucessivas (cada um com seu próprio número de
processo) sem perder histórico nem misturar dados — mesma garantia já
coberta para o importador de PDF em test_importacao_pdf.py, só que
para o formato que o usuário efetivamente usou na Fase 12.
"""

from app.models.empresa import Convenio, Empresa
from app.models.vaga import Vaga
from app.services.importacao.empresas_vagas_planilha import import_empresas_vagas_planilha

_CABECALHO = "empresa_id;empresa;cnpj;area;segmento;cidade;uf;convenio;status;inicio;termino;vaga_id;vaga;descricao;requisitos;tecnologias;modalidade;carga;bolsa;auxilio;qtd"


def _csv(linhas: list[str]) -> bytes:
    return ("\n".join([_CABECALHO] + linhas)).encode("utf-8")


def test_empresa_pode_ter_varios_convenios_ao_longo_de_reimportacoes_csv(db_session, mock_ollama):
    """Mesma garantia do importador de PDF: reimportar com um processo
    NOVO para uma empresa já conhecida ADICIONA um convênio, nunca
    perde ou sobrescreve o antigo."""
    csv_antigo = _csv(
        [
            "1;Empresa Multi Convenio CSV;00.000.099/0001-99;Zootecnia;Produção Animal;Cruz das Almas;BA;"
            "CONV-ANTIGO;Inativo;2018-01-01;2020-01-01;101;Estágio Antigo;Descrição;Requisito;Excel;"
            "Presencial;20h semanais;R$ 700,00;Vale-transporte;1"
        ]
    )
    import_empresas_vagas_planilha(db_session, csv_antigo, "csv", fonte="antigo.csv")

    empresa = db_session.query(Empresa).filter(Empresa.nome == "Empresa Multi Convenio CSV").first()
    assert empresa is not None
    convenio_antigo = db_session.query(Convenio).filter(Convenio.empresa_id == empresa.id).first()
    assert convenio_antigo.processo == "CONV-ANTIGO"
    assert convenio_antigo.status == "vencido"

    csv_novo = _csv(
        [
            "1;Empresa Multi Convenio CSV;00.000.099/0001-99;Zootecnia;Produção Animal;Cruz das Almas;BA;"
            "CONV-NOVO;Ativo;2026-01-01;2028-01-01;102;Estágio Novo;Descrição nova;Requisito novo;Excel;"
            "Remoto;30h semanais;R$ 900,00;Vale-transporte;2"
        ]
    )
    import_empresas_vagas_planilha(db_session, csv_novo, "csv", fonte="novo.csv")

    # a mesma empresa (achada pelo CNPJ) — nunca duplicada
    assert db_session.query(Empresa).filter(Empresa.nome == "Empresa Multi Convenio CSV").count() == 1

    convenios = (
        db_session.query(Convenio).filter(Convenio.empresa_id == empresa.id).order_by(Convenio.processo).all()
    )
    assert len(convenios) == 2, "o convenio antigo nao pode ter sido perdido/sobrescrito"
    assert convenios[0].processo == "CONV-ANTIGO"
    assert convenios[0].status == "vencido"  # continua intocado
    assert convenios[1].processo == "CONV-NOVO"
    assert convenios[1].status == "vigente"

    vagas = db_session.query(Vaga).filter(Vaga.empresa_id == empresa.id).all()
    assert len(vagas) == 2, "as duas vagas (uma por convenio) tem que coexistir"


def test_reimportar_mesmo_processo_atualiza_status_em_vez_de_duplicar_csv(db_session, mock_ollama):
    csv_v1 = _csv(
        [
            "1;Empresa Recorrente CSV;00.000.088/0001-88;Biologia;Pesquisa;Salvador;BA;"
            "CONV-X;Ativo;2026-01-01;2020-01-01;201;Estágio Bio;Descrição;Requisito;Excel;"
            "Presencial;20h semanais;R$ 700,00;Vale-transporte;1"
        ]
    )
    import_empresas_vagas_planilha(db_session, csv_v1, "csv", fonte="v1.csv")

    csv_v2 = _csv(
        [
            "1;Empresa Recorrente CSV;00.000.088/0001-88;Biologia;Pesquisa;Salvador;BA;"
            "CONV-X;Ativo;2026-01-01;2030-01-01;201;Estágio Bio;Descrição;Requisito;Excel;"
            "Presencial;20h semanais;R$ 700,00;Vale-transporte;1"
        ]
    )
    import_empresas_vagas_planilha(db_session, csv_v2, "csv", fonte="v2.csv")

    empresa = db_session.query(Empresa).filter(Empresa.nome == "Empresa Recorrente CSV").first()
    convenios = db_session.query(Convenio).filter(Convenio.empresa_id == empresa.id).all()
    assert len(convenios) == 1, "mesmo processo reimportado deve atualizar a linha existente, nao duplicar"
    assert convenios[0].status == "vigente"
    assert str(convenios[0].data_fim) == "2030-01-01"
