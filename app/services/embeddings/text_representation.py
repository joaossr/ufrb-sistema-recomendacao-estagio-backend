"""
Transforma perfil/empresa/vaga em texto estruturado — a base dos
embeddings (Fase 7 / passo 16). Roda ANTES de qualquer chamada de IA:
só concatena os dados que já existem no banco, nunca inventa nada. Se
um campo estiver vazio, a linha correspondente simplesmente não entra
no texto.
"""

from app.models.aluno import Aluno
from app.models.empresa import Empresa
from app.models.vaga import Vaga


def _linha(rotulo: str, valor) -> str:
    if not valor:
        return ""
    if isinstance(valor, (list, tuple)):
        valor = ", ".join(str(v) for v in valor if v)
        if not valor:
            return ""
    return f"{rotulo}: {valor}"


def aluno_to_text(aluno: Aluno) -> str:
    partes = []

    if aluno.curso:
        partes.append(_linha("Curso", f"{aluno.curso.nome} ({aluno.curso.centro_id})"))
    partes.append(_linha("Semestre atual", aluno.semestre_atual))
    partes.append(_linha("Previsão de conclusão", aluno.previsao_conclusao))

    tecnologias = [f"{v.tecnologia.nome} ({v.nivel})" if v.nivel else v.tecnologia.nome for v in aluno.tecnologias]
    partes.append(_linha("Tecnologias e conhecimentos", tecnologias))

    for projeto in aluno.projetos:
        detalhes = [projeto.nome]
        if projeto.area_projeto:
            detalhes.append(f"área: {projeto.area_projeto.nome}")
        if projeto.tipo_projeto:
            detalhes.append(f"tipo: {projeto.tipo_projeto.nome}")
        if projeto.descricao:
            detalhes.append(projeto.descricao)
        tecs_projeto = [t.nome for t in projeto.tecnologias]
        if tecs_projeto:
            detalhes.append("tecnologias: " + ", ".join(tecs_projeto))
        partes.append(_linha("Projeto", " — ".join(detalhes)))

    for exp in aluno.experiencias:
        detalhes = [f"{exp.cargo} em {exp.empresa}"]
        if exp.area_atuacao:
            detalhes.append(f"área: {exp.area_atuacao}")
        if exp.descricao:
            detalhes.append(exp.descricao)
        partes.append(_linha("Experiência profissional", " — ".join(detalhes)))

    areas_interesse = [v.area_interesse.nome for v in aluno.areas_interesse]
    partes.append(_linha("Áreas de interesse", areas_interesse))

    if aluno.tcc and aluno.tcc.situacao != "nao_iniciou":
        detalhes = [aluno.tcc.situacao]
        if aluno.tcc.titulo:
            detalhes.append(aluno.tcc.titulo)
        if aluno.tcc.palavras_chave:
            detalhes.append("palavras-chave: " + ", ".join(aluno.tcc.palavras_chave))
        partes.append(_linha("TCC", " — ".join(detalhes)))

    for formacao in aluno.formacoes_complementares:
        partes.append(_linha("Formação complementar", formacao.nome))

    idiomas = [lang.nome for lang in aluno.idiomas]
    partes.append(_linha("Idiomas", idiomas))

    return "\n".join(p for p in partes if p)


def empresa_to_text(empresa: Empresa) -> str:
    """Hoje a única fonte de dados de empresa é o PDF de convênios
    (só nome) — o texto fica mais rico automaticamente assim que a
    empresa tiver vagas cadastradas (Fase 6)."""
    partes = [_linha("Empresa", empresa.nome)]

    cursos, areas, tecnologias = set(), set(), set()
    for vaga in empresa.vagas:
        cursos.update(vaga.cursos or [])
        areas.update(vaga.areas or [])
        tecnologias.update(vaga.tecnologias or [])

    partes.append(_linha("Cursos relacionados às vagas", sorted(cursos)))
    partes.append(_linha("Áreas de atuação", sorted(areas)))
    partes.append(_linha("Tecnologias associadas", sorted(tecnologias)))

    return "\n".join(p for p in partes if p)


def vaga_to_text(vaga: Vaga) -> str:
    partes = [
        _linha("Vaga", vaga.titulo),
        _linha("Empresa", vaga.empresa.nome if vaga.empresa else None),
        _linha("Descrição", vaga.descricao),
        _linha("Atividades", vaga.atividades),
        _linha("Requisitos", vaga.requisitos),
        _linha("Cursos", vaga.cursos),
        _linha("Áreas", vaga.areas),
        _linha("Tecnologias", vaga.tecnologias),
        _linha("Modalidade", vaga.modalidade),
        _linha("Localização", vaga.localizacao),
        _linha("Bolsa", vaga.bolsa),
        _linha("Carga horária", vaga.carga_horaria),
        _linha("Benefícios", vaga.beneficios),
    ]
    return "\n".join(p for p in partes if p)
