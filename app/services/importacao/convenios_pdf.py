"""
Importador do PDF de convênios/vagas da UFRB (Fase 5 / passo 12,
estendido nas Fases 16 e 17). Reconhece TRÊS formatos de tabela, via
PyMuPDF `find_tables()` — a classificação usa o texto do CABEÇALHO de
cada tabela, nunca só a contagem de colunas (duas fontes reais
tinham exatamente 9 colunas cada, com significados diferentes):

  - FORMATO ANTIGO (3 colunas, sem cabeçalho com "CNPJ"/"Vaga"):
    Empresa | Nº Processo | Término Vigência. Arquivo de referência
    original ("TERMOS FIRMADOS... COOPC..."). Datas em DD/MM/AAAA.
    Sem CNPJ — deduplicação de empresa usa só o nome normalizado.
  - FORMATO EMPRESA+CONVÊNIO (9 colunas, cabeçalho contém "CNPJ"):
    ID | Empresa | Área | Cidade | CNPJ | Nº Convênio/Processo |
    Situação | Início | Término. Datas em AAAA-MM-DD (ISO).
  - FORMATO VAGA (9 colunas, cabeçalho contém "Vaga"): Empresa | Área
    | Vaga | Requisitos | Tecnologias/Ferramentas | Modalidade |
    Carga | Bolsa | Qtd. Vem em páginas separadas do formato
    empresa+convênio, ligada a ele só pelo NOME da empresa (sem CNPJ
    nem nº de processo) — por isso as linhas de convênio são
    processadas ANTES das de vaga, e uma vaga cuja empresa não existe
    ainda vira erro isolado daquela linha (nunca inventa uma empresa
    nova a partir de uma linha de vaga sem CNPJ).

Em qualquer formato, a coluna "Situação"/status (quando existe) é só
informativa — o status determinístico do convênio SEMPRE é
recalculado a partir da data de término, nunca lido direto da fonte.

Cada linha é processada dentro de um SAVEPOINT (`db.begin_nested()`):
um erro numa linha desfaz só aquela linha, nunca a importação inteira.
"""

from datetime import datetime, timezone

import fitz  # PyMuPDF

from sqlalchemy.orm import Session

from app.models.empresa import Convenio, Empresa
from app.models.importacao import Importacao
from app.models.vaga import Vaga
from app.services.embeddings.service import regenerate_empresa_embedding, regenerate_vaga_embedding
from app.services.importacao.convenio_status import (
    parse_and_compute_status,
    parse_and_compute_status_iso,
    parse_iso_date,
)
from app.services.importacao.empresas import get_or_create_empresa, normalize_company_name

_TITLE_PREFIXES = (
    "PRÓ-REITORIA DE PLANEJAMENTO",
    "COORDENADORIA DE PROJETOS E CONVÊNIOS",
    "NÚCLEO DE APOIO",
)


def _is_title_or_header_row(nome: str) -> bool:
    nome = (nome or "").strip()
    if not nome:
        return True
    if any(nome.upper().startswith(p) for p in _TITLE_PREFIXES):
        return True
    lowered = nome.lower()
    if lowered.startswith("convênios de estágio") or lowered.startswith("convenios de estagio"):
        return True
    return lowered == "empresa"  # cabeçalho de coluna dos formatos novos (9 colunas)


def _celula(valor) -> str | None:
    valor = str(valor or "").replace("\n", " ").strip()
    return valor or None


def _split_lista(valor) -> list[str]:
    valor = str(valor or "").replace("\n", " ")
    return [item.strip() for item in valor.split(";") if item.strip()]


def _int_ou_none(valor) -> int | None:
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return int(float(valor))
    except ValueError:
        return None


def _linha_formato_antigo(row: list, pagina: int) -> dict | None:
    nome, processo, data_fim_original = row[0], row[1], row[2]
    if _is_title_or_header_row(nome):
        return None
    return {
        "tipo": "convenio",
        "formato": "antigo",
        "nome": (nome or "").strip(),
        "processo": _celula(processo),
        "data_fim_original": _celula(data_fim_original),
        "data_inicio_original": None,
        "cnpj": None,
        "area": None,
        "cidade": None,
        "pagina": pagina,
    }


def _linha_formato_novo(row: list, pagina: int) -> dict | None:
    """9 colunas: ID | Empresa | Área | Cidade | CNPJ | Nº Convênio/
    Processo | Situação | Início | Término."""
    _id, nome, area, cidade, cnpj, processo, _situacao, data_inicio, data_fim = row[:9]
    if _is_title_or_header_row(nome):
        return None
    return {
        "tipo": "convenio",
        "formato": "novo",
        "nome": (nome or "").strip(),
        "processo": _celula(processo),
        "data_fim_original": _celula(data_fim),
        "data_inicio_original": _celula(data_inicio),
        "cnpj": _celula(cnpj),
        "area": _celula(area),
        "cidade": _celula(cidade),
        "pagina": pagina,
    }


def _linha_vaga(row: list, pagina: int) -> dict | None:
    """9 colunas: Empresa | Área | Vaga | Requisitos | Tecnologias/
    Ferramentas | Modalidade | Carga | Bolsa | Qtd."""
    nome_empresa, area, titulo, requisitos, tecnologias, modalidade, carga, bolsa, qtd = row[:9]
    if _is_title_or_header_row(nome_empresa):
        return None
    titulo = _celula(titulo)
    if not titulo:
        return None
    return {
        "tipo": "vaga",
        "empresa_nome": (nome_empresa or "").strip(),
        "area": _celula(area),
        "titulo": titulo,
        "requisitos": ", ".join(_split_lista(requisitos)) or None,
        "tecnologias": _split_lista(tecnologias),
        "modalidade": _celula(modalidade),
        "carga_horaria": _celula(carga),
        "bolsa": _celula(bolsa),
        "quantidade": _int_ou_none(qtd),
        "pagina": pagina,
    }


def _classificar_cabecalho(header: list) -> str:
    """Decide o formato da tabela pelo texto do cabeçalho (linha 0) —
    nunca só pela contagem de colunas: os formatos 'novo' (empresa+
    convênio) e 'vaga' desta fonte têm as duas exatamente 9 colunas."""
    texto = " ".join(str(c or "") for c in header).lower()
    if "cnpj" in texto:
        return "empresa_convenio"
    if "vaga" in texto:
        return "vaga"
    return "antigo"


def extract_convenio_rows(pdf_bytes: bytes) -> dict:
    """Retorna {"convenios": [...], "vagas": [...]} — só a extração,
    sem tocar no banco (facilita testar/depurar isoladamente)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    convenios: list[dict] = []
    vagas: list[dict] = []
    for page in doc:
        tables = page.find_tables()
        for table in tables.tables:
            extraido = table.extract()
            if not extraido:
                continue
            formato_tabela = _classificar_cabecalho(extraido[0])
            for row in extraido:
                if formato_tabela == "vaga":
                    if len(row) < 9:
                        continue
                    linha = _linha_vaga(row, page.number + 1)
                    if linha is not None:
                        vagas.append(linha)
                elif formato_tabela == "empresa_convenio":
                    if len(row) < 9:
                        continue
                    linha = _linha_formato_novo(row, page.number + 1)
                    if linha is not None:
                        convenios.append(linha)
                else:  # formato antigo — _linha_formato_antigo já filtra título/cabeçalho
                    if len(row) < 3:
                        continue
                    linha = _linha_formato_antigo(row, page.number + 1)
                    if linha is not None:
                        convenios.append(linha)
    return {"convenios": convenios, "vagas": vagas}


def _find_existing_convenio(db: Session, empresa_id, processo: str | None, data_fim_original: str | None):
    query = db.query(Convenio).filter(Convenio.empresa_id == empresa_id)
    if processo:
        return query.filter(Convenio.processo == processo).first()
    return query.filter(Convenio.processo.is_(None), Convenio.data_fim_original == data_fim_original).first()


def _find_empresa_por_nome(db: Session, nome: str) -> Empresa | None:
    return db.query(Empresa).filter(Empresa.nome_normalizado == normalize_company_name(nome)).first()


def _find_or_create_vaga(db: Session, empresa: Empresa, linha: dict) -> tuple[Vaga, bool]:
    existente = (
        db.query(Vaga)
        .filter(Vaga.empresa_id == empresa.id, Vaga.titulo == linha["titulo"], Vaga.convenio_id.is_(None))
        .first()
    )
    area = linha.get("area")
    campos = {
        "requisitos": linha.get("requisitos"),
        "cursos": [area] if area else [],
        "areas": [area] if area else [],
        "tecnologias": linha.get("tecnologias") or [],
        "modalidade": linha.get("modalidade"),
        "bolsa": linha.get("bolsa"),
        "carga_horaria": linha.get("carga_horaria"),
        "quantidade": linha.get("quantidade"),
    }
    if existente:
        for campo, valor in campos.items():
            setattr(existente, campo, valor)
        db.flush()
        return existente, False

    vaga = Vaga(empresa_id=empresa.id, titulo=linha["titulo"], status="ativa", **campos)
    db.add(vaga)
    db.flush()
    return vaga, True


def import_convenios_pdf(db: Session, pdf_bytes: bytes, fonte: str) -> Importacao:
    importacao = Importacao(fonte=fonte, tipo_arquivo="pdf", total_linhas=0, sucesso=0)
    db.add(importacao)
    db.flush()

    try:
        extraido = extract_convenio_rows(pdf_bytes)
    except Exception as exc:  # PDF corrompido, não é bem um PDF, etc.
        importacao.erros = [{"linha": None, "erro": f"Falha ao ler o PDF: {exc}"}]
        importacao.finalizado_em = datetime.now(timezone.utc)
        db.commit()
        db.refresh(importacao)
        return importacao

    linhas_convenio = extraido["convenios"]
    linhas_vaga = extraido["vagas"]
    importacao.total_linhas = len(linhas_convenio) + len(linhas_vaga)
    erros: list[dict] = []
    empresas_criadas = 0
    convenios_criados = 0
    convenios_atualizados = 0
    vagas_criadas = 0
    vagas_atualizadas = 0
    empresas_para_reembedar: dict = {}
    vagas_para_reembedar: list = []

    # Passo 1: empresas + convênios — sempre primeiro, porque as
    # linhas de vaga (quando existem) só sabem o NOME da empresa e
    # dependem dela já existir no banco.
    for idx, row in enumerate(linhas_convenio, start=1):
        try:
            with db.begin_nested():
                if not row["nome"]:
                    raise ValueError("Nome da empresa vazio.")

                empresa, criada = get_or_create_empresa(
                    db,
                    nome=row["nome"],
                    cnpj=row.get("cnpj"),
                    area=row.get("area"),
                    cidade=row.get("cidade"),
                )
                if criada:
                    empresas_criadas += 1
                empresas_para_reembedar[empresa.id] = empresa

                if row["formato"] == "novo":
                    data_inicio = parse_iso_date(row.get("data_inicio_original"))
                    data_fim, status_calc = parse_and_compute_status_iso(row["data_fim_original"])
                else:
                    data_inicio = None
                    data_fim, status_calc = parse_and_compute_status(row["data_fim_original"])

                existente = _find_existing_convenio(db, empresa.id, row["processo"], row["data_fim_original"])
                if existente:
                    existente.data_inicio = data_inicio
                    existente.data_fim_original = row["data_fim_original"]
                    existente.data_fim = data_fim
                    existente.status = status_calc
                    existente.fonte = fonte
                    existente.pagina_origem = str(row["pagina"])
                    convenios_atualizados += 1
                else:
                    db.add(
                        Convenio(
                            empresa_id=empresa.id,
                            processo=row["processo"],
                            data_inicio=data_inicio,
                            data_fim_original=row["data_fim_original"],
                            data_fim=data_fim,
                            status=status_calc,
                            fonte=fonte,
                            pagina_origem=str(row["pagina"]),
                        )
                    )
                    convenios_criados += 1
        except Exception as exc:
            erros.append({"linha": idx, "dado": row, "erro": str(exc)})

    # Passo 2: vagas — cada uma precisa achar a empresa já processada
    # acima pelo nome normalizado; se não achar, é erro isolado
    # daquela linha (nunca inventa empresa nova a partir de uma vaga).
    offset = len(linhas_convenio)
    for idx, linha in enumerate(linhas_vaga, start=1):
        try:
            with db.begin_nested():
                empresa = _find_empresa_por_nome(db, linha["empresa_nome"])
                if empresa is None:
                    raise ValueError(f"Empresa '{linha['empresa_nome']}' não encontrada (linha de vaga sem convênio correspondente).")

                vaga, criada = _find_or_create_vaga(db, empresa, linha)
                vagas_para_reembedar.append(vaga)
                empresas_para_reembedar[empresa.id] = empresa
                if criada:
                    vagas_criadas += 1
                else:
                    vagas_atualizadas += 1
        except Exception as exc:
            erros.append({"linha": offset + idx, "dado": linha, "erro": str(exc)})

    for vaga in vagas_para_reembedar:
        regenerate_vaga_embedding(db, vaga)
    for empresa in empresas_para_reembedar.values():
        regenerate_empresa_embedding(db, empresa)
    db.commit()

    importacao.sucesso = importacao.total_linhas - len(erros)
    importacao.erros = erros
    importacao.relatorio = {
        "empresas_criadas": empresas_criadas,
        "convenios_criados": convenios_criados,
        "convenios_atualizados": convenios_atualizados,
        "vagas_criadas": vagas_criadas,
        "vagas_atualizadas": vagas_atualizadas,
        "linhas_com_erro": len(erros),
    }
    importacao.finalizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(importacao)
    return importacao
