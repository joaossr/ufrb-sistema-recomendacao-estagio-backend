"""
Regras determinísticas aplicadas DEPOIS da busca vetorial e ANTES do
Qwen3 (Fase 8 / passo 20). Tudo aqui é código puro — o LLM nunca
decide se uma vaga está ativa, se um convênio venceu ou se o aluno
pertence ao curso exigido.

Só filtra por um critério quando ele está de fato presente nos dados
(`vaga.cursos` vazio = sem exigência de curso, não é ausência de dado
tratada como reprovação). Semestre mínimo e localização preferida do
aluno NÃO existem como campos estruturados ainda no schema atual —
não filtramos por eles aqui para não inventar um critério que o
sistema não coleta; ver observação no schema quando esses campos
existirem.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.aluno import Aluno
from app.models.vaga import Vaga


@dataclass
class CandidatoElegivel:
    vaga: Vaga
    similaridade: float


def _curso_compativel(aluno: Aluno, vaga: Vaga) -> bool:
    if not vaga.cursos:
        return True  # vaga não restringe por curso
    if aluno.curso is None:
        return False
    return aluno.curso.nome in vaga.cursos


def _vaga_dentro_do_prazo(vaga: Vaga, hoje: date | None = None) -> bool:
    if vaga.data_fim is None:
        return True
    hoje = hoje or date.today()
    return vaga.data_fim >= hoje


def _convenio_ok(vaga: Vaga) -> bool:
    if vaga.convenio_id is None:
        return True  # vaga sem convênio vinculado — não filtra por isso
    convenio = vaga.convenio
    return convenio is not None and convenio.status != "vencido"


def vaga_elegivel(aluno: Aluno, vaga: Vaga) -> bool:
    return vaga.status == "ativa" and _curso_compativel(aluno, vaga) and _vaga_dentro_do_prazo(vaga) and _convenio_ok(vaga)


def filtrar_candidatos_elegiveis(
    db: Session, aluno: Aluno, candidatos: list[tuple], top_k: int | None = None
) -> list[CandidatoElegivel]:
    """`candidatos` = [(vaga_id, distancia)] vindo da busca vetorial
    (já ordenado, mais similar primeiro)."""
    elegiveis: list[CandidatoElegivel] = []
    for vaga_id, distancia in candidatos:
        vaga = db.get(Vaga, vaga_id)
        if vaga is None or not vaga_elegivel(aluno, vaga):
            continue
        elegiveis.append(CandidatoElegivel(vaga=vaga, similaridade=distancia))
        if top_k and len(elegiveis) >= top_k:
            break
    return elegiveis
