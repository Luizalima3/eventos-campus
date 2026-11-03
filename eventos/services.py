"""Lugar ÚNICO das cinco regras de negócio.

Escolha de projeto (seção 4 da atividade): em vez de escrever as regras no
serializer (que só a API chamaria) ou nas views HTML (que só o site chamaria),
elas foram extraídas para funções de serviço que AMBOS os caminhos chamam:

  - site HTML   -> eventos/views.py chama essas funções
  - API DRF     -> eventos/api/serializers.py e eventos/api/views.py chamam

Assim cada regra existe exatamente uma vez. O serializer NÃO repete nada; ele
apenas repassa os erros que o serviço devolve para virar JSON com status 400.
"""
from django.core.exceptions import ValidationError

from .models import Atividade, InscricaoEvento, InscricaoAtividade


# ---------------------------------------------------------------------------
# Regras sobre CRIAÇÃO/EDIÇÃO de atividades (RN3 e validação de datas)
# ---------------------------------------------------------------------------

def validar_atividade(*, sala, inicio, fim, evento, instance=None):
    """RN3 + período do evento + fim >= inicio. Retorna lista de mensagens.

    Chamado por AtividadeForm.clean (site) e por AtividadeSerializer.validate (API).
    """
    erros = []
    if fim and inicio and fim < inicio:
        erros.append('O fim não pode vir antes do início.')

    if evento and inicio and fim:
        if inicio.date() < evento.inicio or fim.date() > evento.fim:
            erros.append(
                'A atividade precisa acontecer dentro do período do evento '
                f'({evento.inicio.strftime("%d/%m/%Y")} a {evento.fim.strftime("%d/%m/%Y")}).'
            )

        if sala:
            conflito = Atividade.objects.filter(
                sala=sala, inicio__lt=fim, fim__gt=inicio,
            )
            if instance is not None and instance.pk:
                conflito = conflito.exclude(pk=instance.pk)
            if conflito.exists():
                nomes = ', '.join(a.titulo for a in conflito)
                erros.append(
                    f'A sala {sala.nome} já está ocupada nesse horário (atividade: {nomes}).'
                )
    return erros


# ---------------------------------------------------------------------------
# Regras sobre INSCRIÇÕES (RN1, RN2, RN4)
# ---------------------------------------------------------------------------

def inscrever_em_atividade(participante, atividade):
    """Verifica RN1, RN2 e RN4 e cria a inscrição.

    Retorna (inscricao, erro). erro é None quando tudo deu certo.
    Chamado por views.inscrever_atividade (site) e pela API.
    """
    # RN4: só quem está inscrito no evento.
    inscricao_evento = InscricaoEvento.objects.filter(
        evento=atividade.evento, participante=participante,
    ).first()
    if inscricao_evento is None:
        return None, ValidationError(
            'Você precisa estar inscrito no evento para escolher atividades.'
        )

    if InscricaoAtividade.objects.filter(
        inscricao_evento=inscricao_evento, atividade=atividade,
    ).exists():
        return None, ValidationError('Você já está inscrito nesta atividade.')

    # RN1: capacidade vem da sala, calculada na hora.
    if atividade.lotada():
        return None, ValidationError(
            'Atividade lotada: todas as vagas da sala já foram ocupadas.'
        )

    # RN2: conflito com QUALQUER atividade do participante, inclusive de outros eventos.
    conflitos = Atividade.objects.filter(
        inscricoes__inscricao_evento__participante=participante,
        inicio__lt=atividade.fim,
        fim__gt=atividade.inicio,
    )
    if conflitos.exists():
        nomes = ', '.join(a.titulo for a in conflitos)
        return None, ValidationError(
            f'Conflito de horário: você já está inscrito em "{nomes}", '
            'que acontece no mesmo horário.'
        )

    return InscricaoAtividade.objects.create(
        inscricao_evento=inscricao_evento, atividade=atividade,
    ), None
