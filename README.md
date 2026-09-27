# Backend — Sistema de Recomendação de Estágio (UFRB)

API FastAPI que substitui o `localStorage` do frontend por PostgreSQL
+ pgvector, com Ollama/Qwen3 para a recomendação de estágios. Ver o
plano completo de migração (32 etapas) para o roadmap.

## Status: Fases 1 a 11 concluídas + Fase 12 (fora do roteiro original, pedido do usuário)

- **Fase 1**: PostgreSQL + pgvector via Docker, schema completo (24 tabelas), seed de centros/cursos, `GET /api/health`.
- **Fase 2**: autenticação real (Argon2 + JWT) — `/api/auth/cadastro`, `/api/auth/login`, `/api/auth/me`. Conta admin só existe via `scripts/seed_admin.py`.
- **Fase 3**: CRUD completo de perfil/tecnologias/projetos/experiências/áreas de interesse.
- **Fase 4**: importação do Currículo Lattes (upload → prévia → confirmação), extrai formação/idiomas/formações complementares.
- **Fase 5**: empresas/convênios estruturados, tratamento determinístico de datas de convênio, importador do PDF de convênios da UFRB (validado contra arquivo real).
- **Fase 6**: CRUD de vagas.
- **Fase 7**: representação textual de perfil/empresa/vaga → embeddings via Ollama (`qwen3-embedding:0.6b`, 1024 dimensões) → busca semântica via pgvector (distância de cosseno, Top 20).
- **Fase 8**: regras objetivas (curso, status da vaga, prazo, convênio) filtrando ANTES do LLM → análise de compatibilidade com `qwen3:8b` (JSON estruturado: nível, índice, pontos compatíveis/parciais, lacunas, justificativa) → `Recomendacao` auditável no Postgres. Endpoint: `POST /api/perfil/recomendacoes/gerar`.
- **Fase 9**: `frontend/recomendacoes.html` (cards de vaga + prospecção, filtros por nível) consumindo a API de verdade; prospecção (empresa compatível sem vaga ativa — nunca chamada de "vaga disponível"); caminho inverso no admin (`POST /api/admin/vagas/{id}/recomendacoes/gerar` e `.../empresas/{id}/...`, aluno bloqueado dessas rotas).

- **Fase 10**: `GET /api/admin/alunos` (lista de estudantes reais com contagens e status de embedding) e `GET /api/admin/alunos/{id}` (detalhe completo, reaproveitando os serializers de perfil/tecnologias/projetos/experiências) — fecha a lacuna em que o admin só via os 3 perfis fictícios de `adminMockProfiles.js`. Catálogos públicos novos para autocomplete: `GET /api/tecnologias`, `GET /api/areas-projeto`, `GET /api/tipos-projeto` (mesmo padrão de `/centros`/`/cursos`/`/areas-interesse` desde a Fase 3). Testado em `scripts/test_fase10_manual.py`. `frontend/admin.html`/`admin.js` reescritos com 4 abas (Estudantes, Empresas & Convênios, Vagas, Importações) consumindo tudo isso de verdade: cadastro de empresa/convênio/vaga, upload do PDF de convênios pelo próprio painel, histórico de importações e disparo do caminho inverso (Fase 9) direto da lista de vagas/empresas. `js/adminMockProfiles.js` foi removido — não sobrou dado fictício em lugar nenhum do frontend.

- **Fase 11**: log de auditoria (`logs_auditoria` — criar/atualizar/excluir empresa/convênio/vaga, login com sucesso/falha sem gravar senha; `GET /api/admin/logs-auditoria`); avaliação humana das recomendações (`avaliacoes_humanas` — um admin registra se concorda com o `nivel` do Qwen3 e uma nota independente de 1 a 5, para comparar LLM x humano na dissertação; `POST/GET /api/admin/recomendacoes/{id}/avaliacoes`, `GET /api/admin/avaliacoes`); suíte de testes automatizados com **pytest** (`tests/`, 96 testes, banco Postgres de teste próprio e isolado — nunca toca no banco de desenvolvimento — Ollama sempre mockado de forma determinística, nunca chamado de verdade). Ver seção "Testes automatizados" abaixo.

- **Fase 12** (pedido explícito do usuário, fora das 32 etapas originais): o fluxo de recomendação passou a ser **centralizado no admin**.
  - Removida a rota `POST /perfil/recomendacoes/gerar` (o aluno nunca mais dispara a própria geração) e o botão "Gerar recomendações" da página `recomendacoes.html` — o aluno só visualiza (`GET /perfil/recomendacoes`).
  - Nova `POST /admin/recomendacoes/gerar`: processa **todos os alunos cadastrados** de uma vez (busca vetorial → regras → Qwen3, mesma lógica das Fases 8/9), isolado por aluno (erro num aluno nunca afeta os demais) — retorna um resumo por estudante. Botão equivalente no painel admin (aba Estudantes).
  - Novo importador de planilha CSV/XLSX de empresas+convênios+vagas combinados (`app/services/importacao/empresas_vagas_planilha.py`, endpoint `POST /admin/importacoes/empresas-vagas`) — cada linha é decomposta nos três registros corretos (nunca texto bruto), CNPJ identifica a empresa (evita duplicar/misturar), convênio/vaga repetidos numa reimportação são atualizados em vez de duplicados. `Empresa` ganhou colunas `area`/`segmento`/`cidade`/`uf` (Fase 12) para não perder dado que a planilha fornece e o PDF de convênios não tinha.
  - Banco de desenvolvimento limpo de empresas/vagas/convênios/recomendações de teste anteriores (`scripts/limpar_dados_teste_empresas.py`) — alunos/usuários e o log de auditoria não foram tocados.
  - 5 perfis de estudante de teste criados (`scripts/criar_alunos_teste_fase12.py`), um por área presente na planilha de teste do usuário: Medicina Veterinária, Engenharia de Computação, Zootecnia, Biologia, Engenharia Civil.
  - Testado: importação da planilha real do usuário (78 linhas, 0 erros — 50 empresas, 59 convênios, 78 vagas, todos os campos verificados linha a linha); suíte pytest com 100 testes (14 deles reescritos para o novo fluxo, incluindo um teste dedicado a isolamento entre alunos na geração em lote). **A geração de recomendações em lote com o Ollama real ainda não foi verificada de ponta a ponta nesta máquina** — bloqueada por RAM insuficiente no momento do teste (ver nota abaixo); o `scripts/test_fase12_manual.py` está pronto para rodar assim que houver memória livre.

**Ainda não implementado**: importador da COOPC (falta arquivo de exemplo — pode ter sido superado pelo importador de planilha da Fase 12, a confirmar com o usuário), autocomplete do formulário de perfil (`tech-input`/`project-tech-input`/`exp-tech-input` em `perfil.js`) via `/api/tecnologias`/`/api/areas-projeto`/`/api/tipos-projeto` (os endpoints já existem, só falta ligar o `Combobox` a eles).

### Nota: RAM insuficiente pode derrubar o Ollama silenciosamente

Se `generate_embedding`/`generate_completion` começarem a falhar com erros
tipo `CUDA_Host buffer`/`out of memory` mesmo com a GPU livre (`nvidia-smi`
mostrando VRAM disponível), o problema pode ser RAM do SISTEMA, não da
GPU — o Ollama também precisa de memória "host" (pinned) para transferir
dados para a GPU. Confira com:
```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object @{n='FreeGB';e={[math]::Round($_.FreePhysicalMemory/1MB,2)}}
```
Nesta máquina (8GB de RAM total), rodar Docker+Postgres+Ollama+qwen3:8b
junto com o navegador e o próprio Claude Code deixa pouquíssima margem —
feche processos pesados (o Gerenciador de Tarefas ordenado por memória
ajuda a achar o vilão) antes de rodar uma geração em lote.

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

## Testes automatizados (Fase 11 / passo 31)

```bash
pytest
```

100 testes, ~18s. Não precisa do servidor `uvicorn` no ar nem do
Ollama rodando — só do Postgres do `docker compose up -d` (o mesmo
container do banco de desenvolvimento). Na primeira execução de cada
sessão de pytest, `tests/conftest.py` recria do zero o banco
`sistema_estagio_test` (DROP+CREATE, extensões `pgcrypto`/`vector`,
`Base.metadata.create_all`) — nunca toca em `sistema_estagio`, o
banco de desenvolvimento. Cada teste roda dentro de uma transação com
SAVEPOINT que é desfeita ao final (`join_transaction_mode="create_savepoint"`),
garantindo isolamento total entre testes mesmo quando o código de
produção faz `db.commit()`.

Nenhum teste chama o Ollama de verdade: `generate_embedding` e
`generate_completion` são sempre monkeypatchados (fixture
`mock_ollama`) para respostas determinísticas. Isso testa a
ORQUESTRAÇÃO do pipeline (regras de elegibilidade, prospecção,
caminho inverso, auditoria) — a qualidade da resposta do LLM em si já
foi validada manualmente contra o Ollama real nas Fases 7-9 (ver
`scripts/test_fase*_manual.py`) e é o que a avaliação humana da Fase
11 (`avaliacoes_humanas`) mede continuamente daqui pra frente.

Organização em `tests/`:
- `test_convenio_status.py`, `test_regras.py`, `test_analise.py` — lógica pura, sem banco.
- `test_auth.py`, `test_perfil.py`, `test_catalogos.py`, `test_admin_alunos.py`, `test_admin_empresas_vagas.py`, `test_importacao_pdf.py` — integração via `TestClient`, isolamento entre contas de aluno é testado explicitamente.
- `test_recomendacoes_pipeline.py` — pipeline completo Fase 8/9 fim-a-fim (regras + LLM mockado + persistência auditável).

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
                             # recomendacoes, avaliacoes, auditoria)
    services/
      lattes/                # parser.py, course_matching.py
      importacao/             # convenio_status.py, empresas.py, convenios_pdf.py, empresas_vagas_planilha.py (CSV/XLSX)
      ollama/                  # client.py — único ponto de chamada à API do Ollama
      embeddings/               # text_representation.py, service.py, search.py
      recomendacao/              # regras.py, analise.py, pipeline.py, prospeccao.py, caminho_inverso.py
      auditoria/                 # log.py — único ponto que grava em logs_auditoria
  alembic/                  # migrations (schema inicial em versions/0001_initial_schema.py)
  scripts/
    seed_centros_cursos.py
    seed_areas_interesse.py
    seed_admin.py
    test_fase*_manual.py    # roteiros de verificação manual de cada fase (não é a suíte
                             # pytest da Fase 11 — rodam contra um servidor já no ar)
  tests/                    # suíte pytest (Fase 11 / passo 31) — ver seção acima
  docker-compose.yml        # dentro do próprio backend/, para ficar autocontido
```

## Próxima fase

Não há próxima fase do roteiro original de 32 passos — as 11 fases
estão concluídas, e a Fase 12 (fluxo centralizado no admin + planilha
de empresas/vagas) atende um pedido explícito posterior do usuário.
Pendências imediatas:

- **Verificar a geração em lote com o Ollama real nesta máquina**
  (bloqueada por RAM insuficiente no momento da implementação — ver
  nota acima). Rodar `python scripts/test_fase12_manual.py` assim que
  houver memória livre e conferir manualmente no `admin.html` que cada
  um dos 5 alunos de teste recebeu recomendações da área certa.
- Ligar o autocomplete do formulário de perfil (`tech-input`,
  `project-tech-input`, `exp-tech-input` em `frontend/js/perfil.js`)
  aos catálogos `/api/tecnologias`/`/api/areas-projeto`/`/api/tipos-projeto`
  via `Combobox.attach` (passo 28) — os endpoints já existem desde a
  Fase 10, só falta o frontend consumir.
- Confirmar com o usuário se o importador de planilha da Fase 12
  cobre o que ele esperava do "importador da COOPC", ou se a COOPC
  ainda precisa de um formato próprio.
- Usar `avaliacoes_humanas` de verdade (avaliar uma amostra de
  recomendações reais) para o capítulo de avaliação do TCC.
