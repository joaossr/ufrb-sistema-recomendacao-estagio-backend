"""
Testes das regras determinísticas de elegibilidade (Fase 8 / passo
20) — tudo aqui é código puro, o LLM nunca decide isso. Construímos
os objetos Aluno/Vaga/Curso/Convenio em memória, sem sessão de banco:
SQLAlchemy permite atribuir relationships diretamente em instâncias
transientes, o que é suficiente para testar lógica pura sem o custo
de uma transação real.
"""

from datetime import date, timedelta

from app.models.aluno import Aluno
from app.models.catalogo import Curso
from app.models.empresa import Convenio
from app.models.vaga import Vaga
from app.services.recomendacao.regras import curso_compativel, vaga_elegivel


def _aluno(curso_nome: str | None = "Engenharia de Computação") -> Aluno:
    aluno = Aluno(matricula="0000000000")
    aluno.curso = Curso(nome=curso_nome) if curso_nome else None
    return aluno


def _vaga(**overrides) -> Vaga:
    campos = {
        "titulo": "Estágio de teste",
        "status": "ativa",
        "cursos": [],
        "data_fim": None,
        "convenio_id": None,
    }
    campos.update(overrides)
    vaga = Vaga(**campos)
    return vaga


def test_vaga_sem_restricao_de_curso_e_compativel_com_qualquer_aluno():
    vaga = _vaga(cursos=[])
    assert curso_compativel(_aluno("Qualquer Curso"), vaga) is True


def test_vaga_com_curso_exigido_bate_com_aluno_do_mesmo_curso():
    vaga = _vaga(cursos=["Engenharia de Computação", "Sistemas de Informação"])
    assert curso_compativel(_aluno("Engenharia de Computação"), vaga) is True


def test_vaga_com_curso_exigido_nao_bate_com_aluno_de_outro_curso():
    vaga = _vaga(cursos=["Agronomia"])
    assert curso_compativel(_aluno("Engenharia de Computação"), vaga) is False


def test_vaga_com_curso_exigido_e_aluno_sem_curso_definido_nao_bate():
    vaga = _vaga(cursos=["Agronomia"])
    assert curso_compativel(_aluno(curso_nome=None), vaga) is False


def test_vaga_encerrada_nunca_e_elegivel_mesmo_com_curso_compativel():
    vaga = _vaga(status="encerrada", cursos=[])
    assert vaga_elegivel(_aluno(), vaga) is False


def test_vaga_com_prazo_vencido_nao_e_elegivel():
    ontem = date.today() - timedelta(days=1)
    vaga = _vaga(status="ativa", data_fim=ontem)
    assert vaga_elegivel(_aluno(), vaga) is False


def test_vaga_com_prazo_futuro_e_elegivel():
    amanha = date.today() + timedelta(days=1)
    vaga = _vaga(status="ativa", data_fim=amanha, cursos=[])
    assert vaga_elegivel(_aluno(), vaga) is True


def test_vaga_sem_data_fim_nao_e_filtrada_por_prazo():
    vaga = _vaga(status="ativa", data_fim=None, cursos=[])
    assert vaga_elegivel(_aluno(), vaga) is True


def test_vaga_com_convenio_vencido_nao_e_elegivel():
    ontem = date.today() - timedelta(days=1)
    vaga = _vaga(status="ativa", cursos=[])
    vaga.convenio_id = "algum-id"
    vaga.convenio = Convenio(status="vencido", data_fim=ontem)
    assert vaga_elegivel(_aluno(), vaga) is False


def test_vaga_com_convenio_vigente_e_elegivel():
    amanha = date.today() + timedelta(days=1)
    vaga = _vaga(status="ativa", cursos=[])
    vaga.convenio_id = "algum-id"
    vaga.convenio = Convenio(status="vigente", data_fim=amanha)
    assert vaga_elegivel(_aluno(), vaga) is True


def test_vaga_sem_convenio_vinculado_nao_e_filtrada_por_isso():
    vaga = _vaga(status="ativa", cursos=[], convenio_id=None)
    assert vaga_elegivel(_aluno(), vaga) is True


def test_convenio_com_status_desatualizado_no_banco_e_recalculado_pela_data():
    """Reproduz o cenário relatado pelo usuário: um convênio foi
    importado como 'vigente' num PDF antigo e ninguém nunca mais
    tocou naquela linha — `status` continua dizendo 'vigente' no
    banco, mas `data_fim` já passou de verdade. A regra de
    elegibilidade tem que confiar em `data_fim` (o dado bruto), nunca
    no rótulo congelado desde a última importação."""
    ontem = date.today() - timedelta(days=1)
    vaga = _vaga(status="ativa", cursos=[])
    vaga.convenio_id = "algum-id"
    vaga.convenio = Convenio(status="vigente", data_fim=ontem)  # rótulo desatualizado de propósito
    assert vaga_elegivel(_aluno(), vaga) is False


def test_convenio_com_status_vencido_no_banco_mas_data_fim_futura_e_recalculado_como_vigente():
    """O inverso também precisa funcionar: se por algum motivo o rótulo
    salvo diz 'vencido' mas a data_fim é futura, a vaga é elegível —
    a data manda, não o texto congelado."""
    amanha = date.today() + timedelta(days=1)
    vaga = _vaga(status="ativa", cursos=[])
    vaga.convenio_id = "algum-id"
    vaga.convenio = Convenio(status="vencido", data_fim=amanha)
    assert vaga_elegivel(_aluno(), vaga) is True
