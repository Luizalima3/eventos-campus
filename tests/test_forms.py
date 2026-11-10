"""RF9 — formulário instanciado diretamente, sem passar por view."""
from django import forms

from eventos.forms import EventoForm, AtividadeForm
from .base import DadosBase, dt, HOJE


class EventoFormTest(DadosBase):
    def test_form_valido_e_cleaned_data(self):
        form = EventoForm(data={
            'nome': 'Hackathon', 'descricao': '',
            'inicio': str(HOJE), 'fim': str(HOJE), 'inscricoes_abertas': 'on',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['nome'], 'Hackathon')

    def test_form_com_fim_antes_do_inicio_e_invalido(self):
        form = EventoForm(data={
            'nome': 'X', 'inicio': str(HOJE), 'fim': str(HOJE), 'inscricoes_abertas': 'on',
        })
        # fim == inicio hoje, então inverta
        from datetime import timedelta
        form = EventoForm(data={
            'nome': 'X',
            'inicio': str(HOJE + timedelta(days=3)),
            'fim': str(HOJE),
            'inscricoes_abertas': 'on',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)


class AtividadeFormTest(DadosBase):
    def _dados(self, sala, dia=1, h_ini=9, h_fim=11):
        return {
            'titulo': 'Palestra', 'tipo': 'palestra', 'descricao': '',
            'responsavel': 'Prof', 'sala': sala.pk,
            'inicio': f'{dt(dia, h_ini):%Y-%m-%dT%H:%M}',
            'fim': f'{dt(dia, h_fim):%Y-%m-%dT%H:%M}',
        }

    def test_form_valido_is_true_e_cleaned_data_tem_titulo(self):
        form = AtividadeForm(data=self._dados(self.sala_grande), evento=self.evento1)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['titulo'], 'Palestra')
        self.assertEqual(form.cleaned_data['sala'], self.sala_grande)

    def test_rn3_sala_ocupada_e_recusada_pelo_formulario(self):
        self.criar_atividade(self.evento1, self.sala_grande, 'Ocupante')
        form = AtividadeForm(data=self._dados(self.sala_grande), evento=self.evento1)
        self.assertFalse(form.is_valid())
        self.assertIn('já está ocupada', str(form.errors))

    def test_erros_mencionam_horario_quando_fim_antes_do_inicio(self):
        form = AtividadeForm(data=self._dados(self.sala_grande, h_ini=11, h_fim=9),
                             evento=self.evento1)
        self.assertFalse(form.is_valid())
        self.assertIn('fim', str(form.errors).lower())
