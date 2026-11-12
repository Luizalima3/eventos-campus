"""Rotas da API — tudo sob /api/."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView,
)

from . import views

router = DefaultRouter()
router.register('atividades', views.AtividadeViewSet, basename='atividade')

urlpatterns = [
    # Documentação (RF11)
    path('schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),

    # Autenticação por token (RF4)
    path('token/', obtain_auth_token, name='api-token'),

    # Salas
    path('salas/', views.lista_salas, name='api-salas'),

    # Eventos
    path('eventos/', views.EventoListCreate.as_view(), name='api-eventos'),
    path('eventos/<int:pk>/', views.EventoDetail.as_view(), name='api-evento'),
    path('eventos/<int:pk>/programacao/', views.ProgramacaoEventoView.as_view(),
         name='api-programacao'),
    path('eventos/<int:pk>/inscrever/', views.inscrever_evento, name='api-inscrever-evento'),
    path('eventos/<int:pk>/cancelar/', views.cancelar_inscricao_evento,
         name='api-cancelar-evento'),

    # Atividades (ViewSet)
    path('', include(router.urls)),
    path('atividades/<int:pk>/inscrever/', views.inscrever_atividade,
         name='api-inscrever-atividade'),
    path('atividades/<int:pk>/cancelar/', views.cancelar_inscricao_atividade,
         name='api-cancelar-atividade'),

    # Agenda do participante (RF7)
    path('agenda/', views.minha_agenda, name='api-agenda'),
]
