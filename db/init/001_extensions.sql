-- Roda automaticamente na primeira subida do container (pasta montada em
-- /docker-entrypoint-initdb.d). Idempotente: usa IF NOT EXISTS de propósito,
-- já que o Postgres só executa este diretório quando o volume de dados
-- está vazio, mas mantemos a guarda para reruns manuais.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
