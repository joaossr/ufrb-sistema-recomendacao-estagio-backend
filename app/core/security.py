"""
Hash de senha (Argon2) e emissão/validação de JWT — centralizados
aqui, para que nenhum outro módulo implemente sua própria versão
(mesma regra de "um único ponto de verdade" usada em config.py).
"""

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        # Hash corrompido/algoritmo incompatível — trata como senha
        # incorreta em vez de derrubar a requisição com 500.
        return False


def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Levanta jwt.PyJWTError (ExpiredSignatureError, InvalidTokenError,
    ...) quando o token é inválido ou expirado — o router decide como
    traduzir isso em HTTP 401."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
