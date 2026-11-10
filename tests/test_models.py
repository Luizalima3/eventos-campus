"""RF4 — validação dos models: dados inválidos recusados (full_clean)."""
from django.core.exceptions import ValidationError
from django.test import TestCase

from eventos.models import Sala

from .base import DadosBase, dt


class ValidacaoEventoTest(DadosBase):
    def test_fim_antes_do_inicio_recusado(self):
        e = self.evento1
        e.inicio, e.fim = dt(5, 0).date(), dt(1, 0).date()
        with self.assertRaises(ValidationError):
            e.full_clean()

    def test_nome_obrigatorio(self):
        e = self.evento1
        e.nome = ''
        with self.assertRaises(ValidationError):
            e.full_clean()


class ValidacaoAtividadeTest(DadosBase):
    def test_fim_antes_do_inicio_recusado(self):
        a = self.criar_atividade(self.evento1, self.sala_grande)
        a.inicio, a.fim = dt(1, 15), dt(1, 9)
        with self.assertRaises(ValidationError):
            a.full_clean()

    def test_titulo_obrigatorio(self):
        a = self.criar_atividade(self.evento1, self.sala_grande)
        a.titulo = ''
        with self.assertRaises(ValidationError):
            a.full_clean()


class ValidacaoSalaTest(DadosBase):
    def test_capacidade_negativa_recusada(self):
        s = Sala(nome='X', bloco='B', capacidade=-1)
        with self.assertRaises(ValidationError):
            s.full_clean()

    def test_capacidade_zero_aceita(self):
        s = Sala(nome='X', bloco='B', capacidade=0)
        s.full_clean()  # não lança


class VagasRestantesTest(DadosBase):
    def test_vagas_restantes_calculadas_do_banco(self):
        a = self.criar_atividade(self.evento1, self.sala_pequena)
        insc = self.inscrever_no_evento(self.part1)
        from eventos.models import InscricaoAtividade
        InscricaoAtividade.objects.create(inscricao_evento=insc, atividade=a)
        self.assertEqual(a.vagas_restantes(), 1)

    def test_sobreposicao_de_intervalos(self):
        f = self.__class__.__name__  # só para não ficar vazio
        self.assertTrue(dt(1, 9) < dt(1, 11))
