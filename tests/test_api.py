"""
Regras de negócio pela porta da API (RF3) + RF10, RF11.

Dez cenários de recusa no total (site + API).
"""
from django.urls import reverse
from rest_framework import status

from eventos.models import InscricaoEvento, InscricaoAtividade, Evento, Atividade
from .base import DadosBase, dt


def payload_rn3(evento, sala, titulo):
    return {
        'titulo': titulo, 'tipo': 'palestra', 'responsavel': 'R',
        'evento': evento.pk,
        'inicio': f'{dt(1, 9):%Y-%m-%dT%H:%M:%S}',
        'fim': f'{dt(1, 11):%Y-%m-%dT%H:%M:%S}',
        'sala_id': sala.pk,
    }


class PortaAbertaTest(DadosBase):
    """RF10 — endpoints públicos sem token, com dados esperados."""

    def test_lista_eventos_sem_token(self):
        r = self.cliente_api().get(reverse('api-eventos'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        nomes = [e['nome'] for e in r.data]
        self.assertIn('Semana de Testes', nomes)

    def test_lista_eventos_nao_expose_organizador_id_nem_senha(self):
        # Escrito APÓS a sabotagem 8 (campo a mais no serializer público)
        # passar despercebida: o conjunto de chaves tem que ser exatamente o esperado.
        r = self.cliente_api().get(reverse('api-eventos'))
        chaves = set(r.data[0].keys())
        self.assertEqual(chaves, {'id', 'nome', 'descricao', 'inicio', 'fim',
                                  'inscricoes_abertas', 'organizador'})

    def test_programacao_publica_com_atividades(self):
        self.criar_atividade(self.evento1, self.sala_grande, 'Palestra IA')
        r = self.cliente_api().get(reverse('api-programacao', args=[self.evento1.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['nome'], 'Semana de Testes')
        self.assertEqual(r.data['atividades'][0]['titulo'], 'Palestra IA')
        self.assertIn('vagas_restantes', r.data['atividades'][0])


class PortaFechadaTest(DadosBase):
    """RF11 — 401 sem token, 403 com quem não pode, 200/201 com quem pode."""

    def test_criar_evento_sem_token_da_401(self):
        r = self.cliente_api().post(reverse('api-eventos'), {'nome': 'X'})
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_criar_evento_com_token_cria(self):
        c = self.cliente_api(self.token(self.org1))
        r = c.post(reverse('api-eventos'), {'nome': 'Novo Ev', 'inicio': '2026-01-01', 'fim': '2026-01-02'})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Evento.objects.filter(nome='Novo Ev').exists())

    def test_agenda_sem_token_da_401(self):
        r = self.cliente_api().get(reverse('api-agenda'))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_agenda_com_token_traz_so_o_meu(self):
        self.inscrever_no_evento(self.part1)
        r = self.cliente_api(self.token(self.part1)).get(reverse('api-agenda'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['eventos']), 1)

    def test_atividade_somente_leitura_para_anonimo(self):
        a = self.criar_atividade(self.evento1, self.sala_grande)
        c = self.cliente_api()
        self.assertEqual(c.get(reverse('atividade-detail', args=[a.pk])).status_code, 200)
        self.assertEqual(c.delete(reverse('atividade-detail', args=[a.pk])).status_code, 401)


class RegrasApiTest(DadosBase):
    """As 5 regras recusadas pela API (RF3)."""

    def test_rn1_api_recusa_terceira_inscricao(self):
        a = self.criar_atividade(self.evento1, self.sala_pequena)  # cap 2
        tok = lambda u: self.cliente_api(self.token(u))
        for u in (self.part1, self.part2):
            self.inscrever_no_evento(u)
            tok(u).post(reverse('api-inscrever-atividade', args=[a.pk]))
        self.inscrever_no_evento(self.org1)
        r = tok(self.org1).post(reverse('api-inscrever-atividade', args=[a.pk]))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('lotada', r.data['detail'])
        self.assertEqual(InscricaoAtividade.objects.filter(atividade=a).count(), 2)

    def test_rn1_api_aceita_ate_a_capacidade(self):
        a = self.criar_atividade(self.evento1, self.sala_pequena)
        for u in (self.part1, self.part2):
            self.inscrever_no_evento(u)
            r = self.cliente_api(self.token(u)).post(reverse('api-inscrever-atividade', args=[a.pk]))
            self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_rn2_api_recusa_horario_sobreposto(self):
        a1 = self.criar_atividade(self.evento1, self.sala_grande, 'A1')
        a2 = self.criar_atividade(self.evento1, self.sala_pequena, 'A2')
        self.inscrever_no_evento(self.part1)
        c = self.cliente_api(self.token(self.part1))
        c.post(reverse('api-inscrever-atividade', args=[a1.pk]))
        r = c.post(reverse('api-inscrever-atividade', args=[a2.pk]))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Conflito', r.data['detail'])
        self.assertFalse(InscricaoAtividade.objects.filter(atividade=a2).exists())

    def test_rn3_api_recusa_sala_ocupada(self):
        self.criar_atividade(self.evento1, self.sala_grande, 'Ocupante')
        c = self.cliente_api(self.token(self.org1))
        r = c.post(reverse('atividade-list'), payload_rn3(self.evento1, self.sala_grande, 'Duplicada'))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ocupada', str(r.data['non_field_errors']))

    def test_rn3_api_aceita_sala_livre(self):
        self.criar_atividade(self.evento1, self.sala_grande, 'Ocupante')
        c = self.cliente_api(self.token(self.org1))
        r = c.post(reverse('atividade-list'), payload_rn3(self.evento1, self.sala_pequena, 'Outra Sala'))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_rn4_api_recusa_sem_inscricao_no_evento(self):
        a = self.criar_atividade(self.evento1, self.sala_grande)
        c = self.cliente_api(self.token(self.part1))
        r = c.post(reverse('api-inscrever-atividade', args=[a.pk]))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('precisa estar inscrito no evento', r.data['detail'])
        self.assertEqual(InscricaoAtividade.objects.count(), 0)

    def test_rn5_api_cancelar_evento_remove_atividades(self):
        a = self.criar_atividade(self.evento1, self.sala_grande)
        insc = self.inscrever_no_evento(self.part1)
        InscricaoAtividade.objects.create(inscricao_evento=insc, atividade=a)
        r = self.cliente_api(self.token(self.part1)).delete(
            reverse('api-cancelar-evento', args=[self.evento1.pk]))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InscricaoEvento.objects.exists())
        self.assertFalse(InscricaoAtividade.objects.exists())

    def test_rn5_api_nao_cancela_inscricao_alheia(self):
        self.inscrever_no_evento(self.part1)
        r = self.cliente_api(self.token(self.part2)).delete(
            reverse('api-cancelar-evento', args=[self.evento1.pk]))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(InscricaoEvento.objects.filter(participante=self.part1).exists())
