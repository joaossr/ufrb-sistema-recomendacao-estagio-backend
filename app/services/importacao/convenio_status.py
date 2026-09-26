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


def parse_brazilian_date(raw: str | None) -> date | None:
    """Aceita SOMENTE o formato estrito DD/MM/AAAA com as duas barras
    no lugar certo. Qualquer outra coisa — incluindo os casos
    conhecidos "03/102027" (falta uma barra) e "29/02/2029" (2029 não
    é bissexto) — retorna None em vez de tentar adivinhar a correção."""
    if not raw:
        return None

    match = _DATE_PATTERN.match(raw.strip())
    if not match:
        return None

    day, month, year = (int(part) for part in match.groups())
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
    importador de PDF/CSV vai usar linha a linha."""
    data_fim = parse_brazilian_date(raw_data_fim)
    return data_fim, compute_convenio_status(data_fim, hoje)
