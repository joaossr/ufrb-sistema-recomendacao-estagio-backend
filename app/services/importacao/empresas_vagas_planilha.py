"""
Importador de planilha (CSV/XLSX) de empresas + convênios + vagas
(Fase 12). Diferente do importador de PDF (Fase 5, só empresa+convênio,
3 colunas), esta fonte traz uma linha por vaga com empresa/CNPJ/
convênio/vaga juntos — cada linha é decomposta nos três registros
correspondentes (`Empresa`, `Convenio`, `Vaga`), nunca guardada como
blob de texto.

CNPJ é o identificador preferencial de empresa (`get_or_create_empresa`
já prioriza isso desde a Fase 5) — evita duplicar/misturar empresas
diferentes quando o nome varia levemente entre importações.

Cada linha roda dentro de um SAVEPOINT (`db.begin_nested()`), igual ao
importador de PDF: uma linha malformada vira um erro isolado, nunca
derruba a importação inteira.
"""

import io
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.models.empresa import Convenio, Empresa
from app.models.importacao import Importacao
from app.models.vaga import Vaga
from app.services.embeddings.service import regenerate_empresa_embedding, regenerate_vaga_embedding
from app.services.importacao.convenio_status import parse_and_compute_status_iso, parse_iso_date
from app.services.importacao.empresas import get_or_create_empresa

_COLUNAS_OBRIGATORIAS = {"empresa", "vaga"}


def _ler_planilha(conteudo: bytes, extensao: str) -> pd.DataFrame:
    if extensao == "csv":
        ultimo_erro: Exception | None = None
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(
                    io.BytesIO(conteudo), sep=";", dtype=str, keep_default_na=False, encoding=encoding
                )
            except UnicodeDecodeError as exc:
                ultimo_erro = exc
                continue
        raise ValueError(f"Não foi possível decodificar o CSV: {ultimo_erro}")
    if extensao == "xlsx":
        return pd.read_excel(io.BytesIO(conteudo), dtype=str, keep_default_na=False)
    raise ValueError(f"Extensão não suportada: {extensao}")


def _texto_ou_none(valor) -> str | None:
    valor = str(valor or "").strip()
    return valor or None


def _split_lista(valor) -> list[str]:
    valor = str(valor or "")
    return [item.strip() for item in valor.split(";") if item.strip()]


def _int_ou_none(valor) -> int | None:
    valor = str(valor or "").strip()
    if not valor:
        return None
    try:
        return int(float(valor))
    except ValueError:
        return None


def _find_or_create_convenio(db: Session, empresa: Empresa, row: dict, fonte: str) -> tuple[Convenio | None, bool]:
    processo = _texto_ou_none(row.get("convenio"))
    data_inicio = parse_iso_date(row.get("inicio"))
    data_fim_raw = _texto_ou_none(row.get("termino"))
    data_fim, status_calc = parse_and_compute_status_iso(data_fim_raw)
    status_bruto = _texto_ou_none(row.get("status"))

    if not processo and not data_fim_raw:
        # Linha sem nenhuma informação de convênio — a vaga fica sem
        # convênio vinculado (não filtra por isso, ver regras.py).
        return None, False

    query = db.query(Convenio).filter(Convenio.empresa_id == empresa.id)
    existente = (
        query.filter(Convenio.processo == processo).first()
        if processo
        else query.filter(Convenio.processo.is_(None), Convenio.data_fim_original == data_fim_raw).first()
    )

    observacoes = f"Status informado na fonte: {status_bruto}" if status_bruto else None

    if existente:
        existente.data_inicio = data_inicio
        existente.data_fim_original = data_fim_raw
        existente.data_fim = data_fim
        existente.status = status_calc
        existente.fonte = fonte
        existente.observacoes = observacoes
        return existente, False

    convenio = Convenio(
        empresa_id=empresa.id,
        processo=processo,
        data_inicio=data_inicio,
        data_fim_original=data_fim_raw,
        data_fim=data_fim,
        status=status_calc,
        fonte=fonte,
        observacoes=observacoes,
    )
    db.add(convenio)
    db.flush()
    return convenio, True


def _find_or_create_vaga(db: Session, empresa: Empresa, convenio: Convenio | None, row: dict) -> tuple[Vaga, bool]:
    titulo = _texto_ou_none(row.get("vaga"))
    if not titulo:
        raise ValueError("Vaga sem título (coluna 'vaga' vazia).")

    convenio_id = convenio.id if convenio else None
    existente = (
        db.query(Vaga)
        .filter(Vaga.empresa_id == empresa.id, Vaga.titulo == titulo, Vaga.convenio_id == convenio_id)
        .first()
    )

    area = _texto_ou_none(row.get("area"))
    cidade = _texto_ou_none(row.get("cidade"))
    uf = _texto_ou_none(row.get("uf"))
    localizacao = " - ".join(p for p in (cidade, uf) if p) or None

    campos = {
        "descricao": _texto_ou_none(row.get("descricao")),
        "requisitos": ", ".join(_split_lista(row.get("requisitos"))) or None,
        "cursos": [area] if area else [],
        "areas": [area] if area else [],
        "tecnologias": _split_lista(row.get("tecnologias")),
        "modalidade": _texto_ou_none(row.get("modalidade")),
        "localizacao": localizacao,
        "bolsa": _texto_ou_none(row.get("bolsa")),
        "carga_horaria": _texto_ou_none(row.get("carga")),
        "beneficios": _texto_ou_none(row.get("auxilio")),
        "quantidade": _int_ou_none(row.get("qtd")),
        "convenio_id": convenio_id,
    }

    if existente:
        for campo, valor in campos.items():
            setattr(existente, campo, valor)
        db.flush()
        return existente, False

    vaga = Vaga(empresa_id=empresa.id, titulo=titulo, status="ativa", **campos)
    db.add(vaga)
    db.flush()
    return vaga, True


def import_empresas_vagas_planilha(db: Session, conteudo: bytes, extensao: str, fonte: str) -> Importacao:
    importacao = Importacao(fonte=fonte, tipo_arquivo=extensao, total_linhas=0, sucesso=0)
    db.add(importacao)
    db.flush()

    try:
        df = _ler_planilha(conteudo, extensao)
        df.columns = [str(c).strip().lower() for c in df.columns]
        faltantes = _COLUNAS_OBRIGATORIAS - set(df.columns)
        if faltantes:
            raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(sorted(faltantes))}")
    except Exception as exc:
        importacao.erros = [{"linha": None, "erro": f"Falha ao ler o arquivo: {exc}"}]
        importacao.finalizado_em = datetime.now(timezone.utc)
        db.commit()
        db.refresh(importacao)
        return importacao

    importacao.total_linhas = len(df)
    erros: list[dict] = []
    empresas_criadas = 0
    convenios_criados = 0
    vagas_criadas = 0
    vagas_atualizadas = 0
    empresas_para_reembedar: dict = {}
    vagas_para_reembedar: list = []

    for idx, serie in df.iterrows():
        linha_num = int(idx) + 2  # +1 (0-index) + 1 (linha de cabeçalho)
        row = serie.to_dict()
        try:
            with db.begin_nested():
                nome_empresa = _texto_ou_none(row.get("empresa"))
                if not nome_empresa:
                    raise ValueError("Nome da empresa vazio.")

                empresa, empresa_criada = get_or_create_empresa(
                    db,
                    nome=nome_empresa,
                    cnpj=row.get("cnpj"),
                    area=_texto_ou_none(row.get("area")),
                    segmento=_texto_ou_none(row.get("segmento")),
                    cidade=_texto_ou_none(row.get("cidade")),
                    uf=_texto_ou_none(row.get("uf")),
                )
                if empresa_criada:
                    empresas_criadas += 1

                convenio, convenio_criado = _find_or_create_convenio(db, empresa, row, fonte)
                if convenio_criado:
                    convenios_criados += 1

                vaga, vaga_criada = _find_or_create_vaga(db, empresa, convenio, row)
                if vaga_criada:
                    vagas_criadas += 1
                else:
                    vagas_atualizadas += 1

                empresas_para_reembedar[empresa.id] = empresa
                vagas_para_reembedar.append(vaga)
        except Exception as exc:
            erros.append(
                {
                    "linha": linha_num,
                    "dado": {k: row.get(k) for k in ("empresa", "cnpj", "vaga") if k in row},
                    "erro": str(exc),
                }
            )

    # Embeddings são gerados depois do loop (não linha a linha): uma
    # empresa aparece em várias linhas (uma por vaga) e seu texto
    # agrega os dados de todas as vagas dela — regenerar só uma vez
    # por empresa, já com todas as vagas gravadas, evita recalcular
    # o mesmo embedding repetidas vezes à toa. Falha do Ollama aqui
    # nunca derruba a importação (mesma resiliência de sempre).
    for vaga in vagas_para_reembedar:
        regenerate_vaga_embedding(db, vaga)
    for empresa in empresas_para_reembedar.values():
        regenerate_empresa_embedding(db, empresa)
    db.commit()

    importacao.sucesso = len(df) - len(erros)
    importacao.erros = erros
    importacao.relatorio = {
        "empresas_criadas": empresas_criadas,
        "convenios_criados": convenios_criados,
        "vagas_criadas": vagas_criadas,
        "vagas_atualizadas": vagas_atualizadas,
        "linhas_com_erro": len(erros),
    }
    importacao.finalizado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(importacao)
    return importacao
