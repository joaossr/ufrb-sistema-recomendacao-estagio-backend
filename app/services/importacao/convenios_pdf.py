"""
Importador do PDF de convênios da UFRB (Fase 5 / passo 12). Estrutura
real confirmada com o arquivo de referência fornecido ("TERMOS
FIRMADOS... COOPC..."), via PyMuPDF `find_tables()`:

  - Cada página (exceto uma última página em branco) contém UMA
    tabela de 3 colunas: Empresa | Nº Processo | Término Vigência.
  - A primeira página começa com 3 linhas de título institucional +
    1 linha de cabeçalho ("Nº Processo" / "Término Vigência") antes
    dos dados — são descartadas.
  - Processo e data podem estar ausentes (célula vazia/None) em
    qualquer linha — normal, não é erro.
  - Datas às vezes vêm malformadas (ex.: "03/102027" sem uma barra,
    "27 /02/2029" com espaço perdido) — nunca "corrigidas": o
    parser determinístico (`convenio_status.py`) já trata isso como
    "indeterminado" com segurança.
  - Não há CNPJ nesta fonte — a deduplicação de empresa usa só o nome
    normalizado (ver `services/importacao/empresas.py`).

Cada linha é processada dentro de um SAVEPOINT (`db.begin_nested()`):
um erro numa linha desfaz só aquela linha, nunca a importação inteira.
"""

from datetime import datetime, timezone

import fitz  # PyMuPDF

from sqlalchemy.orm import Session

from app.models.empresa import Convenio
from app.models.importacao import Importacao
from app.services.importacao.convenio_status import parse_and_compute_status
from app.services.importacao.empresas import get_or_create_empresa

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
    return lowered.startswith("convênios de estágio") or lowered.startswith("convenios de estagio")


def extract_convenio_rows(pdf_bytes: bytes) -> list[dict]:
    """Retorna [{nome, processo, data_fim_original, pagina}] — só a
    extração, sem tocar no banco (facilita testar/depurar isoladamente)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    rows: list[dict] = []
    for page in doc:
        tables = page.find_tables()
        for table in tables.tables:
            for row in table.extract():
                if len(row) < 3:
                    continue
                nome, processo, data_fim_original = row[0], row[1], row[2]
                if _is_title_or_header_row(nome):
                    continue
                rows.append(
                    {
                        "nome": (nome or "").strip(),
                        "processo": (processo or "").strip() or None,
                        "data_fim_original": (data_fim_original or "").strip() or None,
                        "pagina": page.number + 1,
                    }
                )
    return rows


def _find_existing_convenio(db: Session, empresa_id, processo: str | None, data_fim_original: str | None):
    query = db.query(Convenio).filter(Convenio.empresa_id == empresa_id)
    if processo:
        return query.filter(Convenio.processo == processo).first()
    return query.filter(Convenio.processo.is_(None), Convenio.data_fim_original == data_fim_original).first()


def import_convenios_pdf(db: Session, pdf_bytes: bytes, fonte: str) -> Importacao:
    importacao = Importacao(fonte=fonte, tipo_arquivo="pdf", total_linhas=0, sucesso=0)
    db.add(importacao)
    db.flush()

    try:
        rows = extract_convenio_rows(pdf_bytes)
    except Exception as exc:  # PDF corrompido, não é bem um PDF, etc.
        importacao.erros = [{"linha": None, "erro": f"Falha ao ler o PDF: {exc}"}]
        importacao.finalizado_em = datetime.now(timezone.utc)
        db.commit()
        db.refresh(importacao)
        return importacao

    importacao.total_linhas = len(rows)
    erros: list[dict] = []
    empresas_criadas = 0
    convenios_criados = 0
    convenios_atualizados = 0

    for idx, row in enumerate(rows, start=1):
        try:
            with db.begin_nested():
                if not row["nome"]:
                    raise ValueError("Nome da empresa vazio.")

                empresa, criada = get_or_create_empresa(db, nome=row["nome"])
                if criada:
                    empresas_criadas += 1

                data_fim, status_calc = parse_and_compute_status(row["data_fim_original"])

                existente = _find_existing_convenio(db, empresa.id, row["processo"], row["data_fim_original"])
                if existente:
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

    importacao.sucesso = len(rows) - len(erros)
    importacao.erros = erros
    importacao.relatorio = {
        "empresas_criadas": empresas_criadas,
        "convenios_criados": convenios_criados,
        "convenios_atualizados": convenios_atualizados,
        "linhas_com_erro": len(erros),
    }
    importacao.finalizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(importacao)
    return importacao
