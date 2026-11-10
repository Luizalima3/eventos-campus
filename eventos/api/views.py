"""
Endpoints da API REST.

Escolhas de arquitetura (justificadas no README):
  - Atividade em ViewSet + router: CRUD padrão completo com paginação,
    busca e ordenação — o ViewSet dá isso de graça (RF10).
  - Evento, programação, inscrições e agenda em @api_view/APIView: têm
    poucas ações específicas do domínio, onde um ViewSet traria rotas
    sem sentido (PUT de inscrição, POST de agenda etc.).
"""
from django.core.exceptions import ValidationError as DjValidationError
from django.db.models import Prefetch, Q, Count
from rest_framework import viewsets, permissions, generics, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.serializers import ValidationError as DrfValidationError

from ..models import Evento, Atividade, Sala, InscricaoEvento, InscricaoAtividade
from ..services import inscrever_em_atividade
from .permissions import IsOrganizadorDoEvento
from .serializers import (
    SalaSerializer, EventoSerializer, AtividadeSerializer,
    ProgramaEventoSerializer, InscricaoEventoSerializer,
    InscricaoAtividadeSerializer,
)


class SalaViewSet(viewsets.ReadOnlyModelViewSet):
    """Porta aberta: qualquer pessoa vê as salas (RF10)."""
    queryset = Sala.objects.all()
    serializer_class = SalaSerializer
    permission_classes = [permissions.AllowAny]


class AtividadeViewSet(viewsets.ModelViewSet):
    """GET público; PUT/PATCH/DELETE apenas do organizador do evento."""
    queryset = Atividade.objects.select_related('sala', 'evento')
    serializer_class = AtividadeSerializer
    permission_classes = [IsOrganizadorDoEvento]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def perform_create(self, serializer):
        evento = serializer.validated_data.get('evento')
        if evento is None:
            raise DrfValidationError({'evento': 'Informe o evento da atividade.'})
        if evento.organizador != self.request.user:
            self.permission_denied(
                self.request, message='Acesso negado: este evento não é seu.'
            )
        serializer.save()


class EventoListCreate(generics.ListCreateAPIView):
    """GET público: lista de eventos. POST autenticado: cria (organizador = request.user)."""
    queryset = Evento.objects.all().order_by('-inicio')
    serializer_class = EventoSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(organizador=self.request.user)


class EventoDetail(generics.RetrieveAPIView):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer
    permission_classes = [permissions.AllowAny]


class ProgramacaoEventoView(generics.RetrieveAPIView):
    """RF3 + desafio: evento, atividades, sala de cada uma e vagas restantes
    em UMA requisição, com número fixo de consultas (3), sem N+1."""
    queryset = Evento.objects.prefetch_related(
        Prefetch('atividades', queryset=Atividade.objects.select_related('sala'))
    ).annotate(_inscritos=Count('atividades__inscricoes'))
    serializer_class = ProgramaEventoSerializer
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, *args, **kwargs):
        evento = self.get_object()
        # vagas_restantes sem consulta extra: um count por atividade em bulk.
        # _inscritos só é usado quando o evento tem alguma inscrição;
        # atividades sem inscrição nenhuma ficam com count zero por agregação.
        inscricoes = list(
            InscricaoAtividade.objects.filter(atividade__evento=evento)
            .values('atividade').annotate(total=Count('pk'))
        )
        counts = {r['atividade']: r['total'] for r in inscricoes}
        atividades = list(evento.atividades.all())
        for a in atividades:
            a._inscritos = counts.get(a.id, 0)
        evento._atividades_prefetch = atividades
        return Response(self.get_serializer(evento).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_inscrever_evento(request, pk):
    try:
        evento = Evento.objects.get(pk=pk)
    except Evento.DoesNotExist:
        return Response({'detail': 'Evento não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    if not evento.inscricoes_abertas:
        return Response(
            {'detail': 'As inscrições deste evento estão encerradas.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    inscricao, criada = InscricaoEvento.objects.get_or_create(
        evento=evento, participante=request.user
    )
    if not criada:
        return Response({'detail': 'Você já está inscrito neste evento.'},
                        status=status.HTTP_200_OK)
    return Response(InscricaoEventoSerializer(inscricao).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_cancelar_evento(request, pk):
    """RN5: apagar a inscrição do evento apaga as das atividades (cascade)."""
    deleted, _ = InscricaoEvento.objects.filter(evento_id=pk, participante=request.user).delete()
    if not deleted:
        return Response({'detail': 'Você não está inscrito neste evento.'},
                        status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_inscrever_atividade(request, pk):
    try:
        atividade = Atividade.objects.get(pk=pk)
    except Atividade.DoesNotExist:
        return Response({'detail': 'Atividade não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    # RF8: RN1, RN2 e RN4 verificadas em services.inscrever_em_atividade —
    # a MESMA função que o site HTML usa.
    try:
        inscricao = inscrever_em_atividade(request.user, atividade)
    except DjValidationError as e:
        # Transforma ValidationError do serviço em 400 com JSON claro (RF8).
        return Response({'detail': '; '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(InscricaoAtividadeSerializer(inscricao).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_cancelar_atividade(request, pk):
    deleted, _ = InscricaoAtividade.objects.filter(
        atividade_id=pk, inscricao_evento__participante=request.user
    ).delete()
    if not deleted:
        return Response({'detail': 'Você não está inscrito nesta atividade.'},
                        status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_agenda(request):
    """RF7: apenas as inscrições de quem apresentou o token, ordenadas."""
    ies = (InscricaoEvento.objects.filter(participante=request.user)
           .select_related('evento').order_by('evento__inicio'))
    iats = (InscricaoAtividade.objects.filter(inscricao_evento__participante=request.user)
            .select_related('atividade__evento', 'atividade__sala')
            .order_by('atividade__inicio', 'atividade__fim'))
    return Response({
        'eventos': InscricaoEventoSerializer([i for i in ies], many=True).data,
        'atividades': InscricaoAtividadeSerializer([i for i in iats], many=True).data,
    })


class ApiTokenView(ObtainAuthToken):
    """POST { username, password } -> { token }. Porta de entrada da API."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        token = Token.objects.filter(key=response.data.get('token')).first()
        if token and not token.user.is_staff:
            return Response(response.data)
        return response
