"""
Dependencies do FastAPI para autenticação/autorização — extrai o
usuário atual do JWT (Authorization: Bearer <token>) e expõe
`require_admin` para proteger rotas administrativas (passo 7: "Proteger
rotas administrativas").
"""

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.usuario import Usuario

# auto_error=False: sem isso, o HTTPBearer levanta 403 "Not authenticated"
# quando não há header nenhum — 401 é o status correto para "não
# autenticado" (403 fica reservado para "autenticado mas sem permissão",
# ver require_admin abaixo).
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_usuario(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        usuario_id = uuid.UUID(payload.get("sub", ""))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")

    return usuario


def require_admin(usuario: Usuario = Depends(get_current_usuario)) -> Usuario:
    if usuario.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao administrador.")
    return usuario
