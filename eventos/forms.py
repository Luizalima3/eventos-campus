from django import forms

from .models import Evento, Atividade


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ['nome', 'descricao', 'inicio', 'fim', 'inscricoes_abertas']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fim': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('inicio', 'fim'):
            self.fields[campo].input_formats = ['%Y-%m-%d']

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('inicio')
        fim = cleaned.get('fim')
        if inicio and fim and fim < inicio:
            raise forms.ValidationError('A data de fim não pode vir antes da de início.')
        return cleaned


class AtividadeForm(forms.ModelForm):
    class Meta:
        model = Atividade
        fields = ['titulo', 'tipo', 'descricao', 'responsavel', 'sala', 'inicio', 'fim']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'fim': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, evento=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.evento_inicial = evento
        for campo in ('inicio', 'fim'):
            self.fields[campo].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M']

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('inicio')
        fim = cleaned.get('fim')
        sala = cleaned.get('sala')

        if fim and inicio and fim < inicio:
            raise forms.ValidationError('O fim não pode vir antes do início.')

        # A atividade precisa acontecer dentro do período do evento.
        evento = self.evento_inicial
        if evento and inicio and fim:
            if inicio.date() < evento.inicio or fim.date() > evento.fim:
                raise forms.ValidationError(
                    'A atividade precisa acontecer dentro do período do evento '
                    f'({evento.inicio.strftime("%d/%m/%Y")} a {evento.fim.strftime("%d/%m/%Y")}).'
                )

            # RN3: sala ocupada — contra TODAS as atividades, de qualquer evento.
            conflito = Atividade.objects.filter(
                sala=sala,
                inicio__lt=fim,
                fim__gt=inicio,
            )
            if self.instance.pk:
                conflito = conflito.exclude(pk=self.instance.pk)
            if conflito.exists():
                nomes = ', '.join(a.titulo for a in conflito)
                raise forms.ValidationError(
                    f'A sala {sala.nome} já está ocupada nesse horário (atividade: {nomes}).'
                )
        return cleaned
