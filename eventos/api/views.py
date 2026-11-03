"""Endpoints da API REST.

Escolhas de arquitetura (justificadas no README):
  - Atividade em ViewSet + router: CRUD padrão completo com paginação,
    busca e ordenação — o ViewSet dá isso de graça (RF10).
  - Evento, programação, inscrições e agenda em @api_view/APIView: têm
    poucas ações específicas do domínio, onde um ViewSet traria rotas
    sem sentido (PUT de inscrição, POST de agenda etc.).
"""
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Evento, Atividade, InscricaoEvento, InscricaoAtividade
from ..services import inscrever_em_atividade, validar_atividade
from .permissions import IsOrganizadorDoEvento
from .serializers import (
    SalaSerializer, EventoSerializer, AtividadeSerializer,
    ProgramacaoAtividadeSerializer, ProgramacaoEventoSerializer,
    InscricaoEventoSerializer, InscricaoAtividadeSerializer,
)


def _erro_validation(exc):
    """Transforma ValidationError do serviço em 400 com JSON claro (RF8)."""
    msgs = exc.messages if hasattr(exc, 'messages') else [str(exc)]
    return Response({'detalhe': msgs}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Salas (leitura pública — útil para apps escolherem sala ao exibir vagas)
# ---------------------------------------------------------------------------

@api_view(['GET'])
def lista_salas(request):
    salas = SalaSerializer(
        __import__('eventos.models', fromlist=['Sala']).Sala.objects.all(), many=True,
    )
    return Response(salas.data)


# ---------------------------------------------------------------------------
# Eventos (RF3 público; RF5/RF9 escrita só do organizador)
# ---------------------------------------------------------------------------

class EventoListCreate(APIView):
    """GET público: lista de eventos. POST autenticado: cria (organizador = request.user)."""

    def get(self, request):
        eventos = Evento.objects.select_related('organizador').order_by('-inicio')
        termo = request.query_params.get('q', '').strip()
        if termo:
            eventos = eventos.filter(Q(nome__icontains=termo) | Q(descricao__icontains=termo))
        return Response(EventoSerializer(eventos, many=True).data)

    def post(self, request):
        if not request.user.is_authenticated:
            return Response(
                {'detalhe': 'Credenciais de autenticação não foram fornecidas.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = EventoSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(organizador=request.user)  # nunca vem do JSON
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EventoDetail(APIView):
    """GET público; PUT/PATCH/DELETE apenas do organizador do evento."""

    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        return Response(EventoSerializer(evento).data)

    def _evento_do_dono(self, request, pk):
        if not request.user.is_authenticated:
            return None, Response(
                {'detalhe': 'Credenciais de autenticação não foram fornecidas.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        evento = get_object_or_404(Evento, pk=pk)
        if evento.organizador != request.user:
            return None, Response(
                {'detalhe': 'Acesso negado: este evento não é seu.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return evento, None

    def put(self, request, pk):
        evento, erro = self._evento_do_dono(request, pk)
        if erro:
            return erro
        serializer = EventoSerializer(evento, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        return self.put(request, pk)

    def delete(self, request, pk):
        evento, erro = self._evento_do_dono(request, pk)
        if erro:
            return erro
        evento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProgramacaoEventoView(APIView):
    """RF3 + desafio: evento, atividades, sala de cada uma e vagas restantes
    em UMA requisição, com número fixo de consultas (3), sem N+1."""

    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        atividades = (
            evento.atividades.select_related('sala')
            .annotate(total_inscricoes=Count('inscricoes'))
        )
        # vagas_restantes calculado do annotate (0 consultas por atividade)
        serializer = ProgramacaoEventoSerializer(evento)
        data = serializer.data
        data['atividades'] = [
            dict(ProgramacaoAtividadeSerializer(a).data,
                 vagas_restantes=max(a.sala.capacidade - a.total_inscricoes, 0))
            for a in atividades
        ]
        return Response(data)


# ---------------------------------------------------------------------------
# Atividades (ViewSet: CRUD + paginação + busca + ordenação — RF10)
# ---------------------------------------------------------------------------

class AtividadeViewSet(viewsets.ModelViewSet):
    queryset = Atividade.objects.select_related('evento', 'sala')
    serializer_class = AtividadeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOrganizadorDoEvento]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['inicio']
    ordering = ['inicio']

    def get_queryset(self):
        # vagas_restantes via annotate: calculada, sem consulta por item.
        return Atividade.objects.select_related('evento', 'sala').annotate(
            total_inscricoes=Count('inscricoes'),
        )

    def perform_create(self, serializer):
        evento_pk = self.kwargs.get('evento_pk') or self.request.data.get('evento')
        evento = get_object_or_404(Evento, pk=evento_pk) if evento_pk else None
        if evento is None:
            raise ValidationError({'evento': ['Informe o evento da atividade.']})
        if evento.organizador != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Acesso negado: este evento não é seu.')
        serializer.save(evento=evento)  # evento nunca é aceito do JSON direto

    def perform_update(self, serializer):
        serializer.save()  # evento nunca muda pelo payload

    # RF8: o serializer.validate já roda validar_atividade (regra única).
    # Convertemos ValidationError do serviço em 400 com JSON.
    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            return _erro_validation(e)


# ---------------------------------------------------------------------------
# Inscrições (RF6) — funções porque são ações pontuais, não CRUD
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def inscrever_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if not evento.inscricoes_abertas:
        return Response({'detalhe': 'As inscrições deste evento estão encerradas.'},
                        status=status.HTTP_400_BAD_REQUEST)
    inscricao, criada = InscricaoEvento.objects.get_or_create(
        evento=evento, participante=request.user,
    )
    if not criada:
        return Response({'detalhe': 'Você já está inscrito neste evento.'},
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(InscricaoEventoSerializer(inscricao).data,
                    status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancelar_inscricao_evento(request, pk):
    """RN5: apagar a inscrição do evento apaga as das atividades (cascade)."""
    inscricao = get_object_or_404(
        InscricaoEvento, evento_id=pk, participante=request.user,
    )
    inscricao.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def inscrever_atividade(request, pk):
    """RF8: RN1, RN2 e RN4 verificadas em services.inscrever_em_atividade —
    a MESMA função que o site HTML usa."""
    atividade = get_object_or_404(Atividade.objects.select_related('sala'), pk=pk)
    _, erro = inscrever_em_atividade(request.user, atividade)
    if erro is not None:
        return Response({'detalhe': [str(m) for m in erro.messages]},
                        status=status.HTTP_400_BAD_REQUEST)
    inscricao = InscricaoAtividade.objects.get(
        inscricao_evento__participante=request.user, atividade=atividade,
    )
    return Response(InscricaoAtividadeSerializer(inscricao).data,
                    status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancelar_inscricao_atividade(request, pk):
    inscricao = get_object_or_404(
        InscricaoAtividade,
        atividade_id=pk, inscricao_evento__participante=request.user,
    )
    inscricao.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def minha_agenda(request):
    """RF7: apenas as inscrições de quem apresentou o token, ordenadas."""
    inscricoes = (
        InscricaoAtividade.objects
        .filter(inscricao_evento__participante=request.user)
        .select_related('atividade__evento', 'atividade__sala')
        .order_by('atividade__inicio', 'atividade__fim')
    )
    eventos = (
        InscricaoEvento.objects.filter(participante=request.user)
        .select_related('evento').order_by('evento__inicio')
    )
    return Response({
        'eventos': InscricaoEventoSerializer(eventos, many=True).data,
        'atividades': InscricaoAtividadeSerializer(inscricoes, many=True).data,
    })
