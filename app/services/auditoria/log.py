"""
Registro de auditoria (Fase 11 / passo 30). `registrar` só faz
`db.add` + `db.flush()` — nunca `db.commit()` sozinho, porque sempre é
chamado no meio de uma transação já em andamento no router (criar
empresa, mudar status de vaga, etc.); quem finaliza a transação é o
próprio router, exatamente como já acontece com o restante da
operação. Se o `flush()` falhar por algum motivo, isso deve derrubar a
operação inteira junto (auditoria não é "best effort" como as chamadas
ao Ollama — é dado estrutural, sempre determinístico).
"""

import uuid

from sqlalchemy.orm import Session

from app.models.log_auditoria import LogAuditoria


def registrar(
    db: Session,
    usuario_id: uuid.UUID | None,
    acao: str,
    entidade_tipo: str | None = None,
    entidade_id: uuid.UUID | None = None,
    detalhes: dict | None = None,
) -> LogAuditoria:
    log = LogAuditoria(
        usuario_id=usuario_id,
        acao=acao,
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        detalhes=detalhes,
    )
    db.add(log)
    db.flush()
    return log
