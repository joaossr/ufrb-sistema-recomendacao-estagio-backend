"""
Cria 5 perfis de estudante de teste (Fase 12), um por área presente no
arquivo de empresas/vagas fornecido pelo usuário: Medicina Veterinária,
Engenharia de Computação, Zootecnia, Biologia e Engenharia Civil.
Pedido explícito do usuário para testar a geração de recomendações em
lote contra dados reais de empresas/vagas — nenhuma empresa/vaga é
criada aqui, só os estudantes.

As tecnologias/conhecimentos de cada perfil vêm do próprio vocabulário
da planilha de vagas (coluna "tecnologias"/"requisitos" de cada área),
não são inventadas: servem para o perfil ter alguma correspondência
textual real com as vagas da mesma área ao gerar as recomendações.

Uso: python scripts/criar_alunos_teste_fase12.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

BASE = "http://127.0.0.1:8000/api"
SENHA = "SenhaTeste@123"

PERFIS = [
    {
        "matricula": "2026500001",
        "email": "teste.vet@ufrb.edu.br",
        "nome_completo": "Aluno Teste — Medicina Veterinária",
        "curso": "Medicina Veterinária",
        "semestre": "6",
        "tecnologias": ["Semiologia", "Clínica de Pequenos Animais", "Prontuário eletrônico", "Excel"],
        "area_interesse": "Medicina Veterinária",
    },
    {
        "matricula": "2026500002",
        "email": "teste.computacao@ufrb.edu.br",
        "nome_completo": "Aluno Teste — Engenharia de Computação",
        "curso": "Engenharia de Computação",
        "semestre": "7",
        "tecnologias": ["Python", "SQL", "Git", "FastAPI", "PostgreSQL"],
        "area_interesse": "Engenharia de Computação",
    },
    {
        "matricula": "2026500003",
        "email": "teste.zootecnia@ufrb.edu.br",
        "nome_completo": "Aluno Teste — Zootecnia",
        "curso": "Zootecnia",
        "semestre": "5",
        "tecnologias": ["Nutrição Animal", "Manejo de rebanhos", "Formulação de dietas", "Excel"],
        "area_interesse": "Zootecnia",
    },
    {
        "matricula": "2026500004",
        "email": "teste.biologia@ufrb.edu.br",
        "nome_completo": "Aluno Teste — Biologia",
        "curso": "Biologia",
        "semestre": "6",
        "tecnologias": ["Ecologia", "QGIS", "Identificação de espécies", "Excel"],
        "area_interesse": "Biologia",
    },
    {
        "matricula": "2026500005",
        "email": "teste.civil@ufrb.edu.br",
        "nome_completo": "Aluno Teste — Engenharia Civil",
        "curso": "Engenharia Civil",
        "semestre": "8",
        "tecnologias": ["AutoCAD", "Revit", "Orçamento", "Excel"],
        "area_interesse": "Engenharia Civil",
    },
]


def main():
    admin_login = requests.post(BASE + "/auth/login", json={"matricula": "admin.cetec", "password": "UfrbAdmin@2026Local!"})
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    cursos = {c["nome"]: c["id"] for c in requests.get(BASE + "/cursos").json()}

    for perfil in PERFIS:
        curso_id = cursos.get(perfil["curso"])
        if curso_id is None:
            print(f"AVISO: curso '{perfil['curso']}' não encontrado no catálogo — pulando {perfil['matricula']}.")
            continue

        r = requests.post(
            BASE + "/auth/cadastro",
            json={"matricula": perfil["matricula"], "email": perfil["email"], "password": SENHA},
        )
        if r.status_code == 409:
            print(f"Já existe: {perfil['matricula']} ({perfil['nome_completo']}) — pulando cadastro, só ajustando perfil.")
            login = requests.post(BASE + "/auth/login", json={"matricula": perfil["matricula"], "password": SENHA})
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        elif r.status_code == 201:
            headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
            print(f"Criado: {perfil['matricula']} ({perfil['nome_completo']})")
        else:
            print(f"ERRO ao cadastrar {perfil['matricula']}: {r.status_code} {r.text}")
            continue

        r = requests.put(
            BASE + "/perfil",
            headers=headers,
            json={"full_name": perfil["nome_completo"], "course_id": curso_id, "semester": perfil["semestre"]},
        )
        assert r.status_code == 200, r.text

        tecnologias_existentes = {t["name"] for t in requests.get(BASE + "/perfil/tecnologias", headers=headers).json()}
        for nome_tec in perfil["tecnologias"]:
            if nome_tec in tecnologias_existentes:
                continue
            requests.post(BASE + "/perfil/tecnologias", headers=headers, json={"name": nome_tec, "level": "Intermediário"})

        requests.put(BASE + "/perfil/areas-interesse", headers=headers, json={"areas": [perfil["area_interesse"]]})

        print(f"  -> curso: {perfil['curso']} | tecnologias: {perfil['tecnologias']}")

    print("\nConcluído. Verifique em admin.html -> aba Estudantes.")


if __name__ == "__main__":
    main()
