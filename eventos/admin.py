from django.contrib import admin

from .models import Sala, Evento, Atividade, InscricaoEvento, InscricaoAtividade


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'bloco', 'capacidade')
    list_filter = ('bloco',)
    search_fields = ('nome', 'bloco')


class AtividadeInline(admin.TabularInline):
    model = Atividade
    extra = 0
    fields = ('titulo', 'tipo', 'responsavel', 'sala', 'inicio', 'fim')


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'inicio', 'fim', 'inscricoes_abertas', 'organizador')
    list_filter = ('inscricoes_abertas', 'organizador')
    search_fields = ('nome', 'descricao')
    inlines = [AtividadeInline]


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'evento', 'sala', 'inicio', 'fim')
    list_filter = ('tipo', 'sala', 'evento')
    search_fields = ('titulo', 'responsavel')


@admin.register(InscricaoEvento)
class InscricaoEventoAdmin(admin.ModelAdmin):
    list_display = ('evento', 'participante', 'data')
    list_filter = ('evento',)
    search_fields = ('participante__username', 'evento__nome')


@admin.register(InscricaoAtividade)
class InscricaoAtividadeAdmin(admin.ModelAdmin):
    list_display = ('atividade', 'inscricao_evento', 'data')
    list_filter = ('atividade__evento', 'atividade')
    search_fields = ('inscricao_evento__participante__username', 'atividade__titulo')
