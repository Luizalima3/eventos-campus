"""Serializers da API.

Eles NÃO reimplementam nenhuma regra de negócio: as cinco regras moram em
`eventos/services.py` e são chamadas daqui. O organizador/participante nunca
vem do JSON — vêm de request.user (restrição técnica 3).
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models import Sala, Evento, Atividade, InscricaoEvento, InscricaoAtividade
from ..services import validar_atividade

User = get_user_model()


class SalaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sala
        fields = ['id', 'nome', 'bloco', 'capacidade']


class AtividadeSerializer(serializers.ModelSerializer):
    """Programação pública: nome da sala e vagas restantes calculadas."""
    sala_nome = serializers.CharField(source='sala.nome', read_only=True)
    vagas_restantes = serializers.IntegerField(read_only=True)
    evento_nome = serializers.CharField(source='evento.nome', read_only=True)

    class Meta:
        model = Atividade
        fields = [
            'id', 'evento', 'evento_nome', 'titulo', 'tipo', 'descricao',
            'responsavel', 'sala', 'sala_nome', 'inicio', 'fim',
            'vagas_restantes',
        ]
        read_only_fields = ['evento']

    def validate(self, attrs):
        # RN3 e datas: regra única, mesma chamada que o formulário HTML faz.
        if self.instance is not None:
            evento = self.instance.evento
        else:
            evento_pk = self.initial_data.get('evento')
            evento = Evento.objects.filter(pk=evento_pk).first() if evento_pk else None
        sala = attrs.get('sala') or getattr(self.instance, 'sala', None)
        inicio = attrs.get('inicio') or getattr(self.instance, 'inicio', None)
        fim = attrs.get('fim') or getattr(self.instance, 'fim', None)
        erros = validar_atividade(
            sala=sala, inicio=inicio, fim=fim,
            evento=evento,
            instance=self.instance,
        )
        if erros:
            raise serializers.ValidationError({'detalhe': erros})
        return attrs


class EventoSerializer(serializers.ModelSerializer):
    organizador_username = serializers.CharField(
        source='organizador.username', read_only=True,
    )

    class Meta:
        model = Evento
        fields = [
            'id', 'nome', 'descricao', 'inicio', 'fim',
            'inscricoes_abertas', 'organizador', 'organizador_username',
        ]
        read_only_fields = ['organizador']

    def validate(self, attrs):
        inicio = attrs.get('inicio') or getattr(self.instance, 'inicio', None)
        fim = attrs.get('fim') or getattr(self.instance, 'fim', None)
        if inicio and fim and fim < inicio:
            raise serializers.ValidationError(
                {'detalhe': 'A data de fim não pode vir antes da de início.'}
            )
        return attrs


class ProgramacaoAtividadeSerializer(serializers.ModelSerializer):
    """Atividade dentro da programação de um evento (dados públicos do site)."""
    sala_nome = serializers.CharField(source='sala.nome', read_only=True)
    vagas_restantes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Atividade
        fields = [
            'id', 'titulo', 'tipo', 'descricao', 'responsavel',
            'sala_nome', 'inicio', 'fim', 'vagas_restantes',
        ]


class ProgramacaoEventoSerializer(serializers.ModelSerializer):
    """Endpoint único (desafio): evento + atividades aninhadas, sem N+1
    quando a view usa select_related/prefetch (vagas são annotate/count)."""
    atividades = ProgramacaoAtividadeSerializer(many=True, read_only=True)
    organizador_username = serializers.CharField(
        source='organizador.username', read_only=True,
    )

    class Meta:
        model = Evento
        fields = [
            'id', 'nome', 'descricao', 'inicio', 'fim',
            'inscricoes_abertas', 'organizador_username', 'atividades',
        ]


class InscricaoEventoSerializer(serializers.ModelSerializer):
    participante_username = serializers.CharField(
        source='participante.username', read_only=True,
    )
    evento_nome = serializers.CharField(source='evento.nome', read_only=True)

    class Meta:
        model = InscricaoEvento
        fields = ['id', 'evento', 'evento_nome', 'participante_username', 'data']
        read_only_fields = ['participante']


class InscricaoAtividadeSerializer(serializers.ModelSerializer):
    atividade_titulo = serializers.CharField(source='atividade.titulo', read_only=True)
    sala_nome = serializers.CharField(source='atividade.sala.nome', read_only=True)
    inicio = serializers.DateTimeField(source='atividade.inicio', read_only=True)
    fim = serializers.DateTimeField(source='atividade.fim', read_only=True)

    class Meta:
        model = InscricaoAtividade
        fields = [
            'id', 'atividade', 'atividade_titulo', 'sala_nome',
            'inicio', 'fim', 'data',
        ]
