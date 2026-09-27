"""
Serviço centralizado de comunicação com o Ollama (Fase 7 / passo 17).
Nenhum outro módulo deve chamar a API do Ollama diretamente — sempre
importar `OllamaClient` daqui, para que trocar de modelo, ajustar
timeout ou lidar com indisponibilidade fique num único lugar.

Ambiente desta máquina (registrado aqui por importância prática): o
Ollama com aceleração de GPU (RTX 3050) crasha com
"CUDA error: device kernel image is invalid" nesta combinação de
driver/Ollama — rodando em modo CPU (OLLAMA_NO_GPU=1) funciona
normalmente. Ver README para o comando de iniciar o servidor assim.
"""

import httpx

from app.core.config import settings


class OllamaError(Exception):
    """Erro de comunicação com o Ollama — indisponível, timeout, ou
    resposta inesperada. Quem chama decide como degradar (ex.: manter
    o embedding antigo em vez de falhar a requisição inteira)."""


def generate_embedding(text: str) -> list[float]:
    try:
        response = httpx.post(
            f"{settings.ollama_url}/api/embed",
            json={"model": settings.ollama_embed_model, "input": text},
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OllamaError(f"Falha ao gerar embedding: {exc}") from exc

    data = response.json()
    if "error" in data:
        raise OllamaError(f"Ollama retornou erro: {data['error']}")

    try:
        return data["embeddings"][0]
    except (KeyError, IndexError) as exc:
        raise OllamaError(f"Resposta inesperada do Ollama: {data}") from exc


def generate_completion(prompt: str, system: str | None = None) -> str:
    """Reservado para a Fase 8 (análise de compatibilidade com Qwen3)
    — nenhum endpoint chama isto ainda."""
    payload = {"model": settings.ollama_llm_model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system

    try:
        response = httpx.post(f"{settings.ollama_url}/api/generate", json=payload, timeout=120.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OllamaError(f"Falha ao gerar resposta do LLM: {exc}") from exc

    data = response.json()
    if "error" in data:
        raise OllamaError(f"Ollama retornou erro: {data['error']}")
    return data.get("response", "")
