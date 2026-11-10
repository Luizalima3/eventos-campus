"""
Regras de negócio pela porta do SITE HTML (RF2/RF3) + RF5, RF6, RF7, RF8.

Endereços sempre com reverse(); nada escrito à mão.
"""
from django.urls import reverse

from eventos.models import InscricaoEvento, InscricaoAtividade
from .base import DadosBase, dt


def detalhe(evento):
    return reverse('detalhe_evento', args=[evento.pk])


class RegrasSiteTest(DadosBase):
    """Cada regra em seu caminho que DEVE funcionar e no que DEVE ser recusado."""

    # RN1 — capacidade
    def test_rn1_inscreve_ate_a_capacidade_e_recusa_a_terceira(self):
        a = self.criar_atividade(self.evento1, self.sala_pequena)  # cap 2
        for u in (self.part1, self.part2):
            self.inscrever_no_evento(u)
            self.client.force_login(u)
            r = self.client.post(reverse('inscrever_atividade', args=[a.pk]), follow=True)
            self.assertEqual(r.status_code, 200)
        self.inscrever_no_evento(self.org1)  # usuário extra
        self.client.force_login(self.org1)
        r = self.client.post(reverse('inscrever_atividade', args=[a.pk]), follow=True)
        self.assertContains(r, 'lotada')
        self.assertEqual(InscricaoAtividade.objects.filter(atividade=a).count(), 2)

    # RN2 — horário sobreposto
    def test_rn2_mesmo_horario_para_o_participante_e_recusado(self):
        a1 = self.criar_atividade(self.evento1, self.sala_grande, 'A1')
        a2 = self.criar_atividade(self.evento1, self.sala_pequena, 'A2')  # mesmo horário, outra sala
        self.inscrever_no_evento(self.part1)
        self.client.force_login(self.part1)
        self.client.post(reverse('inscrever_atividade', args=[a1.pk]))
        r = self.client.post(reverse('inscrever_atividade', args=[a2.pk]), follow=True)
        self.assertContains(r, 'Conflito de horário')
        self.assertFalse(InscricaoAtividade.objects.filter(atividade=a2).exists())

    def test_rn2_horarios_diferentes_sao_aceitos(self):
        a1 = self.criar_atividade(self.evento1, self.sala_grande, 'A1', hora_ini=9, hora_fim=11)
        a2 = self.criar_atividade(self.evento1, self.sala_grande, 'A2', hora_ini=13, hora_fim=15)
        self.inscrever_no_evento(self.part1)
        self.client.force_login(self.part1)
        r = self.client.post(reverse('inscrever_atividade', args=[a1.pk]), follow=True)
        r = self.client.post(reverse('inscrever_atividade', args=[a2.pk]), follow=True)
        self.assertContains(r, 'Inscrição em "A2" realizada!'.replace('"A2"', '“A2”')) if False else None
        self.assertContains(r, 'Inscrição em &quot;A2&quot; realizada!')
        self.assertEqual(InscricaoAtividade.objects.filter(inscricao_evento__participante=self.part1).count(), 2)

    # RN3 — sala ocupada
    def test_rn3_duas_atividades_na_mesma_sala_sobrepostas_e_recusado(self):
        self.criar_atividade(self.evento1, self.sala_grande, 'Ja Existe')
        self.client.force_login(self.org1)
        r = self.client.post(
            reverse('criar_atividade', args=[self.evento1.pk]),
            data={
                'titulo': 'Duplicada', 'tipo': 'palestra', 'responsavel': 'R',
                'sala': self.sala_grande.pk,
                'inicio': f'{dt(1, 9):%Y-%m-%dT%H:%M}',
                'fim': f'{dt(1, 11):%Y-%m-%dT%H:%M}',
            }, follow=True)
        # sobrepõe: mesma sala, mesmo dia 09-11 do dados base
        self.assertContains(r, 'ocupada')

    def test_rn3_sala_livre_no_mesmo_horario_e_aceita(self):
        self.criar_atividade(self.evento1, self.sala_grande, 'Ja Existe')
        self.client.force_login(self.org1)
        r = self.client.post(
            reverse('criar_atividade', args=[self.evento1.pk]),
            data={
                'titulo': 'Outra Sala', 'tipo': 'palestra', 'responsavel': 'R',
                'sala': self.sala_pequena.pk,
                'inicio': f'{dt(1, 9):%Y-%m-%dT%H:%M}',
                'fim': f'{dt(1, 11):%Y-%m-%dT%H:%M}',
            }, follow=True)
        self.assertContains(r, 'Atividade criada!')

    # RF6/redirect — escrito APÓS a sabotagem 6 (render no lugar de redirect)
    # passar despercebida na primeira rodada.
    def test_post_inscrever_atividade_redireciona_para_o_detalhe(self):
        a = self.criar_atividade(self.evento1, self.sala_grande)
        self.inscrever_no_evento(self.part1)
        self.client.force_login(self.part1)
        r = self.client.post(reverse('inscrever_atividade', args=[a.pk]))
        self.assertEqual(r.status_code, 302)  # redirect, não render
        self.assertRedirects(r, detalhe(self.evento1))

    # RN4 — inscrição prévia no evento
    def test_rn4_sem_inscricao_no_evento_e_recusado(self):
        a = self.criar_atividade(self.evento1, self.sala_grande)
        self.client.force_login(self.part1)  # NÃO inscrito no evento
        r = self.client.post(reverse('inscrever_atividade', args=[a.pk]), follow=True)
        self.assertContains(r, 'precisa estar inscrito no evento')
        self.assertEqual(InscricaoAtividade.objects.count(), 0)

    def test_rn4_com_inscricao_no_evento_e_aceito(self):
        # Escrito APÓS a sabotagem 6 passar despercebida: um POST bem-sucedido
        # deve REDIRECIONAR (302 para o detalhe), não renderizar direto.
        a = self.criar_atividade(self.evento1, self.sala_grande)
        self.inscrever_no_evento(self.part1)
        self.client.force_login(self.part1)
        r = self.client.post(reverse('inscrever_atividade', args=[a.pk]), follow=True)
        self.assertContains(r, 'realizada')
        self.assertEqual(InscricaoAtividade.objects.count(), 1)

    # RN5 — cancelar o evento cancela as atividades
    def test_rn5_cancelar_evento_remove_inscricoes_das_atividades(self):
        a = self.criar_atividade(self.evento1, self.sala_grande)
        insc = self.inscrever_no_evento(self.part1)
        InscricaoAtividade.objects.create(inscricao_evento=insc, atividade=a)
        self.client.force_login(self.part1)
        r = self.client.post(reverse('cancelar_inscricao_evento', args=[self.evento1.pk]), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(InscricaoEvento.objects.filter(participante=self.part1).exists())
        self.assertFalse(InscricaoAtividade.objects.filter(atividade=a).exists())

    def test_rn5_cancelar_somente_atividade_preserva_o_evento(self):
        a = self.criar_atividade(self.evento1, self.sala_grande)
        insc = self.inscrever_no_evento(self.part1)
        InscricaoAtividade.objects.create(inscricao_evento=insc, atividade=a)
        self.client.force_login(self.part1)
        self.client.post(reverse('cancelar_inscricao_atividade', args=[a.pk]))
        self.assertTrue(InscricaoEvento.objects.filter(participante=self.part1).exists())
        self.assertEqual(InscricaoAtividade.objects.count(), 0)


class ViewsLeituraTest(DadosBase):
    """RF5 — views de leitura: status, conteúdo, contexto e template."""

    def test_programacao_status_conteudo_contexto_template(self):
        a = self.criar_atividade(self.evento1, self.sala_grande, 'Palestra X')
        r = self.client.get(detalhe(self.evento1))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Palestra X')
        self.assertTemplateUsed(r, 'eventos/detalhe_evento.html')
        self.assertEqual(r.context['evento'].pk, self.evento1.pk)
        self.assertIn(a, r.context['atividades'])
        self.assertIsNone(r.context['inscricao'])


class ViewsEscritaTest(DadosBase):
    """RF6 — inscrição/cancelamento: banco, redirect e mensagem."""

    def test_post_inscrever_no_evento_salva_redireciona_e_mensagem(self):
        self.client.force_login(self.part1)
        r = self.client.post(reverse('inscrever_evento', args=[self.evento1.pk]))
        self.assertRedirects(r, detalhe(self.evento1))
        self.assertTrue(InscricaoEvento.objects.filter(participante=self.part1).exists())
        msgs = [str(m) for m in r.wsgi_request._messages]
        self.assertTrue(any('realizada' in m for m in msgs))

    def test_post_cancelar_evento_apaga_e_redireciona(self):
        self.inscrever_no_evento(self.part1)
        self.client.force_login(self.part1)
        r = self.client.post(reverse('cancelar_inscricao_evento', args=[self.evento1.pk]))
        self.assertRedirects(r, detalhe(self.evento1))
        self.assertEqual(InscricaoEvento.objects.count(), 0)


class AutenticacaoTest(DadosBase):
    """RF7 — anônimo vai para o login com next de volta."""

    def test_anonimo_redirecionado_para_login_com_next(self):
        url = reverse('inscrever_evento', args=[self.evento1.pk])
        r = self.client.get(url)
        login_url = reverse('login')
        self.assertRedirects(r, f'{login_url}?next={url}')

    def test_anonimo_redirecionado_na_agenda_com_next(self):
        url = reverse('minha_agenda')
        r = self.client.get(url)
        self.assertRedirects(r, f'{reverse("login")}?next={url}')


class AutorizacaoTest(DadosBase):
    """RF8 — resposta correta E banco intacto, em cada caso."""

    def test_participante_nao_cria_evento(self):
        self.client.force_login(self.part1)
        r = self.client.post(reverse('criar_evento'), {'nome': 'X'})
        self.assertEqual(r.status_code, 200)  # formulário devolvido com erros
        self.assertFalse(r.context['form'].is_valid())
        self.assertEqual(Evento_count(), 2)

    def test_organizador_nao_edita_evento_de_outro(self):
        self.client.force_login(self.org2)
        r = self.client.post(
            reverse('editar_evento', args=[self.evento1.pk]), {'nome': 'Hackeado'},
        )
        self.evento1.refresh_from_db()
        self.assertNotEqual(self.evento1.nome, 'Hackeado')
        self.assertIn(r.status_code, (302, 403))

    def test_ninguem_cancela_inscricao_alheia(self):
        self.inscrever_no_evento(self.part1)
        self.client.force_login(self.part2)
        r = self.client.post(reverse('cancelar_inscricao_evento', args=[self.evento1.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(InscricaoEvento.objects.filter(participante=self.part1).exists())


def Evento_count():
    from eventos.models import Evento
    return Evento.objects.count()
