# Backend — Sistema de Recomendação de Estágio (UFRB)

API FastAPI que substitui o `localStorage` do frontend por PostgreSQL
+ pgvector, com Ollama/Qwen3 para a recomendação de estágios. Ver o
plano completo de migração (32 etapas) para o roadmap.

## Status: Fases 1 a 7 concluídas

- **Fase 1**: PostgreSQL + pgvector via Docker, schema completo (24 tabelas), seed de centros/cursos, `GET /api/health`.
- **Fase 2**: autenticação real (Argon2 + JWT) — `/api/auth/cadastro`, `/api/auth/login`, `/api/auth/me`. Conta admin só existe via `scripts/seed_admin.py`.
- **Fase 3**: CRUD completo de perfil/tecnologias/projetos/experiências/áreas de interesse.
- **Fase 4**: importação do Currículo Lattes (upload → prévia → confirmação), extrai formação/idiomas/formações complementares.
- **Fase 5**: empresas/convênios estruturados, tratamento determinístico de datas de convênio, importador do PDF de convênios da UFRB (validado contra arquivo real).
- **Fase 6**: CRUD de vagas.
- **Fase 7**: representação textual de perfil/empresa/vaga → embeddings via Ollama (`qwen3-embedding:0.6b`, 1024 dimensões) → busca semântica via pgvector (distância de cosseno, Top 20).

**Ainda não implementado**: importador da COOPC (falta arquivo de exemplo), regras objetivas + análise com Qwen3 + recomendações estruturadas (Fase 8), página de recomendações/prospecção (Fase 9), painel administrativo completo (Fase 10), auditoria/testes automatizados/avaliação científica (Fase 11).

## Pré-requisitos

- Docker Desktop instalado e rodando.
- Python 3.11+ (testado com 3.13).
- [Ollama](https://ollama.com) instalado, com os modelos baixados:
  ```bash
  ollama pull qwen3-embedding:0.6b
  ollama pull qwen3:8b
  ```

### ⚠️ Ollama + GPU NVIDIA: erro conhecido nesta máquina

Com a GPU (RTX 3050) habilitada, o Ollama 0.34.4 falha com:
```
CUDA error: device kernel image is invalid
```
Solução: rodar o Ollama forçado em modo CPU. No Windows, feche o app
do Ollama (ícone na bandeja) e suba o servidor manualmente com as
variáveis de ambiente abaixo (em uma sessão PowerShell, por exemplo):

```powershell
$env:OLLAMA_NO_GPU="1"; $env:OLLAMA_LLM_LIBRARY="cpu"; $env:CUDA_VISIBLE_DEVICES=""
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
```
Um modelo de embedding de 0.6B roda bem em CPU (resposta em ~1s). Se
quiser tornar isso permanente, defina essas variáveis como variáveis
de ambiente do usuário no Windows (Configurações → Variáveis de
Ambiente) — não fizemos isso automaticamente por ser uma mudança de
configuração do sistema.

## Como rodar

```bash
# 0. Entrar na pasta do backend (docker-compose.yml fica aqui dentro)
cd backend

# 1. Subir o Postgres com pgvector
docker compose up -d

# 2. Configurar o backend
cp .env.example .env
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# 3. Criar as tabelas
alembic upgrade head

# 4. Popular dados de referência
python scripts/seed_centros_cursos.py
python scripts/seed_areas_interesse.py
python scripts/seed_admin.py   # edite ADMIN_PASSWORD no .env antes

# 5. Subir a API (evite --reload: neste projeto ele fica instável
#    observando a pasta .venv/ — reinicie manualmente após editar código)
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 6. Testar (em outro terminal)
curl http://localhost:8000/api/health
```

Resposta esperada do passo 6: `{"status":"ok","database":"connected"}`.

Documentação interativa (Swagger): http://127.0.0.1:8000/docs — use
`POST /api/auth/login`, copie o `access_token`, clique em "Authorize"
e cole o token para testar rotas autenticadas manualmente.

## Estrutura

```
backend/
  app/
    main.py              # cria o FastAPI, inclui todos os routers
    core/
      config.py           # Settings (lê .env)
      database.py          # engine, sessão, Base declarativa
      security.py          # Argon2 + JWT
      deps.py               # get_current_usuario / get_current_aluno / require_admin
    models/                 # SQLAlchemy — 1 arquivo por domínio
    schemas/                # Pydantic
    routers/                # 1 arquivo por recurso (auth, perfil, tecnologias, projetos,
                             # experiencias, areas_interesse, catalogos, lattes, empresas,
                             # importacoes, vagas, busca_semantica, admin)
    services/
      lattes/                # parser.py, course_matching.py
      importacao/             # convenio_status.py, empresas.py, convenios_pdf.py
      ollama/                  # client.py — único ponto de chamada à API do Ollama
      embeddings/               # text_representation.py, service.py, search.py
      recomendacao/              # reservado para a Fase 8
  alembic/                  # migrations (schema inicial em versions/0001_initial_schema.py)
  scripts/
    seed_centros_cursos.py
    seed_areas_interesse.py
    seed_admin.py
    test_fase*_manual.py    # roteiros de verificação manual de cada fase (não é a suíte
                             # pytest da Fase 11 — rodam contra um servidor já no ar)
  docker-compose.yml        # dentro do próprio backend/, para ficar autocontido
```

## Próxima fase

Fase 8 — regras objetivas + análise de compatibilidade com Qwen3 +
persistência auditável da recomendação.
