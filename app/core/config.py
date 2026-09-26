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
    ollama_llm_model: str = "qwen3:8b"
    ollama_embed_model: str = "qwen3-embedding:0.6b-q8_0"
    embedding_dim: int = 1024

    jwt_secret_key: str = "troque-esta-chave-antes-de-usar-em-producao"
    jwt_expire_minutes: int = 60


settings = Settings()
