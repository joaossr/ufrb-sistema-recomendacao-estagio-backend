"""
O Lattes costuma registrar o nome do curso sem o prefixo de grau
("Ciências Exatas e Tecnológicas" em vez de "Bacharelado em Ciências
Exatas e Tecnológicas"), porque o grau já vem em outra tag (GRADUACAO).
Mesma lógica que existia em frontend/js/ui.js (findStandardCourseByName)
— agora centralizada aqui, já que a resolução de curso a partir do
texto do Lattes é responsabilidade do backend.
"""

import re

from sqlalchemy.orm import Session

from app.models.catalogo import Curso

_DEGREE_PREFIX = re.compile(r"^bacharelado( interdisciplinar)? em\s+", re.IGNORECASE)


def find_standard_course_by_name(db: Session, course_name: str) -> Curso | None:
    name = (course_name or "").strip().lower()
    if not name:
        return None

    match = db.query(Curso).filter(Curso.nome.ilike(name)).first()
    if match:
        return match

    for curso in db.query(Curso).all():
        if _DEGREE_PREFIX.sub("", curso.nome.lower()) == name:
            return curso
    return None
