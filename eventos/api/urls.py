"""
Rotas da API — tudo sob /api/.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'atividades', views.AtividadeViewSet, basename='atividade')
router.register(r'salas', views.SalaViewSet, basename='sala')

urlpatterns = [
    path('', include(router.urls)),
    path('eventos/', views.EventoListCreate.as_view(), name='api-eventos'),
    path('eventos/<int:pk>/', views.EventoDetail.as_view(), name='api-evento'),
    path('eventos/<int:pk>/programacao/', views.ProgramacaoEventoView.as_view(), name='api-programacao'),
    path('eventos/<int:pk>/inscrever/', views.api_inscrever_evento, name='api-inscrever-evento'),
    path('eventos/<int:pk>/cancelar/', views.api_cancelar_evento, name='api-cancelar-evento'),
    path('atividades/<int:pk>/inscrever/', views.api_inscrever_atividade, name='api-inscrever-atividade'),
    path('atividades/<int:pk>/cancelar/', views.api_cancelar_atividade, name='api-cancelar-atividade'),
    path('agenda/', views.api_agenda, name='api-agenda'),
    path('token/', views.ApiTokenView.as_view(), name='api-token'),
]
