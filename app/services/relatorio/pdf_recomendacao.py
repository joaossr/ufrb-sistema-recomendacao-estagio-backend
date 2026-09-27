"""
Geração de PDF do relatório de compatibilidade de uma Recomendacao
(Fase 14) — o admin baixa e envia à empresa como material de
apresentação do estudante, sem precisar montar isso manualmente.

Mesma regra inviolável do resto do sistema: nível/índice de
compatibilidade NUNCA são apresentados como probabilidade de
contratação — o aviso abaixo é reproduzido no próprio PDF, não só na
tela (ver frontend/recomendacoes.html).
"""

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.models.aluno import Aluno
from app.models.empresa import Empresa
from app.models.recomendacao import Recomendacao
from app.models.vaga import Vaga

_NIVEL_LABELS = {"alta": "Alta compatibilidade", "media": "Compatibilidade média", "baixa": "Baixa compatibilidade"}
_CONVENIO_LABELS = {"vigente": "Convênio vigente", "vencido": "Convênio vencido", "indeterminado": "Convênio com data indefinida"}


def _estilos():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="Titulo",
            parent=base["Title"],
            fontSize=16,
            spaceAfter=4,
        )
    )
    base.add(ParagraphStyle(name="Subtitulo", parent=base["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=16))
    base.add(
        ParagraphStyle(
            name="Secao",
            parent=base["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#1e2f6e"),
            spaceBefore=14,
            spaceAfter=6,
        )
    )
    base.add(ParagraphStyle(name="Corpo", parent=base["Normal"], fontSize=10, leading=14))
    base.add(
        ParagraphStyle(
            name="Aviso",
            parent=base["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#5a5a5a"),
            borderColor=colors.HexColor("#cccccc"),
            borderWidth=0.5,
            borderPadding=8,
            backColor=colors.HexColor("#f5f6fa"),
        )
    )
    return base


def _linha_rotulo(rotulo: str, valor) -> str:
    return f"<b>{rotulo}:</b> {valor if valor else '—'}"


def _lista(itens: list[str], estilo) -> ListFlowable | None:
    if not itens:
        return None
    return ListFlowable(
        [ListItem(Paragraph(item, estilo), leftIndent=8) for item in itens],
        bulletType="bullet",
        start="•",
        leftIndent=14,
    )


def gerar_pdf_recomendacao(db: Session, rec: Recomendacao) -> bytes:
    aluno = db.get(Aluno, rec.aluno_id)
    empresa = db.get(Empresa, rec.empresa_id) if rec.empresa_id else None
    vaga = db.get(Vaga, rec.vaga_id) if rec.vaga_id else None

    estilos = _estilos()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title="Relatório de Compatibilidade",
    )

    story = []
    story.append(Paragraph("Relatório de Compatibilidade — Estágio", estilos["Titulo"]))
    story.append(
        Paragraph(
            "Sistema de Recomendação de Estágio · Universidade Federal do Recôncavo da Bahia · "
            f"Gerado em {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
            estilos["Subtitulo"],
        )
    )

    story.append(
        Paragraph(
            "<b>Aviso importante:</b> o nível e o índice de compatibilidade abaixo medem a similaridade "
            "TEXTUAL/TEMÁTICA entre o perfil do estudante e a vaga ou empresa, avaliada por um modelo de "
            "linguagem (Qwen3) a partir apenas dos dados cadastrados. Isto NÃO é uma previsão de "
            "contratação, nem uma nota de aprovação, nem qualquer medida de \"chance de conseguir a vaga\".",
            estilos["Aviso"],
        )
    )

    # ------------------------------------------------------------------
    # 1. Dados do estudante
    # ------------------------------------------------------------------
    story.append(Paragraph("1. Dados do estudante", estilos["Secao"]))
    identidade = [
        _linha_rotulo("Nome completo", aluno.nome_completo),
        _linha_rotulo("Matrícula", aluno.matricula),
        _linha_rotulo("Curso", aluno.curso.nome if aluno.curso else None),
        _linha_rotulo("Semestre atual", aluno.semestre_atual),
        _linha_rotulo("E-mail", aluno.email),
        _linha_rotulo("Telefone", aluno.telefone),
        _linha_rotulo("LinkedIn", aluno.linkedin_url),
    ]
    for linha in identidade:
        story.append(Paragraph(linha, estilos["Corpo"]))

    # ------------------------------------------------------------------
    # 2. Tecnologias e conhecimentos
    # ------------------------------------------------------------------
    if aluno.tecnologias:
        story.append(Paragraph("2. Tecnologias e conhecimentos", estilos["Secao"]))
        itens = [f"{v.tecnologia.nome} ({v.nivel})" if v.nivel else v.tecnologia.nome for v in aluno.tecnologias]
        lista = _lista(itens, estilos["Corpo"])
        if lista:
            story.append(lista)

    # ------------------------------------------------------------------
    # 3. Projetos desenvolvidos
    # ------------------------------------------------------------------
    if aluno.projetos:
        story.append(Paragraph("3. Projetos desenvolvidos", estilos["Secao"]))
        for projeto in aluno.projetos:
            titulo = f"<b>{projeto.nome}</b>"
            detalhes = [d for d in (projeto.area_projeto.nome if projeto.area_projeto else None, projeto.tipo_projeto.nome if projeto.tipo_projeto else None) if d]
            if detalhes:
                titulo += " — " + ", ".join(detalhes)
            story.append(Paragraph(titulo, estilos["Corpo"]))
            if projeto.descricao:
                story.append(Paragraph(projeto.descricao, estilos["Corpo"]))
            tecs_projeto = [t.nome for t in projeto.tecnologias]
            if tecs_projeto:
                story.append(Paragraph("<i>Tecnologias: " + ", ".join(tecs_projeto) + "</i>", estilos["Corpo"]))
            story.append(Spacer(1, 6))

    # ------------------------------------------------------------------
    # 4. Experiência profissional
    # ------------------------------------------------------------------
    if aluno.experiencias:
        story.append(Paragraph("4. Experiência profissional", estilos["Secao"]))
        for exp in aluno.experiencias:
            cabecalho = f"<b>{exp.cargo}</b> — {exp.empresa}"
            if exp.area_atuacao:
                cabecalho += f" ({exp.area_atuacao})"
            story.append(Paragraph(cabecalho, estilos["Corpo"]))
            if exp.descricao:
                story.append(Paragraph(exp.descricao, estilos["Corpo"]))
            story.append(Spacer(1, 6))

    # ------------------------------------------------------------------
    # 5. Áreas de interesse
    # ------------------------------------------------------------------
    if aluno.areas_interesse:
        story.append(Paragraph("5. Áreas de interesse", estilos["Secao"]))
        nomes = [v.area_interesse.nome for v in aluno.areas_interesse]
        story.append(Paragraph(", ".join(nomes), estilos["Corpo"]))

    # ------------------------------------------------------------------
    # 6. Empresa / vaga de interesse
    # ------------------------------------------------------------------
    story.append(Paragraph("6. Empresa / vaga de interesse", estilos["Secao"]))
    if empresa:
        story.append(Paragraph(_linha_rotulo("Empresa", empresa.nome), estilos["Corpo"]))
        story.append(Paragraph(_linha_rotulo("CNPJ", empresa.cnpj), estilos["Corpo"]))
        localizacao_empresa = " - ".join(p for p in (empresa.cidade, empresa.uf) if p)
        story.append(Paragraph(_linha_rotulo("Área / Cidade", f"{empresa.area or '—'} / {localizacao_empresa or '—'}"), estilos["Corpo"]))
    if vaga:
        story.append(Spacer(1, 6))
        story.append(Paragraph(_linha_rotulo("Vaga", vaga.titulo), estilos["Corpo"]))
        story.append(Paragraph(_linha_rotulo("Modalidade", vaga.modalidade), estilos["Corpo"]))
        story.append(Paragraph(_linha_rotulo("Localização", vaga.localizacao), estilos["Corpo"]))
        story.append(Paragraph(_linha_rotulo("Bolsa", vaga.bolsa), estilos["Corpo"]))
        story.append(Paragraph(_linha_rotulo("Carga horária", vaga.carga_horaria), estilos["Corpo"]))
        if vaga.convenio:
            story.append(Paragraph(_linha_rotulo("Situação do convênio", _CONVENIO_LABELS.get(vaga.convenio.status, vaga.convenio.status)), estilos["Corpo"]))
        if vaga.descricao:
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Descrição:</b> " + vaga.descricao, estilos["Corpo"]))
        if vaga.requisitos:
            story.append(Paragraph("<b>Requisitos:</b> " + vaga.requisitos, estilos["Corpo"]))
        if vaga.tecnologias:
            story.append(Paragraph("<b>Tecnologias buscadas:</b> " + ", ".join(vaga.tecnologias), estilos["Corpo"]))
    else:
        story.append(
            Paragraph(
                "Sem vaga ativa vinculada no momento — recomendação de prospecção "
                "(contato para futura oportunidade, não uma vaga aberta agora).",
                estilos["Corpo"],
            )
        )

    # ------------------------------------------------------------------
    # 7. Análise de compatibilidade (Qwen3)
    # ------------------------------------------------------------------
    story.append(Paragraph("7. Análise de compatibilidade", estilos["Secao"]))
    nivel_label = _NIVEL_LABELS.get(rec.nivel, rec.nivel or "—")
    indice_label = f"{round(rec.indice_compatibilidade)}/100" if rec.indice_compatibilidade is not None else "—"
    tabela = Table(
        [["Nível", "Índice de compatibilidade"], [nivel_label, indice_label]],
        colWidths=[8 * cm, 8 * cm],
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e2f6e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ]
        )
    )
    story.append(tabela)
    story.append(Spacer(1, 10))

    if rec.pontos_compativeis:
        story.append(Paragraph("<b>Pontos compatíveis</b>", estilos["Corpo"]))
        lista = _lista(rec.pontos_compativeis, estilos["Corpo"])
        if lista:
            story.append(lista)
        story.append(Spacer(1, 6))

    if rec.pontos_parciais:
        story.append(Paragraph("<b>Compatibilidade parcial</b>", estilos["Corpo"]))
        lista = _lista(rec.pontos_parciais, estilos["Corpo"])
        if lista:
            story.append(lista)
        story.append(Spacer(1, 6))

    if rec.lacunas:
        story.append(Paragraph("<b>Lacunas identificadas</b>", estilos["Corpo"]))
        lista = _lista(rec.lacunas, estilos["Corpo"])
        if lista:
            story.append(lista)
        story.append(Spacer(1, 6))

    if rec.justificativa:
        story.append(Paragraph("<b>Justificativa</b>", estilos["Corpo"]))
        story.append(Paragraph(rec.justificativa, estilos["Corpo"]))

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "Documento gerado automaticamente pelo Sistema de Recomendação de Estágio (UFRB). "
            "Dados acadêmicos e de contato fornecidos pelo próprio estudante em seu cadastro.",
            estilos["Subtitulo"],
        )
    )

    doc.build(story)
    return buffer.getvalue()
