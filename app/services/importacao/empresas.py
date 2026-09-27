"""
Identificação/deduplicação de empresas (Fase 5 / passo 11): prioriza
CNPJ; quando não existe, usa o nome normalizado. Nunca cria uma
empresa duplicada silenciosamente — ver `get_or_create_empresa`.
"""

import re
import unicodedata

from sqlalchemy.orm import Session

from app.models.empresa import Empresa

_CNPJ_DIGITS = re.compile(r"\D")
_COMPANY_SUFFIXES = re.compile(
    r"\b(LTDA|EIRELI|S\.?A\.?|ME|EPP|S/A|SA)\b\.?", re.IGNORECASE
)
_EXTRA_SPACE = re.compile(r"\s+")


def normalize_cnpj(cnpj: str | None) -> str | None:
    """Mantém só os dígitos — evita "12.345.678/0001-99" e
    "12345678000199" serem tratados como empresas diferentes."""
    if not cnpj:
        return None
    digits = _CNPJ_DIGITS.sub("", cnpj)
    return digits or None


def normalize_company_name(name: str) -> str:
    """Maiúsculas, sem acento, sem sufixo societário, espaços
    colapsados — só para efeito de COMPARAÇÃO (o nome original,
    `Empresa.nome`, nunca é alterado)."""
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    without_suffix = _COMPANY_SUFFIXES.sub("", without_accents)
    return _EXTRA_SPACE.sub(" ", without_suffix).strip().upper()


def get_or_create_empresa(
    db: Session,
    *,
    nome: str,
    cnpj: str | None = None,
    area: str | None = None,
    segmento: str | None = None,
    cidade: str | None = None,
    uf: str | None = None,
) -> tuple[Empresa, bool]:
    """Retorna (empresa, criada). Busca por CNPJ primeiro (identificador
    mais confiável); sem CNPJ, cai para o nome normalizado. Os campos
    extras (área/segmento/cidade/UF, Fase 12) só completam dado
    ausente — nunca sobrescrevem o que já existia numa reimportação."""
    cnpj_normalizado = normalize_cnpj(cnpj)

    def _completar_campos_ausentes(empresa: Empresa) -> None:
        if cnpj_normalizado and not empresa.cnpj:
            empresa.cnpj = cnpj_normalizado
        if area and not empresa.area:
            empresa.area = area
        if segmento and not empresa.segmento:
            empresa.segmento = segmento
        if cidade and not empresa.cidade:
            empresa.cidade = cidade
        if uf and not empresa.uf:
            empresa.uf = uf

    if cnpj_normalizado:
        existente = db.query(Empresa).filter(Empresa.cnpj == cnpj_normalizado).first()
        if existente:
            _completar_campos_ausentes(existente)
            return existente, False

    nome_normalizado = normalize_company_name(nome)
    existente = db.query(Empresa).filter(Empresa.nome_normalizado == nome_normalizado).first()
    if existente:
        _completar_campos_ausentes(existente)
        return existente, False

    empresa = Empresa(
        nome=nome.strip(),
        nome_normalizado=nome_normalizado,
        cnpj=cnpj_normalizado,
        area=area,
        segmento=segmento,
        cidade=cidade,
        uf=uf,
    )
    db.add(empresa)
    db.flush()
    return empresa, True
