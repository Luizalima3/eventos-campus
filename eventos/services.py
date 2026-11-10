"""
Lugar ÚNICO das cinco regras de negócio.

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


def validar_atividade(inicio, fim, sala, evento=None, instance=None):
    """RN3 + período do evento + fim >= inicio. Retorna lista de mensagens.

    Chamado por AtividadeForm.clean (site), AtividadeSerializer.validate (API)
    e Atividade.clean/Sala.clean (models, RF4).
    """
    erros = []
    if fim and inicio and fim < inicio:
        erros.append('O fim não pode vir antes do início.')
        return erros

    if evento is None and instance is not None and instance.pk:
        evento = instance.evento
    if evento is not None and inicio and fim:
        if inicio.date() < evento.inicio or fim.date() > evento.fim:
            erros.append(
                'A atividade precisa acontecer dentro do período do evento '
                f'({evento.inicio.strftime("%d/%m/%Y")} a {evento.fim.strftime("%d/%m/%Y")}).'
            )

    # RN3: sala ocupada — contra TODAS as atividades, de qualquer evento.
    conflito = Atividade.objects.filter(
        sala=sala,
        inicio__lt=fim,
        fim__gt=inicio,
    )
    if instance and instance.pk:
        conflito = conflito.exclude(pk=instance.pk)
    if conflito.exists():
        nomes = ', '.join(a.titulo for a in conflito)
        erros.append(f'A sala {sala.nome} já está ocupada nesse horário (atividade: {nomes}).')
    return erros


def inscrever_em_atividade(participante, atividade):
    """Verifica RN1, RN2 e RN4 e cria a inscrição.

    Retorna (inscricao, erro). erro é None quando tudo deu certo.
    Chamado por views.inscrever_atividade (site) e pela API.
    """
    evento = atividade.evento

    # RN4: só quem já está inscrito no evento.
    inscricao = InscricaoEvento.objects.filter(
        evento=evento, participante=participante
    ).first()
    if inscricao is None:
        raise ValidationError(
            ['Você precisa estar inscrito no evento para escolher atividades.']
        )

    if atividade.lotada():  # RN1: capacidade vem da sala, por relacionamento
        raise ValidationError(
            ['Atividade lotada: todas as vagas da sala já foram ocupadas.']
        )

    if InscricaoAtividade.objects.filter(inscricao_evento=inscricao, atividade=atividade).exists():
        raise ValidationError(['Você já está inscrito nesta atividade.'])

    # RN2: conflito com QUALQUER atividade do participante, inclusive de outros eventos.
    conflitos = Atividade.objects.filter(
        inscricoes__inscricao_evento__participante=participante,
        inicio__lt=atividade.fim,
        fim__gt=atividade.inicio,
    )
    if conflitos.exists():
        nomes = ', '.join(a.titulo for a in conflitos)
        raise ValidationError(
            [f'Conflito de horário: você já está inscrito em "{nomes}", '
             'que acontece no mesmo horário.']
        )

    return InscricaoAtividade.objects.create(inscricao_evento=inscricao, atividade=atividade)
