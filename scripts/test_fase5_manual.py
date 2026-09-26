"""Verificação manual da Fase 5 (empresas/convênios + tratamento de datas)."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from app.services.importacao.convenio_status import compute_convenio_status, parse_brazilian_date
from app.services.importacao.empresas import normalize_cnpj, normalize_company_name

BASE = "http://127.0.0.1:8000/api"


def test_date_parsing():
    print("== parse_brazilian_date ==")
    cases = [
        ("15/03/2027", date(2027, 3, 15)),
        ("03/102027", None),  # caso conhecido: falta uma barra
        ("29/02/2029", None),  # caso conhecido: 2029 não é bissexto
        ("29/02/2028", date(2028, 2, 29)),  # 2028 É bissexto — deve funcionar
        ("31/04/2025", None),  # abril não tem dia 31
        ("", None),
        (None, None),
        ("2027-03-15", None),  # formato ISO não é aceito (só DD/MM/AAAA)
    ]
    for raw, expected in cases:
        result = parse_brazilian_date(raw)
        status_ok = "OK" if result == expected else "FALHOU"
        print(f"  {status_ok}: parse_brazilian_date({raw!r}) = {result} (esperado {expected})")
        assert result == expected, f"parse_brazilian_date({raw!r}) retornou {result}, esperado {expected}"


def test_status_computation():
    print("\n== compute_convenio_status ==")
    hoje = date(2026, 9, 27)
    assert compute_convenio_status(date(2026, 1, 1), hoje) == "vencido"
    assert compute_convenio_status(date(2027, 1, 1), hoje) == "vigente"
    assert compute_convenio_status(hoje, hoje) == "vigente"  # hoje mesmo -> vigente (regra: "hoje ou depois")
    assert compute_convenio_status(None, hoje) == "indeterminado"
    print("  OK: vencido/vigente/indeterminado calculados corretamente")


def test_company_normalization():
    print("\n== normalize_company_name / normalize_cnpj ==")
    assert normalize_company_name("Tech Solutions Ltda.") == "TECH SOLUTIONS"
    assert normalize_company_name("  Café   & Cia   S/A ") == "CAFE & CIA"
    assert normalize_company_name("Tech Solutions LTDA") == normalize_company_name("TECH SOLUTIONS S.A.")
    assert normalize_cnpj("12.345.678/0001-99") == "12345678000199"
    assert normalize_cnpj(None) is None
    print("  OK: nomes normalizados de forma consistente, CNPJ só com dígitos")


def test_api():
    print("\n== API: criar empresa/convênio (admin) ==")
    admin_login = requests.post(BASE + "/auth/login", json={"matricula": "admin.cetec", "password": "UfrbAdmin@2026Local!"})
    admin_login.raise_for_status()
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    aluno_login = requests.post(BASE + "/auth/login", json={"matricula": "2026333444", "password": "senha123"})
    aluno_headers = {"Authorization": f"Bearer {aluno_login.json()['access_token']}"}

    print("Aluno tentando criar empresa (esperado 403):")
    r = requests.post(BASE + "/admin/empresas", headers=aluno_headers, json={"nome": "Empresa Teste"})
    print(" ", r.status_code)
    assert r.status_code == 403

    print("Admin criando empresa:")
    r = requests.post(
        BASE + "/admin/empresas", headers=admin_headers, json={"nome": "TechBahia Soluções Ltda", "cnpj": "12.345.678/0001-99"}
    )
    print(" ", r.status_code, r.json())
    assert r.status_code == 201
    empresa = r.json()

    print("Criando a MESMA empresa de novo (mesmo CNPJ) — deve reaproveitar, não duplicar:")
    r = requests.post(BASE + "/admin/empresas", headers=admin_headers, json={"nome": "TechBahia Soluções LTDA.", "cnpj": "12345678000199"})
    assert r.status_code == 201
    assert r.json()["id"] == empresa["id"], "deveria ter reaproveitado a empresa existente pelo CNPJ"
    print("  OK: mesma empresa reaproveitada pelo CNPJ")

    print("Criando convênio com data vencida:")
    r = requests.post(
        BASE + f"/admin/empresas/{empresa['id']}/convenios",
        headers=admin_headers,
        json={"processo": "23212.001234/2020-11", "data_fim_original": "10/01/2020", "fonte": "teste-manual"},
    )
    print(" ", r.status_code, r.json())
    assert r.status_code == 201
    assert r.json()["status"] == "vencido"

    print("Criando convênio com data problemática (esperado indeterminado):")
    r = requests.post(
        BASE + f"/admin/empresas/{empresa['id']}/convenios",
        headers=admin_headers,
        json={"processo": "23212.009999/2021-00", "data_fim_original": "03/102027", "fonte": "teste-manual"},
    )
    print(" ", r.status_code, r.json())
    assert r.status_code == 201
    assert r.json()["status"] == "indeterminado"
    assert r.json()["data_fim_original"] == "03/102027"

    print("\nGET /admin/empresas/{id}/convenios:")
    r = requests.get(BASE + f"/admin/empresas/{empresa['id']}/convenios", headers=admin_headers)
    print(" ", r.status_code, len(r.json()), "convênios")
    assert len(r.json()) == 2

    print("\nTODOS OS TESTES PASSARAM.")


if __name__ == "__main__":
    test_date_parsing()
    test_status_computation()
    test_company_normalization()
    test_api()
