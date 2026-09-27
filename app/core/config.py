"""
Configuração central do backend, lida do ambiente (.env). Nenhum outro
módulo deve ler variáveis de ambiente diretamente — sempre importar
`settings` daqui, para manter um único ponto de verdade sobre a
configuração (facilita trocar de ambiente e documentar no TCC).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sistema_estagio"

    ollama_url: str = "http://localhost:11434"
    # qwen3:8b existe (baixado), mas em CPU-only nesta máquina é
    # impraticavelmente lento p/ uso síncrono (nem um prompt trivial
    # respondeu em minutos) — qwen3:4b como padrão local; trocar via
    # .env quando houver GPU funcional ou hardware mais forte.
    ollama_llm_model: str = "qwen3:4b"
    ollama_embed_model: str = "qwen3-embedding:0.6b"  # já é Q8_0 (única quantização publicada nesta tag)
    embedding_dim: int = 1024

    jwt_secret_key: str = "troque-esta-chave-antes-de-usar-em-producao"
    jwt_expire_minutes: int = 60

    # Bootstrap do usuário administrador (ver scripts/seed_admin.py) — o
    # admin NUNCA se cadastra pelo endpoint público de cadastro; só existe
    # se alguém com acesso a este .env rodar o script de seed.
    admin_matricula: str = "admin.cetec"
    admin_email: str = "admin@ufrb.edu.br"
    admin_password: str = "troque-esta-senha-antes-de-rodar-o-seed"


settings = Settings()
