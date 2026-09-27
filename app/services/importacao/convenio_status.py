"""
Tratamento DETERMINÍSTICO de datas de convênio (Fase 5 / passo 13).
Nada aqui usa o LLM — decidir se um convênio está vigente ou vencido é
responsabilidade do backend, sempre. Regras:

  - data_fim válida e anterior a hoje  -> "vencido"
  - data_fim válida e hoje ou depois   -> "vigente"
  - data_fim ausente ou inválida       -> "indeterminado"

Nunca "corrige" uma data problemática automaticamente — ela vira
"indeterminado" e fica disponível em `data_fim_original` para revisão
humana. Um valor problemático numa linha nunca derruba a importação
inteira (ver app/services/importacao/convenios_pdf.py).
"""

import re
from datetime import date

_DATE_PATTERN = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_ISO_DATE_PATTERN = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")


def parse_brazilian_date(raw: str | None) -> date | None:
    """Aceita SOMENTE o formato estrito DD/MM/AAAA com as duas barras
    no lugar certo. Qualquer outra coisa — incluindo os casos reais
    encontrados no PDF de convênios da UFRB: "03/102027" (falta uma
    barra) e "27 /02/2029" (espaço perdido na extração do PDF) —
    retorna None em vez de tentar adivinhar a correção. Espaços
    internos são removidos antes de validar (ruído de extração de
    PDF, não ambiguidade do dado em si — diferente de uma barra
    faltando, que É ambíguo e por isso não é "corrigido")."""
    if not raw:
        return None

    match = _DATE_PATTERN.match(re.sub(r"\s+", "", raw.strip()))
    if not match:
        return None

    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_iso_date(raw: str | None) -> date | None:
    """Formato AAAA-MM-DD (planilha de empresas/vagas, Fase 12) — mesma
    postura de `parse_brazilian_date`: só aceita o formato estrito,
    nunca tenta adivinhar uma data ambígua ou malformada."""
    if not raw:
        return None

    match = _ISO_DATE_PATTERN.match(raw.strip())
    if not match:
        return None

    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def compute_convenio_status(data_fim: date | None, hoje: date | None = None) -> str:
    if data_fim is None:
        return "indeterminado"
    hoje = hoje or date.today()
    return "vencido" if data_fim < hoje else "vigente"


def parse_and_compute_status(raw_data_fim: str | None, hoje: date | None = None) -> tuple[date | None, str]:
    """Conveniência: faz os dois passos de uma vez, do jeito que o
    importador do PDF de convênios usa linha a linha (formato BR)."""
    data_fim = parse_brazilian_date(raw_data_fim)
    return data_fim, compute_convenio_status(data_fim, hoje)


def parse_and_compute_status_iso(raw_data_fim: str | None, hoje: date | None = None) -> tuple[date | None, str]:
    """Mesma conveniência de `parse_and_compute_status`, para a
    planilha de empresas/vagas (Fase 12), que traz datas em AAAA-MM-DD."""
    data_fim = parse_iso_date(raw_data_fim)
    return data_fim, compute_convenio_status(data_fim, hoje)
