# Backend — Sistema de Recomendação de Estágio (UFRB)

API FastAPI que substitui gradualmente o `localStorage` do frontend por
PostgreSQL + pgvector, e futuramente integra Ollama/Qwen3 para a
recomendação de estágios. Ver o plano completo de migração (32 etapas)
para o roadmap além da Fase 1.

## Fase 1 (atual): infraestrutura + banco + backend base

O que existe nesta fase: banco PostgreSQL com pgvector rodando via
Docker, schema completo (todas as tabelas do sistema, não só as usadas
agora), seed de centros/cursos e `GET /api/health` provando que a API
conversa com o banco. **Não há autenticação, CRUD de perfil, Lattes,
embeddings ou recomendação ainda** — isso vem nas fases seguintes.

## Pré-requisitos

- Docker Desktop instalado e rodando.
- Python 3.11+ (testado com 3.13).

## Como rodar

```bash
# 0. Entrar na pasta do backend (docker-compose.yml fica aqui dentro)
cd backend

# 1. Subir o Postgres com pgvector
docker compose up -d

# 2. Conferir que o container está saudável
docker compose ps

# 3. Conferir que as extensões foram criadas
docker compose exec db psql -U postgres -d sistema_estagio -c "SELECT extname FROM pg_extension;"

# 4. Configurar o backend
cp .env.example .env
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# 5. Criar as tabelas
alembic upgrade head

# 6. Popular centros e cursos
python scripts/seed_centros_cursos.py

# 7. Subir a API
uvicorn app.main:app --reload

# 8. Testar (em outro terminal)
curl http://localhost:8000/api/health
```

Resposta esperada do passo 8: `{"status":"ok","database":"connected"}`.

## Estrutura

```
backend/
  app/
    main.py          # cria o FastAPI, inclui routers
    core/
      config.py       # Settings (lê .env)
      database.py      # engine, sessão, Base declarativa
      security.py      # placeholder — Argon2/JWT chegam na Fase 2
    models/            # SQLAlchemy — 1 arquivo por domínio
    schemas/            # Pydantic (vazio nesta fase)
    routers/
      health.py         # GET /api/health
    services/           # pastas prontas para lattes/importacao/embeddings/ollama/recomendacao
  alembic/               # migrations versionadas (schema inicial em versions/0001_initial_schema.py)
  scripts/
    seed_centros_cursos.py
  docker-compose.yml     # dentro do próprio backend/, para ficar autocontido
```

## Próxima fase

Fase 2 — autenticação real (cadastro/login/`/api/me` com Argon2 + JWT,
separação aluno/admin), só depois que a Fase 1 estiver verificada.
