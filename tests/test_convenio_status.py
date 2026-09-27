"""
Testes puros (sem banco) do tratamento determinístico de datas de
convênio (Fase 5 / passo 13). Os casos malformados aqui são os
mesmos encontrados de verdade no PDF de convênios da UFRB durante a
validação manual da Fase 5 (ver README) — não são hipotéticos.
"""

from datetime import date

from app.services.importacao.convenio_status import (
    compute_convenio_status,
    parse_and_compute_status,
    parse_brazilian_date,
)


def test_data_valida_e_parseada_corretamente():
    assert parse_brazilian_date("15/03/2027") == date(2027, 3, 15)


def test_data_com_espaco_interno_e_tolerada():
    """Ruído de extração de PDF (espaço perdido) — não é ambiguidade
    do dado em si, então é normalizado antes de validar."""
    assert parse_brazilian_date("27 /02/2029") == date(2029, 2, 27)


def test_data_faltando_barra_vira_none():
    """Caso real do PDF da UFRB: barra faltando é AMBÍGUO (não dá pra
    saber se é 03/10/2027 ou outra coisa) — nunca adivinha, vira None."""
    assert parse_brazilian_date("03/102027") is None


def test_data_vazia_ou_none_vira_none():
    assert parse_brazilian_date(None) is None
    assert parse_brazilian_date("") is None


def test_data_com_dia_mes_invalidos_vira_none():
    assert parse_brazilian_date("31/02/2027") is None  # fevereiro não tem dia 31
    assert parse_brazilian_date("15/13/2027") is None  # mês 13 não existe


def test_status_vencido_quando_data_fim_no_passado():
    hoje = date(2026, 9, 26)
    assert compute_convenio_status(date(2020, 1, 1), hoje=hoje) == "vencido"


def test_status_vigente_quando_data_fim_no_futuro_ou_hoje():
    hoje = date(2026, 9, 26)
    assert compute_convenio_status(date(2027, 1, 1), hoje=hoje) == "vigente"
    assert compute_convenio_status(hoje, hoje=hoje) == "vigente"


def test_status_indeterminado_quando_sem_data_fim():
    assert compute_convenio_status(None) == "indeterminado"


def test_parse_and_compute_status_junta_os_dois_passos():
    hoje = date(2026, 9, 26)
    data_fim, status = parse_and_compute_status("20/05/2027", hoje=hoje)
    assert data_fim == date(2027, 5, 20)
    assert status == "vigente"

    data_fim, status = parse_and_compute_status("dado incompreensível", hoje=hoje)
    assert data_fim is None
    assert status == "indeterminado"
