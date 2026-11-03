from django.urls import path

from . import views

urlpatterns = [
    path('', views.lista_eventos, name='lista_eventos'),
    path('evento/<int:pk>/', views.detalhe_evento, name='detalhe_evento'),
    path('evento/<int:pk>/inscrever/', views.inscrever_evento, name='inscrever_evento'),
    path('evento/<int:pk>/cancelar/', views.cancelar_inscricao_evento, name='cancelar_inscricao_evento'),
    path('atividade/<int:pk>/inscrever/', views.inscrever_atividade, name='inscrever_atividade'),
    path('atividade/<int:pk>/cancelar/', views.cancelar_inscricao_atividade, name='cancelar_inscricao_atividade'),
    path('agenda/', views.minha_agenda, name='minha_agenda'),
    path('meus-eventos/', views.meus_eventos, name='meus_eventos'),
    path('meus-eventos/novo/', views.criar_evento, name='criar_evento'),
    path('meus-eventos/<int:pk>/editar/', views.EditarEventoView.as_view(), name='editar_evento'),
    path('meus-eventos/<int:pk>/excluir/', views.excluir_evento, name='excluir_evento'),
    path('evento/<int:evento_pk>/atividade/nova/', views.criar_atividade, name='criar_atividade'),
    path('atividade/<int:pk>/editar/', views.editar_atividade, name='editar_atividade'),
    path('atividade/<int:pk>/excluir/', views.excluir_atividade, name='excluir_atividade'),
    path('atividade/<int:pk>/participantes/', views.participantes_atividade, name='participantes_atividade'),
    path('conta/cadastro/', views.cadastro, name='cadastro'),
]
