from django.conf import settings
from django.db import models
from django.db.models import Q, F


class Sala(models.Model):
    """Sala física do campus. Cadastrada apenas pelo Admin."""
    nome = models.CharField(max_length=100)
    bloco = models.CharField(max_length=50)
    capacidade = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'

    def __str__(self):
        return f'{self.nome} (bloco {self.bloco})'


class Evento(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    inicio = models.DateField()
    fim = models.DateField()
    inscricoes_abertas = models.BooleanField(default=True)
    organizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='eventos_organizados',
    )

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'

    def __str__(self):
        return self.nome


class Atividade(models.Model):
    TIPO_CHOICES = [
        ('palestra', 'Palestra'),
        ('treinamento', 'Treinamento'),
        ('apresentacao', 'Apresentação'),
    ]

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name='atividades',
    )
    titulo = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField(blank=True)
    responsavel = models.CharField(max_length=150)
    sala = models.ForeignKey(
        Sala,
        on_delete=models.PROTECT,
        related_name='atividades',
    )
    inicio = models.DateTimeField()
    fim = models.DateTimeField()

    class Meta:
        verbose_name = 'Atividade'
        verbose_name_plural = 'Atividades'
        ordering = ['inicio']

    def __str__(self):
        return f'{self.titulo} — {self.evento.nome}'

    def inscritos_count(self):
        return self.inscricoes.count()

    def vagas_restantes(self):
        """Vagas restantes calculadas do banco, nunca guardadas."""
        return max(self.sala.capacidade - self.inscricoes.count(), 0)

    def lotada(self):
        return self.vagas_restantes() <= 0

    @staticmethod
    def sobrepostos(ini_a, fim_a, ini_b, fim_b):
        """Dois intervalos [ini, fim) se sobrepõem?"""
        return ini_a < fim_b and ini_b < fim_a


class InscricaoEvento(models.Model):
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name='inscricoes',
    )
    participante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inscricoes_evento',
    )
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Inscrição no evento'
        verbose_name_plural = 'Inscrições no evento'
        unique_together = [('evento', 'participante')]

    def __str__(self):
        return f'{self.participante} em {self.evento}'


class InscricaoAtividade(models.Model):
    """Ligada à inscrição no evento: RN4 e RN5 saem quase de graça."""
    inscricao_evento = models.ForeignKey(
        InscricaoEvento,
        on_delete=models.CASCADE,
        related_name='inscricoes_atividades',
    )
    atividade = models.ForeignKey(
        Atividade,
        on_delete=models.CASCADE,
        related_name='inscricoes',
    )
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Inscrição em atividade'
        verbose_name_plural = 'Inscrições em atividade'
        unique_together = [('inscricao_evento', 'atividade')]

    def __str__(self):
        return f'{self.inscricao_evento.participante} em {self.atividade}'
