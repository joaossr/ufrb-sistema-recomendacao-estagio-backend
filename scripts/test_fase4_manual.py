"""Verificação manual da Fase 4 (importação do Lattes no backend)."""

import requests

BASE = "http://127.0.0.1:8000/api"

XML = """<?xml version="1.0" encoding="UTF-8"?>
<CURRICULO-VITAE NOME-COMPLETO="Joana Teste Silva" NUMERO-IDENTIFICADOR="9988776655443322">
  <DADOS-GERAIS>
    <FORMACAO-ACADEMICA-TITULACAO>
      <GRADUACAO NOME-CURSO="Ciências Exatas e Tecnológicas" NOME-INSTITUICAO="Universidade Federal do Recôncavo da Bahia" STATUS-DO-CURSO="EM_ANDAMENTO" ANO-DE-INICIO="2021"/>
    </FORMACAO-ACADEMICA-TITULACAO>
    <IDIOMAS>
      <IDIOMA IDIOMA="EN" PROFICIENCIA-DE-LEITURA="BEM" PROFICIENCIA-DE-FALA="RAZOAVEL" PROFICIENCIA-DE-ESCRITA="RAZOAVEL" PROFICIENCIA-DE-COMPREENSAO="BEM"/>
    </IDIOMAS>
    <FORMACAO-COMPLEMENTAR>
      <FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO NOME-DO-CURSO="Introdução a Bancos de Dados Vetoriais" NOME-DA-INSTITUICAO="Coursera" ANO-DE-INICIO="2025" ANO-DE-TERMINO="2025"/>
    </FORMACAO-COMPLEMENTAR>
  </DADOS-GERAIS>
</CURRICULO-VITAE>"""


def main():
    login = requests.post(BASE + "/auth/login", json={"matricula": "2026333444", "password": "senha123"})
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("== POST /perfil/lattes/preview ==")
    files = {"file": ("lattes.xml", XML.encode("utf-8"), "text/xml")}
    r = requests.post(BASE + "/perfil/lattes/preview", headers=headers, files=files)
    print(r.status_code, r.json())
    assert r.status_code == 200
    preview = r.json()
    assert preview["full_name"] == "Joana Teste Silva"
    assert len(preview["formations"]) == 1
    assert len(preview["languages"]) == 1
    assert len(preview["complementary_formations"]) == 1

    print("\n== POST /perfil/lattes/preview com arquivo inválido (esperado 422) ==")
    files_bad = {"file": ("nota.txt", b"isto nao e um xml", "text/plain")}
    r = requests.post(BASE + "/perfil/lattes/preview", headers=headers, files=files_bad)
    print(r.status_code, r.json())
    assert r.status_code == 422

    print("\n== POST /perfil/lattes/confirmar ==")
    r = requests.post(
        BASE + "/perfil/lattes/confirmar",
        headers=headers,
        json={
            "full_name": preview["full_name"],
            "lattes_id": preview["lattes_id"],
            "chosen_formation": preview["formations"][0],
            "languages": preview["languages"],
            "complementary_formations": preview["complementary_formations"],
        },
    )
    print(r.status_code, r.json())
    assert r.status_code == 200
    body = r.json()
    assert body["course_matched"] is True
    assert body["perfil"]["course"] == "Bacharelado em Ciências Exatas e Tecnológicas"
    assert body["perfil"]["full_name"] == "Joana Teste Silva"
    assert len(body["perfil"]["languages"]) == 1

    print("\n== Confirmar de novo (idempotência: não deve duplicar formação complementar) ==")
    r = requests.post(
        BASE + "/perfil/lattes/confirmar",
        headers=headers,
        json={
            "full_name": preview["full_name"],
            "lattes_id": preview["lattes_id"],
            "chosen_formation": preview["formations"][0],
            "languages": preview["languages"],
            "complementary_formations": preview["complementary_formations"],
        },
    )
    assert r.status_code == 200

    print("\n== GET /perfil (email/matricula preservados, nunca sobrescritos) ==")
    r = requests.get(BASE + "/perfil", headers=headers)
    print(r.status_code, r.json())
    assert r.json()["email"] == "browser.teste@ufrb.edu.br"
    assert r.json()["registration_number"] == "2026333444"

    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    main()
