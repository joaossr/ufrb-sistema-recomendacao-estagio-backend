import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RecomendacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    aluno_id: uuid.UUID
    empresa_id: uuid.UUID | None
    vaga_id: uuid.UUID | None
    similaridade: float | None
    indice_compatibilidade: float | None
    nivel: str | None
    pontos_compativeis: list | None
    pontos_parciais: list | None
    lacunas: list | None
    justificativa: str | None
    tipo: str
    modelo_llm: str | None
    modelo_embedding: str | None
    created_at: datetime


class EmpresaResumoOut(BaseModel):
    id: uuid.UUID
    nome: str


class ConvenioResumoOut(BaseModel):
    status: str
    data_fim: date | None


class VagaResumoOut(BaseModel):
    id: uuid.UUID
    titulo: str
    modalidade: str | None
    localizacao: str | None
    bolsa: str | None
    carga_horaria: str | None
    link: str | None
    status: str
    convenio: ConvenioResumoOut | None


class AlunoResumoOut(BaseModel):
    """Usado só nas rotas do caminho inverso (admin) — nunca exposto
    ao próprio aluno olhando as próprias recomendações."""

    id: uuid.UUID
    nome_completo: str | None
    matricula: str
    curso: str | None


class GeracaoAlunoResultadoOut(BaseModel):
    """Uma linha do resumo de `POST /admin/recomendacoes/gerar` — o
    que aconteceu para UM aluno dentro do processamento em lote."""

    aluno_id: uuid.UUID
    matricula: str
    nome_completo: str | None
    recomendacoes_geradas: int
    prospeccoes_geradas: int
    erro: str | None = None


class GeracaoRecomendacoesResumoOut(BaseModel):
    """Resposta de `POST /admin/recomendacoes/gerar` (Fase 12): o
    admin dispara para TODOS os alunos cadastrados de uma vez — cada
    aluno é processado de forma isolada (um erro num aluno não afeta
    os demais), mesma filosofia de resiliência do resto do sistema."""

    alunos_processados: int
    alunos_com_erro: int
    total_recomendacoes_geradas: int
    total_prospeccoes_geradas: int
    detalhes: list[GeracaoAlunoResultadoOut]


class RecomendacaoDetalhadaOut(BaseModel):
    """Formato consumido pelo frontend (recomendacoes.html): junta a
    Recomendacao com os dados de exibição da empresa/vaga/convênio,
    para a tela não precisar de N chamadas extras."""

    id: uuid.UUID
    tipo: str
    nivel: str | None
    indice_compatibilidade: float | None
    similaridade: float | None
    pontos_compativeis: list
    pontos_parciais: list
    lacunas: list
    justificativa: str | None
    empresa: EmpresaResumoOut
    vaga: VagaResumoOut | None
    aluno: AlunoResumoOut | None = None
    created_at: datetime
