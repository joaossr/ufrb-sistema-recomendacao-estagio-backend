"""
Roda o importador de PDF contra o arquivo REAL fornecido (não é um
teste sintético) — verifica o relatório e os dois casos de data
problemática que ele contém de verdade.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

BASE = "http://127.0.0.1:8000/api"
PDF_PATH = r"C:\Users\joaos\Downloads\TERMOS_FIRMADOS_-_PUBLICAR_SITE_COOPC_-_PADRONIZADO_-_02-09-2026.pdf"


def main():
    admin_login = requests.post(BASE + "/auth/login", json={"matricula": "admin.cetec", "password": "UfrbAdmin@2026Local!"})
    admin_login.raise_for_status()
    headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    print("== Importando o PDF real (1ª vez) ==")
    with open(PDF_PATH, "rb") as f:
        r = requests.post(BASE + "/admin/importacoes/convenios-pdf", headers=headers, files={"file": (
            "convenios.pdf", f, "application/pdf"
        )})
    print(r.status_code)
    resultado = r.json()
    print("total_linhas:", resultado["total_linhas"])
    print("sucesso:", resultado["sucesso"])
    print("relatorio:", resultado["relatorio"])
    print("erros:", resultado["erros"])
    assert r.status_code == 201
    assert resultado["total_linhas"] >= 560
    assert len(resultado["erros"]) == 0, "não esperava erro de linha nesta importação"

    print("\n== Conferindo os dois casos de data problematica ==")
    r = requests.get(BASE + "/admin/empresas", headers=headers)
    empresas = {e["nome_normalizado"]: e for e in r.json()}

    from app.services.importacao.empresas import normalize_company_name
    esg_norm = normalize_company_name("ESG AGRONEGOCIO LTDA")
    wabtec_norm = normalize_company_name("WABTEC BRASIL FABRICAÇÃO E MANUTENÇÃO DE EQUIPAMENTO LTDA")

    esg = empresas.get(esg_norm)
    wabtec = empresas.get(wabtec_norm)
    assert esg, f"nao achei empresa normalizada {esg_norm}"
    assert wabtec, f"nao achei empresa normalizada {wabtec_norm}"

    r = requests.get(BASE + f"/admin/empresas/{esg['id']}/convenios", headers=headers)
    conv = r.json()[0]
    print("ESG AGRONEGOCIO:", conv["data_fim_original"], "->", conv["status"])
    assert conv["data_fim_original"] == "03/102027"
    assert conv["status"] == "indeterminado"

    r = requests.get(BASE + f"/admin/empresas/{wabtec['id']}/convenios", headers=headers)
    conv = r.json()[0]
    print("WABTEC:", repr(conv["data_fim_original"]), "->", conv["data_fim"], conv["status"])
    # "27 /02/2029" tem um espaço perdido (ruído de extração do PDF),
    # mas 27/02 é uma data VÁLIDA (diferente de 29/02 num ano não
    # bissexto) — o parser corretamente remove o espaço e computa a
    # data normalmente, em vez de marcar como indeterminado à toa.
    assert conv["data_fim"] == "2029-02-27"
    assert conv["status"] == "vigente"

    print("\n== Conferindo duplicidade real: MUNICÍPIO DE CRUZ DAS ALMAS (2 convenios, 1 empresa) ==")
    muni_norm = normalize_company_name("MUNICÍPIO DE CRUZ DAS ALMAS")
    muni = empresas.get(muni_norm)
    assert muni, "nao achei Municipio de Cruz das Almas"
    r = requests.get(BASE + f"/admin/empresas/{muni['id']}/convenios", headers=headers)
    print("convenios de", muni["nome"], ":", len(r.json()))
    assert len(r.json()) == 2

    total_empresas_antes = len(empresas)

    print("\n== Reimportando o MESMO PDF (idempotencia: nao deve duplicar) ==")
    with open(PDF_PATH, "rb") as f:
        r = requests.post(BASE + "/admin/importacoes/convenios-pdf", headers=headers, files={"file": (
            "convenios.pdf", f, "application/pdf"
        )})
    resultado2 = r.json()
    print("relatorio (2a importacao):", resultado2["relatorio"])
    assert resultado2["relatorio"]["empresas_criadas"] == 0, "reimportar nao deveria criar empresa nova"
    assert resultado2["relatorio"]["convenios_criados"] == 0, "reimportar nao deveria criar convenio novo"
    assert resultado2["relatorio"]["convenios_atualizados"] == resultado["sucesso"]

    r = requests.get(BASE + "/admin/empresas", headers=headers)
    assert len(r.json()) == total_empresas_antes, "numero de empresas nao deveria mudar na reimportacao"

    print("\n== GET /admin/importacoes (historico) ==")
    r = requests.get(BASE + "/admin/importacoes", headers=headers)
    print("total de importacoes registradas:", len(r.json()))
    assert len(r.json()) >= 2

    print("\nTODOS OS TESTES PASSARAM (contra o arquivo real).")


if __name__ == "__main__":
    main()
