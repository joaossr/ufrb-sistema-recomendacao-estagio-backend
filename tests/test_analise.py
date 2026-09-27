"""
Testes de app/services/recomendacao/analise.py — a camada que parseia
e valida a resposta do Qwen3 (Fase 8 / passo 22). Nunca chama o Ollama
de verdade: monkeypatcha `generate_completion` para controlar
exatamente o que "o LLM respondeu" em cada cenário, incluindo os que
importam mais (resposta malformada, Ollama fora do ar) — são esses
que garantem que uma falha do LLM nunca derruba a requisição inteira.
"""

import app.services.recomendacao.analise as analise_module
from app.services.ollama.client import OllamaError


def test_resposta_valida_e_parseada_corretamente(monkeypatch):
    monkeypatch.setattr(
        analise_module,
        "generate_completion",
        lambda prompt, system=None, json_format=False: (
            '{"nivel": "alta", "indice": 90, "pontos_compativeis": ["Python", "SQL"], '
            '"pontos_parciais": ["Docker"], "lacunas": ["AWS"], "justificativa": "Boa aderência."}'
        ),
    )
    resultado = analise_module.analisar_compatibilidade("perfil", "vaga")
    assert resultado["nivel"] == "alta"
    assert resultado["indice"] == 90
    assert resultado["pontos_compativeis"] == ["Python", "SQL"]
    assert resultado["lacunas"] == ["AWS"]


def test_indice_fora_da_faixa_e_limitado_entre_0_e_100(monkeypatch):
    monkeypatch.setattr(
        analise_module,
        "generate_completion",
        lambda prompt, system=None, json_format=False: '{"nivel": "media", "indice": 500}',
    )
    resultado = analise_module.analisar_compatibilidade("perfil", "vaga")
    assert resultado["indice"] == 100.0


def test_texto_extra_ao_redor_do_json_e_ignorado(monkeypatch):
    """Mesmo em modo JSON o Qwen3 às vezes emite texto antes/depois —
    achado real documentado em analise.py."""
    monkeypatch.setattr(
        analise_module,
        "generate_completion",
        lambda prompt, system=None, json_format=False: (
            'Aqui está minha análise: {"nivel": "baixa", "indice": 10} Espero ter ajudado!'
        ),
    )
    resultado = analise_module.analisar_compatibilidade("perfil", "vaga")
    assert resultado["nivel"] == "baixa"


def test_json_invalido_retorna_none_sem_levantar_excecao(monkeypatch):
    monkeypatch.setattr(
        analise_module,
        "generate_completion",
        lambda prompt, system=None, json_format=False: "isto não é json nenhum",
    )
    assert analise_module.analisar_compatibilidade("perfil", "vaga") is None


def test_nivel_fora_do_vocabulario_permitido_retorna_none(monkeypatch):
    monkeypatch.setattr(
        analise_module,
        "generate_completion",
        lambda prompt, system=None, json_format=False: '{"nivel": "excelente", "indice": 95}',
    )
    assert analise_module.analisar_compatibilidade("perfil", "vaga") is None


def test_ollama_indisponivel_retorna_none_sem_propagar_excecao(monkeypatch):
    def _levanta_erro(prompt, system=None, json_format=False):
        raise OllamaError("Ollama fora do ar (teste)")

    monkeypatch.setattr(analise_module, "generate_completion", _levanta_erro)
    assert analise_module.analisar_compatibilidade("perfil", "vaga") is None


def test_listas_ausentes_na_resposta_viram_listas_vazias(monkeypatch):
    monkeypatch.setattr(
        analise_module,
        "generate_completion",
        lambda prompt, system=None, json_format=False: '{"nivel": "media", "indice": 50}',
    )
    resultado = analise_module.analisar_compatibilidade("perfil", "vaga")
    assert resultado["pontos_compativeis"] == []
    assert resultado["pontos_parciais"] == []
    assert resultado["lacunas"] == []
    assert resultado["justificativa"] == ""
