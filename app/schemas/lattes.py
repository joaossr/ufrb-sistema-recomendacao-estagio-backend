from pydantic import BaseModel

from app.schemas.perfil import LanguageItem, PerfilOut


class LattesFormationOut(BaseModel):
    level_tag: str
    level: str
    course: str
    institution: str
    status: str = ""
    start_year: str = ""
    end_year: str = ""


class LattesComplementaryFormationOut(BaseModel):
    tipo: str = ""
    nome: str = ""
    instituicao: str = ""
    ano: str = ""


class LattesPreviewOut(BaseModel):
    full_name: str = ""
    lattes_id: str = ""
    formations: list[LattesFormationOut] = []
    languages: list[LanguageItem] = []
    complementary_formations: list[LattesComplementaryFormationOut] = []


class LattesConfirmRequest(BaseModel):
    full_name: str = ""
    lattes_id: str = ""
    chosen_formation: LattesFormationOut | None = None
    languages: list[LanguageItem] = []
    complementary_formations: list[LattesComplementaryFormationOut] = []


class LattesConfirmResponse(BaseModel):
    perfil: PerfilOut
    course_matched: bool
