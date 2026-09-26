"""
Ponto de entrada da API. Fase 1: só o router de health check. Cada fase
seguinte adiciona seu próprio router aqui (auth, perfil, lattes,
empresas, vagas, recomendacoes, admin) — nunca lógica de negócio
diretamente neste arquivo.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, auth, health

app = FastAPI(title="Sistema de Recomendação de Estágio — API")

# Fase 1: libera qualquer origem para facilitar o desenvolvimento local
# do frontend estático (aberto via file:// ou http.server em outra
# porta). Restringir a origens conhecidas antes de produção.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
