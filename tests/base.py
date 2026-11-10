"""
Dados de teste criados pelos próprios testes (restrição técnica 3) e
cenários compartilhados em setUpTestData (restrição técnica 7).

Todos os endereços vêm de reverse() e nada usa time.sleep (restrições 5 e 6).
"""
from datetime import date, datetime, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from eventos.models import Sala, Evento, Atividade, InscricaoEvento, InscricaoAtividade

User = get_user_model()
HOJE = date.today()
BASE = datetime(HOJE.year, HOJE.month, HOJE.day, 9, 0)


def dt(dia, hora, minuto=0):
    """DateTime aware em TZ local a partir do dia de hoje + deslocamento."""
    from django.utils import timezone
    return timezone.make_aware(datetime.combine(HOJE + timedelta(days=dia),
                                                datetime.min.time()) + timedelta(hours=hora, minutes=minuto))


class DadosBase(TestCase):
    """Cenário comum: 2 organizadores, 2 participantes, salas, 2 eventos."""

    @classmethod
    def setUpTestData(cls):
        cls.org1 = User.objects.create_user('org.carlos', password='rad2026#senha')
        cls.org2 = User.objects.create_user('org.beatriz', password='rad2026#senha')
        cls.part1 = User.objects.create_user('part.ana', password='rad2026#senha')
        cls.part2 = User.objects.create_user('part.bruno', password='rad2026#senha')

        cls.sala_pequena = Sala.objects.create(nome='Sala 12', bloco='C', capacidade=2)
        cls.sala_grande = Sala.objects.create(nome='Auditorio', bloco='A', capacidade=100)

        cls.evento1 = Evento.objects.create(
            nome='Semana de Testes', organizador=cls.org1,
            inicio=HOJE, fim=HOJE + timedelta(days=5),
        )
        cls.evento2 = Evento.objects.create(
            nome='Outro Evento', organizador=cls.org2,
            inicio=HOJE, fim=HOJE + timedelta(days=5),
        )

    @classmethod
    def criar_atividade(cls, evento, sala, titulo='Aula', dia=1, hora_ini=9, hora_fim=11):
        return Atividade.objects.create(
            evento=evento, titulo=titulo, tipo='palestra', responsavel='Resp',
            sala=sala, inicio=dt(dia, hora_ini), fim=dt(dia, hora_fim),
        )

    @classmethod
    def inscrever_no_evento(cls, user, evento=None):
        return InscricaoEvento.objects.create(evento=evento or cls.evento1, participante=user)

    @staticmethod
    def token(user):
        return Token.objects.get_or_create(user=user)[0].key

    @staticmethod
    def cliente_api(token=None):
        c = APIClient()
        if token:
            c.credentials(HTTP_AUTHORIZATION='Token ' + token)
        return c
