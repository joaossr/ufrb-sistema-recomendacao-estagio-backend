"""
Leitura do XML do Currículo Lattes — porta para o backend a mesma
lógica que antes rodava no navegador (frontend/js/lattesParser.js),
seguindo a Fase 4: "O XML deve ser enviado ao backend, processado e
convertido para dados estruturados."

Nenhum dado é inventado: se uma informação não existe no arquivo, o
campo correspondente vem vazio/None — nunca um valor "chutado".

Confiança na extração (documentado por honestidade, não por enfeite):
  - Nome completo, ID Lattes, formação acadêmica, idiomas: alta —
    testados neste projeto contra XML sintético e real durante a
    migração do parser client-side.
  - Formações complementares: média — a tag FORMACAO-COMPLEMENTAR é
    bem estabelecida no schema do Lattes, mas os nomes exatos de
    atributo variam entre exportações; a busca abaixo é tolerante a
    isso (ver `_find_attr_contains`).
  - Projetos e experiências profissionais NÃO são extraídos aqui: o
    schema do Lattes para essas seções é significativamente mais
    variável (ATUACOES-PROFISSIONAIS, PROJETOS-DE-PESQUISA, etc.) e,
    sem um arquivo real para validar contra, a extração arriscaria
    ficar silenciosamente errada. Continuam sendo cadastrados
    manualmente (já funciona) até haver um arquivo de referência.
"""

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

LEVEL_LABELS = {
    "GRADUACAO": "Graduação",
    "ESPECIALIZACAO": "Especialização",
    "MESTRADO": "Mestrado",
    "DOUTORADO": "Doutorado",
    "POS-DOUTORADO": "Pós-Doutorado",
    "LIVRE-DOCENCIA": "Livre-Docência",
}

STATUS_LABELS = {
    "CONCLUIDO": "Concluído",
    "EM_ANDAMENTO": "Em andamento",
    "EM-ANDAMENTO": "Em andamento",
    "INTERROMPIDO": "Interrompido",
    "TRANCADO": "Trancado",
}

PROFICIENCY_LABELS = {
    "NADA": "Nada",
    "POUCO": "Pouco",
    "RAZOAVEL": "Razoavelmente",
    "RAZOAVELMENTE": "Razoavelmente",
    "BEM": "Bem",
}

LANGUAGE_NAMES = {
    "PT": "Português", "POR": "Português", "PORTUGUES": "Português",
    "EN": "Inglês", "ING": "Inglês", "INGLES": "Inglês",
    "ES": "Espanhol", "ESP": "Espanhol", "ESPANHOL": "Espanhol", "CASTELHANO": "Espanhol",
    "FR": "Francês", "FRA": "Francês", "FRANCES": "Francês",
    "DE": "Alemão", "ALE": "Alemão", "ALEMAO": "Alemão",
    "IT": "Italiano", "ITA": "Italiano", "ITALIANO": "Italiano",
    "JA": "Japonês", "JAP": "Japonês", "JAPONES": "Japonês",
    "ZH": "Mandarim", "CHI": "Mandarim", "MANDARIM": "Mandarim", "CHINES": "Mandarim",
    "NL": "Holandês", "HOLANDES": "Holandês",
    "RU": "Russo", "RUSSO": "Russo",
    "DL": "Língua Brasileira de Sinais (Libras)", "LIBRAS": "Língua Brasileira de Sinais (Libras)",
}


@dataclass
class LattesFormation:
    level_tag: str
    level: str
    course: str
    institution: str
    status: str = ""
    start_year: str = ""
    end_year: str = ""


@dataclass
class LattesLanguage:
    name: str
    reading: str = ""
    speaking: str = ""
    writing: str = ""
    comprehension: str = ""


@dataclass
class LattesComplementaryFormation:
    tipo: str = ""
    nome: str = ""
    instituicao: str = ""
    ano: str = ""


@dataclass
class LattesParseResult:
    ok: bool
    error: str = ""
    full_name: str = ""
    lattes_id: str = ""
    email: str = ""
    phone: str = ""
    formations: list[LattesFormation] = field(default_factory=list)
    languages: list[LattesLanguage] = field(default_factory=list)
    complementary_formations: list[LattesComplementaryFormation] = field(default_factory=list)


def _format_status(raw: str) -> str:
    if not raw:
        return ""
    return STATUS_LABELS.get(raw.upper(), raw)


def _format_proficiency(raw: str) -> str:
    if not raw:
        return ""
    upper = raw.upper()
    if upper in PROFICIENCY_LABELS:
        return PROFICIENCY_LABELS[upper]
    return raw[:1].upper() + raw[1:].lower()


def _format_language_name(raw: str) -> str:
    if not raw:
        return ""
    trimmed = raw.strip()
    upper = trimmed.upper()
    if upper in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[upper]
    return trimmed[:1].upper() + trimmed[1:].lower()


def _find_attr(element: ET.Element, names: list[str]) -> str:
    for name in names:
        value = element.get(name)
        if value:
            return value.strip()
    return ""


def _find_attr_contains(element: ET.Element, parts: list[str]) -> str:
    """Casa por SUBSTRING no nome do atributo — o Lattes varia o nome
    exato entre exportações/versões (ver mesmo raciocínio no antigo
    lattesParser.js do frontend)."""
    for attr_name, attr_value in element.attrib.items():
        if not attr_value or not attr_value.strip():
            continue
        upper_name = attr_name.upper()
        if any(part in upper_name for part in parts):
            return attr_value.strip()
    return ""


def _find_any_attribute(root: ET.Element, name_contains: list[str]) -> str:
    for element in root.iter():
        for attr_name, attr_value in element.attrib.items():
            if not attr_value or not attr_value.strip():
                continue
            upper_name = attr_name.upper()
            if any(part in upper_name for part in name_contains):
                return attr_value.strip()
    return ""


def _extract_phone(root: ET.Element) -> str:
    ddd = _find_any_attribute(root, ["DDD-TELEFONE-COMERCIAL", "DDD-CELULAR"])
    number = _find_any_attribute(root, ["TELEFONE-COMERCIAL", "TELEFONE-CELULAR", "NUMERO-DO-CELULAR"])
    if ddd and number:
        return f"({ddd}) {number}"
    return number or ""


def _find_first(root: ET.Element, tags: list[str]) -> ET.Element | None:
    for tag in tags:
        found = root.find(f".//{tag}")
        if found is not None:
            return found
    return None


def parse_lattes_xml(xml_bytes: bytes) -> LattesParseResult:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return LattesParseResult(ok=False, error="O arquivo selecionado não é um XML válido.")

    if "CURRICULO" not in root.tag.upper() and "CURRICULOVITAE" not in root.tag.upper().replace("-", ""):
        return LattesParseResult(
            ok=False, error="Este arquivo não parece ser um Currículo Lattes exportado em XML."
        )

    dados_gerais = _find_first(root, ["DADOS-GERAIS"])
    full_name = _find_attr(root, ["NOME-COMPLETO"]) or (
        _find_attr(dados_gerais, ["NOME-COMPLETO"]) if dados_gerais is not None else ""
    )
    lattes_id = _find_attr(root, ["NUMERO-IDENTIFICADOR"])
    email = _find_any_attribute(root, ["EMAIL", "E-MAIL"])
    phone = _extract_phone(root)

    formations: list[LattesFormation] = []
    formation_wrapper = _find_first(root, ["FORMACAO-ACADEMICA-TITULACAO"])
    if formation_wrapper is not None:
        for el in formation_wrapper:
            tag = el.tag.upper()
            level_label = LEVEL_LABELS.get(tag)
            if not level_label:
                continue

            course = _find_attr(el, ["NOME-CURSO"])
            institution = _find_attr(el, ["NOME-INSTITUICAO"]) or _find_attr(el, ["NOME-ORGAO"])
            if not course and not institution:
                continue

            formations.append(
                LattesFormation(
                    level_tag=tag,
                    level=level_label,
                    course=course or "Não informado no arquivo",
                    institution=institution or "Não informada no arquivo",
                    status=_format_status(_find_attr(el, ["STATUS-DO-CURSO"])),
                    start_year=_find_attr(el, ["ANO-DE-INICIO"]),
                    end_year=_find_attr(el, ["ANO-DE-CONCLUSAO"]),
                )
            )

    languages: list[LattesLanguage] = []
    languages_wrapper = _find_first(root, ["IDIOMAS"])
    if languages_wrapper is not None:
        for el in languages_wrapper:
            raw_name = _find_attr(el, ["NOME-DO-IDIOMA", "DESCRICAO-DO-IDIOMA"]) or _find_attr_contains(
                el, ["IDIOMA"]
            )
            if not raw_name:
                continue
            languages.append(
                LattesLanguage(
                    name=_format_language_name(raw_name),
                    reading=_format_proficiency(_find_attr_contains(el, ["LEITURA"])),
                    speaking=_format_proficiency(_find_attr_contains(el, ["FALA"])),
                    writing=_format_proficiency(_find_attr_contains(el, ["ESCRIT", "ESCREV"])),
                    comprehension=_format_proficiency(_find_attr_contains(el, ["COMPREEN", "ENTEND"])),
                )
            )

    complementary: list[LattesComplementaryFormation] = []
    complementary_wrapper = _find_first(root, ["FORMACAO-COMPLEMENTAR"])
    if complementary_wrapper is not None:
        for el in complementary_wrapper:
            nome = _find_attr_contains(el, ["NOME-DO-CURSO", "NOME-CURSO"])
            if not nome:
                continue
            complementary.append(
                LattesComplementaryFormation(
                    tipo=el.tag.replace("FORMACAO-COMPLEMENTAR-", "").replace("-", " ").title(),
                    nome=nome,
                    instituicao=_find_attr_contains(el, ["NOME-DA-INSTITUICAO", "NOME-INSTITUICAO"]),
                    ano=_find_attr_contains(el, ["ANO-DE-TERMINO", "ANO-DE-INICIO"]),
                )
            )

    if not full_name and not lattes_id and not formations:
        return LattesParseResult(
            ok=False, error="Não foi possível localizar nome, ID Lattes ou formação acadêmica neste arquivo."
        )

    return LattesParseResult(
        ok=True,
        full_name=full_name,
        lattes_id=lattes_id,
        email=email,
        phone=phone,
        formations=formations,
        languages=languages,
        complementary_formations=complementary,
    )
