"""
Verificação manual da Fase 12: importação de planilha CSV/XLSX de
empresas+convênios+vagas, geração de recomendações em lote pelo admin
(o aluno não gera mais a própria recomendação) e isolamento por
estudante. Assume que os 5 alunos de teste já foram criados
(scripts/criar_alunos_teste_fase12.py) e que o arquivo CSV real do
usuário está disponível no caminho indicado abaixo — ajuste
CSV_PATH se necessário.

IMPORTANTE: este script importa o arquivo de verdade (não é sintético)
— rode scripts/limpar_dados_teste_empresas.py antes se quiser começar
de um banco limpo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

BASE = "http://127.0.0.1:8000/api"
CSV_PATH = Path.home() / "Downloads" / "empresas_convenios_vagas_teste_50_empresas.csv"


def main():
    admin_login = requests.post(BASE + "/auth/login", json={"matricula": "admin.cetec", "password": "UfrbAdmin@2026Local!"})
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    print("== 1. Aluno NÃO tem mais rota própria para gerar recomendações (404) ==")
    aluno_login = requests.post(BASE + "/auth/login", json={"matricula": "2026500002", "password": "SenhaTeste@123"})
    assert aluno_login.status_code == 200, "rode scripts/criar_alunos_teste_fase12.py primeiro"
    aluno_headers = {"Authorization": f"Bearer {aluno_login.json()['access_token']}"}
    r = requests.post(BASE + "/perfil/recomendacoes/gerar", headers=aluno_headers)
    assert r.status_code == 404
    print("   OK: rota removida (404)")

    print("\n== 2. Importar a planilha CSV real de empresas/vagas ==")
    assert CSV_PATH.exists(), f"Arquivo não encontrado: {CSV_PATH}"
    with open(CSV_PATH, "rb") as f:
        r = requests.post(
            BASE + "/admin/importacoes/empresas-vagas",
            headers=admin_headers,
            files={"file": (CSV_PATH.name, f, "text/csv")},
        )
    assert r.status_code == 201, r.text
    importacao = r.json()
    print(f"   linhas: {importacao['total_linhas']} | sucesso: {importacao['sucesso']} | erros: {len(importacao['erros'])}")
    print(f"   relatorio: {importacao['relatorio']}")
    assert importacao["sucesso"] == importacao["total_linhas"], "esperava 0 erros na importação"

    print("\n== 3. Admin gera recomendações para TODOS os alunos cadastrados ==")
    r = requests.post(BASE + "/admin/recomendacoes/gerar", headers=admin_headers, timeout=1800)
    assert r.status_code == 200, r.text
    resumo = r.json()
    print(f"   alunos processados: {resumo['alunos_processados']} | com erro: {resumo['alunos_com_erro']}")
    print(f"   total recomendacoes: {resumo['total_recomendacoes_geradas']} | prospeccoes: {resumo['total_prospeccoes_geradas']}")
    for d in resumo["detalhes"]:
        print(f"   - {d['matricula']} ({d['nome_completo']}): {d['recomendacoes_geradas']} rec, {d['prospeccoes_geradas']} prosp, erro={d['erro']}")

    print("\n== 4. Cada aluno vê só as próprias recomendações ==")
    matriculas_teste = ["2026500001", "2026500002", "2026500003", "2026500004", "2026500005"]
    resultados_por_aluno = {}
    for matricula in matriculas_teste:
        login = requests.post(BASE + "/auth/login", json={"matricula": matricula, "password": "SenhaTeste@123"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        recs = requests.get(BASE + "/perfil/recomendacoes", headers=headers).json()
        resultados_por_aluno[matricula] = recs
        print(f"   {matricula}: {len(recs)} recomendações/prospecções")
        for rec in recs[:3]:
            titulo = rec["vaga"]["titulo"] if rec["vaga"] else "(prospecção, sem vaga)"
            print(f"      -> {rec['empresa']['nome']} | {titulo} | nível: {rec['nivel']}")

    print("\nTODOS OS PASSOS EXECUTADOS. Confira manualmente que cada aluno recebeu vagas da área correta.")


if __name__ == "__main__":
    main()
