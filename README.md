# Backend — Sistema de Recomendação de Estágio (UFRB)

API FastAPI que substitui o `localStorage` do frontend por PostgreSQL
+ pgvector, com Ollama/Qwen3 para a recomendação de estágios. Ver o
plano completo de migração (32 etapas) para o roadmap.

## Status: Fases 1 a 9 concluídas, Fase 10 em andamento (backend pronto, frontend do admin ainda pendente)

- **Fase 1**: PostgreSQL + pgvector via Docker, schema completo (24 tabelas), seed de centros/cursos, `GET /api/health`.
- **Fase 2**: autenticação real (Argon2 + JWT) — `/api/auth/cadastro`, `/api/auth/login`, `/api/auth/me`. Conta admin só existe via `scripts/seed_admin.py`.
- **Fase 3**: CRUD completo de perfil/tecnologias/projetos/experiências/áreas de interesse.
- **Fase 4**: importação do Currículo Lattes (upload → prévia → confirmação), extrai formação/idiomas/formações complementares.
- **Fase 5**: empresas/convênios estruturados, tratamento determinístico de datas de convênio, importador do PDF de convênios da UFRB (validado contra arquivo real).
- **Fase 6**: CRUD de vagas.
- **Fase 7**: representação textual de perfil/empresa/vaga → embeddings via Ollama (`qwen3-embedding:0.6b`, 1024 dimensões) → busca semântica via pgvector (distância de cosseno, Top 20).
- **Fase 8**: regras objetivas (curso, status da vaga, prazo, convênio) filtrando ANTES do LLM → análise de compatibilidade com `qwen3:8b` (JSON estruturado: nível, índice, pontos compatíveis/parciais, lacunas, justificativa) → `Recomendacao` auditável no Postgres. Endpoint: `POST /api/perfil/recomendacoes/gerar`.
- **Fase 9**: `frontend/recomendacoes.html` (cards de vaga + prospecção, filtros por nível) consumindo a API de verdade; prospecção (empresa compatível sem vaga ativa — nunca chamada de "vaga disponível"); caminho inverso no admin (`POST /api/admin/vagas/{id}/recomendacoes/gerar` e `.../empresas/{id}/...`, aluno bloqueado dessas rotas).

- **Fase 10 (backend, em andamento)**: `GET /api/admin/alunos` (lista de estudantes reais com contagens e status de embedding) e `GET /api/admin/alunos/{id}` (detalhe completo, reaproveitando os serializers de perfil/tecnologias/projetos/experiências) — fecha a lacuna em que o admin só via os 3 perfis fictícios de `adminMockProfiles.js`. Catálogos públicos novos para autocomplete: `GET /api/tecnologias`, `GET /api/areas-projeto`, `GET /api/tipos-projeto` (mesmo padrão de `/centros`/`/cursos`/`/areas-interesse` desde a Fase 3). Testado em `scripts/test_fase10_manual.py`.

**Ainda não implementado**: importador da COOPC (falta arquivo de exemplo), reescrita de `admin.html`/`admin.js` para consumir os endpoints acima + UI para o caminho inverso (hoje só a API existe) + upload de PDF de convênios pelo painel, autocomplete do frontend (`tech-input`/`project-tech-input`/`exp-tech-input`) via `/api/tecnologias`, auditoria/testes automatizados/avaliação científica (Fase 11).

### Sobre o modelo de linguagem usado

`qwen3:8b` (o modelo do plano original) é o padrão — com a GPU (RTX
3050) rodando corretamente, ele responde em ~20s por análise. Numa
primeira tentativa sem GPU utilizável ele era impraticável (nem um
prompt trivial respondia em minutos); se você estiver numa máquina
sem GPU, troque `OLLAMA_LLM_MODEL` no `.env` para `qwen3:4b`
(~10-15s em CPU) — ambos os modelos já estão testados e funcionam.

Achado importante: o Qwen3 tem um modo de "pensar" (thinking) que, sem
ser desligado, consome todo o limite de tokens da resposta e nunca
chega a gerar o JSON final (resposta vazia). O cliente do Ollama
(`app/services/ollama/client.py`) já envia `"think": false` em toda
chamada de análise por causa disso.

## Pré-requisitos

- Docker Desktop instalado e rodando.
- Python 3.11+ (testado com 3.13).
- [Ollama](https://ollama.com) instalado, com os modelos baixados:
  ```bash
  ollama pull qwen3-embedding:0.6b
  ollama pull qwen3:8b
  ollama pull qwen3:4b   # alternativa mais rápida se não houver GPU utilizável
  ```

### GPU NVIDIA (RTX 3050): funciona, com uma ressalva

Na primeira tentativa, o Ollama 0.34.4 falhou com `CUDA error: device
kernel image is invalid` e o modo CPU foi usado como contorno (ver
histórico do git se precisar dos comandos). **Depois de um restart
limpo dos processos do Ollama, a GPU passou a funcionar normalmente**
com `qwen3:4b` e `qwen3:8b` — inclusive mais rápido que em CPU
(~10-20s por análise em vez de ~15-40s). Se o erro de CUDA voltar a
aparecer, mate todos os processos `ollama*`/`llama-server.exe` e suba
o Ollama de novo (`ollama serve` ou o app da bandeja) — no nosso caso
foi só isso que resolveu, não precisou forçar CPU permanentemente.

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
                             # importacoes, vagas, busca_semantica, admin, admin_alunos,
                             # recomendacoes)
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

Fase 10 (continuação) — reescrever `frontend/admin.html`/`js/admin.js`
para consumir `/api/admin/alunos` (estudantes reais em vez dos
fictícios), além de empresas/convênios/vagas já existentes, com upload
de PDF de convênios pelo painel, histórico de importações e UI para
o caminho inverso (hoje só a API existe). Depois, ligar o autocomplete
do formulário de perfil aos catálogos novos (`/api/tecnologias` etc.).
