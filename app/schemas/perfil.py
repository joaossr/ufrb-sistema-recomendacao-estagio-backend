import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LanguageItem(BaseModel):
    name: str
    reading: str | None = ""
    speaking: str | None = ""
    writing: str | None = ""
    comprehension: str | None = ""


class PerfilOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str = ""
    lattes_id: str = ""
    course: str = ""
    course_id: int | None = None
    institution: str = ""
    education_level: str = ""
    education_status: str = ""
    education_start_year: str = ""
    education_end_year: str = ""
    email: str = ""
    phone: str = ""
    registration_number: str = ""
    linkedin_url: str = ""
    semester: str = ""
    expected_graduation: str = ""
    has_experience: bool = False
    tcc_status: str = "nao_iniciou"
    tcc_title: str = ""
    tcc_summary: str = ""
    tcc_advisor: str = ""
    tcc_keywords: list[str] = []
    languages: list[LanguageItem] = []
    updated_at: datetime


class PerfilUpdate(BaseModel):
    """Todos os campos são opcionais de propósito: o frontend salva
    parcialmente (mesma semântica de `saveProfile(changes)` no
    dataService.js atual) — só o que veio no corpo é alterado."""

    course_id: int | None = None
    linkedin_url: str | None = None
    semester: str | None = None
    expected_graduation: str | None = None
    has_experience: bool | None = None
    tcc_status: str | None = None
    tcc_title: str | None = None
    tcc_summary: str | None = None
    tcc_advisor: str | None = None
    tcc_keywords: list[str] | None = None
    languages: list[LanguageItem] | None = None

    # Hoje vêm da importação do Lattes, que ainda roda 100% no
    # navegador (a Fase 4 move esse processamento para o backend) —
    # aceitos aqui para o fluxo atual continuar funcionando sem regressão.
    full_name: str | None = None
    lattes_id: str | None = None
    institution: str | None = None
    education_level: str | None = None
    education_status: str | None = None
    education_start_year: str | None = None
    education_end_year: str | None = None
