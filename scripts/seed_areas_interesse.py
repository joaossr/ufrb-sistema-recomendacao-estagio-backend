"""
Popula `areas_interesse` com a mesma lista hoje hardcoded em
`frontend/js/ui.js` (INTEREST_AREAS_SEED) — mesma lógica do seed de
centros/cursos: o banco vira a fonte única de verdade a partir daqui.

Uso: python scripts/seed_areas_interesse.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models import AreaInteresse

AREAS = [
    "Computação", "Inteligência Artificial", "Machine Learning", "Ciência de Dados",
    "Engenharia de Software", "Desenvolvimento de Software", "Desenvolvimento Web",
    "Desenvolvimento Mobile", "Banco de Dados", "Redes", "Segurança da Informação",
    "Computação em Nuvem", "Internet das Coisas", "Automação", "Robótica", "Eletrônica",
    "Sistemas Embarcados", "Controle",
    "Engenharia", "Engenharia Civil", "Engenharia Mecânica", "Engenharia Elétrica",
    "Matemática", "Estatística", "Física", "Química",
    "Ciências Biológicas", "Biologia", "Biotecnologia", "Ecologia", "Biodiversidade",
    "Recursos Naturais",
    "Agronomia", "Agroecologia", "Produção Vegetal", "Fitotecnia", "Fitopatologia",
    "Entomologia", "Ciência do Solo", "Irrigação", "Recursos Hídricos", "Agroindústria",
    "Tecnologia de Alimentos",
    "Produção Animal", "Zootecnia", "Medicina Veterinária", "Reprodução Animal",
    "Nutrição Animal", "Sanidade Animal", "Saúde Animal", "Clínica Veterinária",
    "Engenharia de Pesca", "Aquicultura", "Recursos Pesqueiros", "Engenharia Florestal",
    "Manejo Florestal",
    "Conservação Ambiental", "Gestão Ambiental", "Ciências Ambientais", "Meio Ambiente",
    "Sustentabilidade",
    "Extensão Rural", "Desenvolvimento Rural", "Pesquisa", "Pesquisa Científica",
    "Extensão", "Inovação", "Desenvolvimento", "Gestão", "Administração", "Educação",
    "Ensino", "Saúde",
]


def seed():
    db = SessionLocal()
    try:
        existentes = {a.nome.lower() for a in db.query(AreaInteresse).all()}
        criadas = 0
        for nome in AREAS:
            if nome.lower() not in existentes:
                db.add(AreaInteresse(nome=nome))
                existentes.add(nome.lower())
                criadas += 1
        db.commit()
        total = db.query(AreaInteresse).count()
        print(f"OK: {criadas} áreas novas criadas, {total} no total.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
