"""
Análise detalhada de compatibilidade com o Qwen3 (Fase 8 / passos
21-22). Só roda DEPOIS da busca vetorial + regras objetivas — nunca
decide sozinho se uma vaga é elegível. O prompt obriga o modelo a usar
somente os dados fornecidos; `format: "json"` (ver ollama/client.py)
evita o Qwen3 verbalizar raciocínio em vez de responder o JSON.

O "índice" devolvido pelo modelo é uma medida interna de compatibilidade
textual — NUNCA uma probabilidade de contratação. Isso é reforçado no
próprio prompt, não só documentado em comentário.
"""

import json
import logging

from app.services.ollama.client import OllamaError, generate_completion

logger = logging.getLogger(__name__)

_NIVEIS_VALIDOS = {"alta", "media", "baixa"}

_SYSTEM_PROMPT = """Você analisa a compatibilidade entre o perfil de um estudante e uma vaga de estágio.

REGRAS OBRIGATÓRIAS, sem exceção:
1. Use SOMENTE as informações escritas no PERFIL DO ESTUDANTE e na VAGA abaixo. Nunca invente tecnologia, experiência, requisito ou qualquer dado que não esteja explicitamente escrito.
2. Você está avaliando compatibilidade TEMÁTICA E TÉCNICA entre o texto do perfil e o texto da vaga — não é uma previsão de contratação, não é uma nota de aprovação, não é uma probabilidade. Não use palavras como "chance", "provável" ou "vai conseguir".
3. Responda ESTRITAMENTE em JSON, com exatamente estas chaves:
{
  "nivel": "alta" ou "media" ou "baixa",
  "indice": número inteiro de 0 a 100 (índice interno de compatibilidade textual, não é probabilidade),
  "pontos_compativeis": lista de strings curtas com o que bate entre perfil e vaga,
  "pontos_parciais": lista de strings curtas com o que bate parcialmente,
  "lacunas": lista de strings curtas com o que a vaga pede e não aparece no perfil,
  "justificativa": um parágrafo curto explicando a análise
}
Nenhum texto fora do JSON."""


def _montar_prompt(aluno_texto: str, vaga_texto: str) -> str:
    return (
        "PERFIL DO ESTUDANTE:\n"
        f"{aluno_texto}\n\n"
        "VAGA:\n"
        f"{vaga_texto}\n\n"
        "Analise a compatibilidade seguindo exatamente as regras e o formato JSON indicados."
    )


def _extrair_bloco_json(texto: str) -> str:
    """Mesmo em modo JSON o modelo às vezes emite texto extra ao redor
    — pega só o primeiro bloco { ... } por segurança."""
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio == -1 or fim == -1 or fim < inicio:
        return texto
    return texto[inicio : fim + 1]


def analisar_compatibilidade(aluno_texto: str, vaga_texto: str) -> dict | None:
    """Retorna None se o Ollama estiver indisponível ou a resposta não
    puder ser interpretada — quem chama decide como lidar (pular este
    candidato, não gerar a Recomendacao, etc.), nunca propaga exceção."""
    prompt = _montar_prompt(aluno_texto, vaga_texto)

    try:
        bruto = generate_completion(prompt, system=_SYSTEM_PROMPT, json_format=True)
    except OllamaError as exc:
        logger.warning("Análise de compatibilidade indisponível (Ollama): %s", exc)
        return None

    try:
        dados = json.loads(_extrair_bloco_json(bruto))
    except json.JSONDecodeError:
        logger.warning("Resposta do Qwen3 não é JSON válido: %r", bruto[:500])
        return None

    if not isinstance(dados, dict) or dados.get("nivel") not in _NIVEIS_VALIDOS:
        logger.warning("Resposta do Qwen3 fora do formato esperado: %r", dados)
        return None

    try:
        indice = max(0.0, min(100.0, float(dados.get("indice", 0))))
    except (TypeError, ValueError):
        indice = 0.0

    def _lista_strings(valor) -> list[str]:
        if not isinstance(valor, list):
            return []
        return [str(item) for item in valor if item]

    return {
        "nivel": dados["nivel"],
        "indice": indice,
        "pontos_compativeis": _lista_strings(dados.get("pontos_compativeis")),
        "pontos_parciais": _lista_strings(dados.get("pontos_parciais")),
        "lacunas": _lista_strings(dados.get("lacunas")),
        "justificativa": str(dados.get("justificativa") or ""),
    }
