"""
Cadastro, login e /api/me — substitui o AuthService client-side do
frontend (SHA-256+salt em localStorage) por autenticação real: Argon2
para o hash da senha, JWT para a sessão. A migração do frontend para
consumir estes endpoints é a Fase 3.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_usuario
from app.core.security import create_access_token, hash_password, verify_password
from app.models.aluno import Aluno
from app.models.usuario import Usuario
from app.schemas.auth import CadastroRequest, LoginRequest, TokenResponse, UsuarioPublic
from app.services.auditoria.log import registrar as registrar_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/cadastro", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def cadastro(payload: CadastroRequest, db: Session = Depends(get_db)):
    matricula = payload.matricula.strip()
    email = payload.email.strip().lower()

    if matricula.lower() == settings.admin_matricula.lower():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um cadastro para esta matrícula.")

    if db.query(Usuario).filter(Usuario.matricula == matricula).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um cadastro para esta matrícula.")
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Já existe um cadastro para este e-mail institucional."
        )

    usuario = Usuario(matricula=matricula, email=email, senha_hash=hash_password(payload.password), role="aluno")
    db.add(usuario)
    try:
        db.flush()  # gera usuario.id sem finalizar a transação
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Matrícula ou e-mail já cadastrados.")

    # Perfil acadêmico já nasce com matrícula/e-mail preenchidos — nunca
    # pedidos de novo (mesma regra que já valia no frontend/js/authService.js).
    aluno = Aluno(usuario_id=usuario.id, matricula=matricula, email=email)
    db.add(aluno)
    db.commit()
    db.refresh(usuario)

    token = create_access_token(subject=str(usuario.id), role=usuario.role)
    return TokenResponse(access_token=token, usuario=UsuarioPublic.model_validate(usuario))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    matricula = payload.matricula.strip()
    usuario = db.query(Usuario).filter(Usuario.matricula == matricula).first()

    if usuario is None or not verify_password(payload.password, usuario.senha_hash):
        # Loga a tentativa mesmo sem usuário resolvido (usuario_id fica
        # None) — não guarda a senha, só a matrícula tentada, para dar
        # visibilidade de tentativas de acesso sem expor credenciais.
        registrar_log(
            db, usuario.id if usuario else None, "login_falha", "usuario",
            usuario.id if usuario else None, {"matricula_tentada": matricula},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Matrícula ou senha incorretos.")

    registrar_log(db, usuario.id, "login_sucesso", "usuario", usuario.id, {"matricula": matricula})
    db.commit()

    token = create_access_token(subject=str(usuario.id), role=usuario.role)
    return TokenResponse(access_token=token, usuario=UsuarioPublic.model_validate(usuario))


@router.get("/me", response_model=UsuarioPublic)
def me(usuario: Usuario = Depends(get_current_usuario)):
    return usuario
