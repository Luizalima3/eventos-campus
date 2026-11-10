from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import UpdateView

from .forms import EventoForm, AtividadeForm
from .models import Evento, Atividade, InscricaoEvento, InscricaoAtividade
from .services import inscrever_em_atividade
from django.core.exceptions import ValidationError as DjValidationError


# ---------------------------------------------------------------------------
# Páginas públicas
# ---------------------------------------------------------------------------

def lista_eventos(request):
    """Página pública: todos os eventos, com busca."""
    termo = request.GET.get('q', '').strip()
    eventos = Evento.objects.all().order_by('-inicio')
    if termo:
        eventos = eventos.filter(Q(nome__icontains=termo) | Q(descricao__icontains=termo))
    return render(request, 'eventos/lista_eventos.html', {'eventos': eventos, 'termo': termo})


def detalhe_evento(request, pk):
    """Página pública: programação completa com vagas restantes."""
    evento = get_object_or_404(Evento, pk=pk)
    atividades = evento.atividades.all()
    inscricao = None
    if request.user.is_authenticated:
        inscricao = InscricaoEvento.objects.filter(
            evento=evento, participante=request.user
        ).first()
    return render(request, 'eventos/detalhe_evento.html', {
        'evento': evento,
        'atividades': atividades,
        'inscricao': inscricao,
    })


# ---------------------------------------------------------------------------
# Inscrições e cancelamentos
# ---------------------------------------------------------------------------

@login_required
def inscrever_evento(request, pk):
    """RF5: inscrição no evento (POST apenas — ação que altera estado)."""
    evento = get_object_or_404(Evento, pk=pk)
    if request.method != 'POST':
        return redirect('detalhe_evento', pk=evento.pk)
    if not evento.inscricoes_abertas:
        messages.error(request, 'As inscrições deste evento estão encerradas.')
    elif InscricaoEvento.objects.filter(evento=evento, participante=request.user).exists():
        messages.info(request, 'Você já está inscrito neste evento.')
    else:
        InscricaoEvento.objects.create(evento=evento, participante=request.user)
        messages.success(request, 'Inscrição no evento realizada!')
    return redirect('detalhe_evento', pk=evento.pk)


@login_required
def cancelar_inscricao_evento(request, pk):
    """RF7/RN5: sai do evento e, junto, de todas as atividades dele (cascade)."""
    if request.method != 'POST':
        return redirect('detalhe_evento', pk=pk)
    inscricao = InscricaoEvento.objects.filter(
        evento_id=pk, participante=request.user
    ).first()
    if inscricao:
        inscricao.delete()
        messages.success(request, 'Você saiu do evento e de todas as atividades dele.')
    return redirect('detalhe_evento', pk=pk)


@login_required
def inscrever_atividade(request, pk):
    """RF6: inscrição em atividade, com RN1, RN2 e RN4 verificadas no servidor."""
    atividade = get_object_or_404(Atividade, pk=pk)
    evento = atividade.evento
    if request.method != 'POST':
        return redirect('detalhe_evento', pk=evento.pk)

    # RN1, RN2 e RN4 moram em services.inscrever_em_atividade — a MESMA
    # função que a API chama. As regras existem uma única vez.
    try:
        inscrever_em_atividade(request.user, atividade)
    except DjValidationError as e:
        for msg in e.messages:
            messages.error(request, msg)
        return redirect('detalhe_evento', pk=evento.pk)

    messages.success(request, f'Inscrição em "{atividade.titulo}" realizada!')
    return redirect('detalhe_evento', pk=evento.pk)


@login_required
def cancelar_inscricao_atividade(request, pk):
    """RF7: cancela apenas uma atividade; continua inscrito no evento."""
    atividade = Atividade.objects.filter(pk=pk).select_related('evento').first()
    if request.method == 'POST':
        ia = InscricaoAtividade.objects.filter(
            atividade_id=pk, inscricao_evento__participante=request.user
        ).first()
        if ia:
            ia.delete()
            messages.success(request, f'Você saiu da atividade "{atividade.titulo}".')
            return redirect('minha_agenda')
    if atividade:
        return redirect('detalhe_evento', pk=atividade.evento.pk)
    return redirect('minha_agenda')


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

def cadastro(request):
    """RF2: conta pública — recém-criada é apenas participante."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Conta criada! Você já pode se inscrever em eventos.')
            return redirect('lista_eventos')
    else:
        form = UserCreationForm()
    return render(request, 'registration/cadastro.html', {'form': form})


# ---------------------------------------------------------------------------
# Participante
# ---------------------------------------------------------------------------

@login_required
def minha_agenda(request):
    """RF8: atividades de todos os eventos, ordenadas por data e hora."""
    inscricoes_evento = (
        InscricaoEvento.objects.filter(participante=request.user)
        .select_related('evento')
        .order_by('evento__inicio')
    )
    inscricoes_atividade = (
        InscricaoAtividade.objects.filter(inscricao_evento__participante=request.user)
        .select_related('atividade__evento', 'atividade__sala')
        .order_by('atividade__inicio', 'atividade__fim')
    )
    return render(request, 'eventos/minha_agenda.html', {
        'inscricoes_evento': inscricoes_evento,
        'inscricoes_atividade': inscricoes_atividade,
    })


# ---------------------------------------------------------------------------
# Organizador
# ---------------------------------------------------------------------------

@login_required
def meus_eventos(request):
    """RF9: painel do organizador — só os eventos dele."""
    eventos = Evento.objects.filter(organizador=request.user).order_by('-inicio')
    return render(request, 'eventos/meus_eventos.html', {'eventos': eventos})


@login_required
def criar_evento(request):
    """RF4: organizador preenchido pelo sistema, nunca pelo formulário."""
    if request.method == 'POST':
        form = EventoForm(request.POST)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.organizador = request.user
            evento.save()
            messages.success(request, 'Evento criado!')
            return redirect('meus_eventos')
    else:
        form = EventoForm()
    return render(request, 'eventos/form_evento.html', {'form': form, 'titulo': 'Novo evento'})


class EditarEventoView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Proteção por mixin + teste de propriedade: só o organizador do evento."""
    model = Evento
    form_class = EventoForm
    template_name = 'eventos/form_evento.html'
    context_object_name = 'evento'

    def test_func(self):
        return self.get_object().organizador == self.request.user

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Acesso negado: este evento não é seu.')
        return redirect('meus_eventos')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar: {self.object.nome}'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Evento atualizado!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('meus_eventos')


@login_required
def excluir_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if evento.organizador != request.user:
        messages.error(request, 'Acesso negado: este evento não é seu.')
        return redirect('meus_eventos')
    if request.method == 'POST':
        evento.delete()
        messages.success(request, 'Evento excluído.')
        return redirect('meus_eventos')
    return render(request, 'eventos/confirmar_exclusao.html', {'objeto': evento, 'tipo': 'evento'})


@login_required
def criar_atividade(request, evento_pk):
    evento = get_object_or_404(Evento, pk=evento_pk)
    if evento.organizador != request.user:
        messages.error(request, 'Acesso negado: este evento não é seu.')
        return redirect('meus_eventos')
    if request.method == 'POST':
        form = AtividadeForm(request.POST, evento=evento)
        if form.is_valid():
            atividade = form.save(commit=False)
            atividade.evento = evento
            atividade.save()
            messages.success(request, 'Atividade criada!')
            return redirect('detalhe_evento', pk=evento.pk)
    else:
        form = AtividadeForm(evento=evento)
    return render(request, 'eventos/form_atividade.html', {
        'form': form, 'titulo': f'Nova atividade em {evento.nome}',
    })


@login_required
def editar_atividade(request, pk):
    atividade = get_object_or_404(Atividade.objects.select_related('evento'), pk=pk)
    if atividade.evento.organizador != request.user:
        messages.error(request, 'Acesso negado: este evento não é seu.')
        return redirect('meus_eventos')
    if request.method == 'POST':
        form = AtividadeForm(request.POST, instance=atividade, evento=atividade.evento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Atividade atualizada!')
            return redirect('detalhe_evento', pk=atividade.evento.pk)
    else:
        form = AtividadeForm(instance=atividade)
    return render(request, 'eventos/form_atividade.html', {
        'form': form, 'titulo': f'Editar: {atividade.titulo}',
    })


@login_required
def excluir_atividade(request, pk):
    atividade = get_object_or_404(Atividade.objects.select_related('evento'), pk=pk)
    if atividade.evento.organizador != request.user:
        messages.error(request, 'Acesso negado: este evento não é seu.')
        return redirect('meus_eventos')
    evento_pk = atividade.evento.pk
    if request.method == 'POST':
        atividade.delete()
        messages.success(request, 'Atividade excluída.')
        return redirect('detalhe_evento', pk=evento_pk)
    return render(request, 'eventos/confirmar_exclusao.html', {'objeto': atividade, 'tipo': 'atividade'})


@login_required
def participantes_atividade(request, pk):
    """RF9: inscritos de uma atividade — apenas para o organizador do evento."""
    atividade = get_object_or_404(Atividade.objects.select_related('evento', 'sala'), pk=pk)
    if atividade.evento.organizador != request.user:
        messages.error(request, 'Acesso negado: este evento não é seu.')
        return redirect('meus_eventos')
    inscricoes = atividade.inscricoes.select_related(
        'inscricao_evento__participante'
    ).order_by('inscricao_evento__participante__username')
    return render(request, 'eventos/participantes.html', {
        'atividade': atividade, 'inscricoes': inscricoes,
    })
