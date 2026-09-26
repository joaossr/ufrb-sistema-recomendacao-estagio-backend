"""
Popula `centros` e `cursos` com os mesmos dados hoje hardcoded em
`frontend/js/ui.js` (ACADEMIC_CENTERS / UFRB_COURSES) — fonte única de
verdade passa a ser o banco a partir daqui; o frontend só troca de
fonte na Fase 3 (migração do DataService).

Uso: python scripts/seed_centros_cursos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models import Centro, Curso

CENTROS = [
    {"id": "CETEC", "nome": "CETEC — Centro de Ciências Exatas e Tecnológicas"},
    {"id": "CCAAB", "nome": "CCAAB — Centro de Ciências Agrárias, Ambientais e Biológicas"},
]

CURSOS = [
    ("CETEC", "Bacharelado em Ciências Exatas e Tecnológicas"),
    ("CETEC", "Engenharia de Computação"),
    ("CETEC", "Bacharelado em Matemática"),
    ("CETEC", "Engenharia Elétrica"),
    ("CETEC", "Engenharia Sanitária e Ambiental"),
    ("CETEC", "Engenharia Civil"),
    ("CETEC", "Engenharia Mecânica"),
    ("CETEC", "Bacharelado em Física"),
    ("CETEC", "Licenciatura em Matemática EaD"),
    ("CETEC", "Licenciatura em Computação EaD"),
    ("CETEC", "Licenciatura em Física EaD"),
    ("CCAAB", "Agroecologia"),
    ("CCAAB", "Agronomia"),
    ("CCAAB", "Biologia"),
    ("CCAAB", "Engenharia de Pesca"),
    ("CCAAB", "Engenharia Florestal"),
    ("CCAAB", "Gestão de Cooperativas"),
    ("CCAAB", "Gestão Ambiental"),
    ("CCAAB", "Interdisciplinar em Ciências Ambientais"),
    ("CCAAB", "Medicina Veterinária"),
    ("CCAAB", "Zootecnia"),
]


def seed():
    db = SessionLocal()
    try:
        for centro in CENTROS:
            if not db.get(Centro, centro["id"]):
                db.add(Centro(**centro))
        db.flush()

        existentes = {(c.centro_id, c.nome) for c in db.query(Curso).all()}
        criados = 0
        for centro_id, nome in CURSOS:
            if (centro_id, nome) not in existentes:
                db.add(Curso(centro_id=centro_id, nome=nome))
                criados += 1

        db.commit()
        total_cursos = db.query(Curso).count()
        print(f"OK: {len(CENTROS)} centros garantidos, {criados} cursos novos criados, {total_cursos} cursos no total.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
