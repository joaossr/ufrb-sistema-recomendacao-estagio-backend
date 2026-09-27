"""
Limpeza dos dados de teste de empresas/convênios/vagas/recomendações
(Fase 12) — pedido explícito do usuário antes de importar o arquivo
real de empresas/vagas. NUNCA apaga alunos/usuários (cadastros reais
de estudante não são "dado de teste de empresa"), nem `logs_auditoria`
(é o próprio histórico de auditoria — apagar destruiria o que ele
existe para preservar).

Ordem de exclusão (respeita as foreign keys):
  1. avaliacoes_humanas (referencia recomendacoes)
  2. recomendacoes (referencia alunos/empresas/vagas)
  3. embeddings de empresa/vaga (sem FK física, mas ficariam órfãos)
  4. vagas (referencia empresas/convenios)
  5. convenios (referencia empresas)
  6. empresas

Uso: python scripts/limpar_dados_teste_empresas.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.avaliacao_humana import AvaliacaoHumana
from app.models.embedding import Embedding
from app.models.empresa import Convenio, Empresa
from app.models.recomendacao import Recomendacao
from app.models.vaga import Vaga


def limpar():
    db = SessionLocal()
    try:
        n_avaliacoes = db.query(AvaliacaoHumana).delete()
        n_recomendacoes = db.query(Recomendacao).delete()
        n_embeddings = db.query(Embedding).filter(Embedding.entidade_tipo.in_(["empresa", "vaga"])).delete(
            synchronize_session=False
        )
        n_vagas = db.query(Vaga).delete()
        n_convenios = db.query(Convenio).delete()
        n_empresas = db.query(Empresa).delete()
        db.commit()

        print("Limpeza concluída:")
        print(f"  avaliacoes_humanas removidas: {n_avaliacoes}")
        print(f"  recomendacoes removidas:      {n_recomendacoes}")
        print(f"  embeddings (empresa/vaga):    {n_embeddings}")
        print(f"  vagas removidas:              {n_vagas}")
        print(f"  convenios removidos:          {n_convenios}")
        print(f"  empresas removidas:           {n_empresas}")
        print("Alunos, usuários e logs de auditoria NÃO foram tocados.")
    finally:
        db.close()


if __name__ == "__main__":
    limpar()
