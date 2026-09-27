"""
Ponto de entrada da API. Cada fase adiciona seu próprio router aqui
(lattes, empresas, vagas, recomendacoes ainda faltam) — nunca lógica de
negócio diretamente neste arquivo.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    admin,
    areas_interesse,
    auth,
    busca_semantica,
    catalogos,
    empresas,
    experiencias,
    health,
    importacoes,
    lattes,
    perfil,
    projetos,
    recomendacoes,
    tecnologias,
    vagas,
)

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
app.include_router(perfil.router, prefix="/api")
app.include_router(tecnologias.router, prefix="/api")
app.include_router(projetos.router, prefix="/api")
app.include_router(experiencias.router, prefix="/api")
app.include_router(areas_interesse.router, prefix="/api")
app.include_router(catalogos.router, prefix="/api")
app.include_router(lattes.router, prefix="/api")
app.include_router(empresas.router, prefix="/api")
app.include_router(importacoes.router, prefix="/api")
app.include_router(vagas.router, prefix="/api")
app.include_router(busca_semantica.router, prefix="/api")
app.include_router(recomendacoes.router, prefix="/api")
