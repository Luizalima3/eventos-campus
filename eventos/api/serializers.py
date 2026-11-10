"""
Serializers da API.

Eles NÃO reimplementam nenhuma regra de negócio: as cinco regras moram em
`eventos/services.py` e são chamadas daqui. O organizador/participante nunca
vem do JSON — vêm de request.user (restrição técnica 3).
"""
from rest_framework import serializers

from ..models import Sala, Evento, Atividade, InscricaoEvento, InscricaoAtividade
from ..services import validar_atividade


class SalaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sala
        fields = ['id', 'nome', 'bloco', 'capacidade']


class EventoSerializer(serializers.ModelSerializer):
    organizador = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Evento
        fields = ['id', 'nome', 'descricao', 'inicio', 'fim', 'inscricoes_abertas', 'organizador']


class AtividadeSerializer(serializers.ModelSerializer):
    sala = SalaSerializer(read_only=True)
    sala_id = serializers.PrimaryKeyRelatedField(
        queryset=Sala.objects.all(), source='sala', write_only=True)
    organizador = serializers.ReadOnlyField(source='evento.organizador.username')

    class Meta:
        model = Atividade
        fields = [
            'id', 'titulo', 'tipo', 'descricao', 'responsavel',
            'evento', 'sala', 'sala_id', 'inicio', 'fim', 'organizador',
        ]
        read_only_fields = ['sala']

    def validate(self, attrs):
        # Delega as regras ao serviço único — o serializer não repete nada.
        sala = attrs.get('sala') or getattr(self.instance, 'sala', None)
        inicio = attrs.get('inicio') or getattr(self.instance, 'inicio', None)
        fim = attrs.get('fim') or getattr(self.instance, 'fim', None)
        evento = (attrs.get('evento') or
                  (self.instance.evento if self.instance else None))
        if sala is None or inicio is None or fim is None:
            raise serializers.ValidationError(
                'Informe título, sala, início e fim da atividade.')
        erros = validar_atividade(inicio, fim, sala, evento=evento,
                                  instance=self.instance)
        if erros:
            raise serializers.ValidationError(erros)
        return attrs


class ProgramaEventoSerializer(serializers.ModelSerializer):
    """Endpoint único (desafio): evento + atividades aninhadas, sem N+1
    quando a view usa select_related/prefetch (vagas são annotate/count)."""
    atividades = serializers.SerializerMethodField()
    organizador = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Evento
        fields = ['id', 'nome', 'inicio', 'fim', 'organizador', 'atividades']

    def get_atividades(self, obj):
        ats = getattr(obj, '_atividades_prefetch', None)
        if ats is None:
            ats = obj.atividades.all()
        return [
            {
                'id': a.id,
                'titulo': a.titulo,
                'tipo': a.tipo,
                'inicio': a.inicio,
                'fim': a.fim,
                'sala': a.sala.nome,
                # _inscritos vem pré-calculado da view (bulk); sem ele, cai no count.
                'vagas_restantes': max(
                    a.sala.capacidade - (a._inscritos if hasattr(a, '_inscritos') else a.inscricoes.count()),
                    0),
            }
            for a in ats
        ]


class InscricaoEventoSerializer(serializers.ModelSerializer):
    participante = serializers.StringRelatedField(read_only=True)
    evento = serializers.StringRelatedField()

    class Meta:
        model = InscricaoEvento
        fields = ['id', 'evento', 'participante', 'data']


class InscricaoAtividadeSerializer(serializers.ModelSerializer):
    participante = serializers.StringRelatedField(read_only=True)
    atividade = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = InscricaoAtividade
        fields = ['id', 'atividade', 'participante', 'data']
