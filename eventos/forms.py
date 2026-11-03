from django import forms

from .models import Evento, Atividade
from .services import validar_atividade


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

        # Regra única em services.validar_atividade — também usada pela API.
        erros = validar_atividade(
            sala=sala, inicio=inicio, fim=fim,
            evento=self.evento_inicial, instance=self.instance,
        )
        for erro in erros:
            raise forms.ValidationError(erro)
        return cleaned
