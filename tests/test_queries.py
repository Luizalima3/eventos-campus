"""RF12 — assertNumQueries na programação: número fixo, não cresce com N."""
from django.test import TestCase
from django.urls import reverse

from eventos.models import Atividade
from .base import DadosBase


class ConsultasProgramacaoTest(DadosBase):
    def _programacao(self):
        from rest_framework.test import APIClient
        return APIClient().get(reverse('api-programacao', args=[self.evento1.pk]))

    def test_programacao_com_uma_atividade_usa_poucas_consultas(self):
        self.criar_atividade(self.evento1, self.sala_grande)
        with self.assertNumQueries(4):
            r = self._programacao()
        self.assertEqual(r.status_code, 200)

    def test_programacao_com_cinco_atividades_nao_cresce(self):
        for i in range(5):
            self.criar_atividade(self.evento1, self.sala_grande, f'A{i}', hora_ini=9 + i * 2, hora_fim=11 + i * 2)
        with self.assertNumQueries(4):  # mesmo número de 1 atividade
            self._programacao()
