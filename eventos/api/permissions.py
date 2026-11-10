"""
Permissões da API (RF9).
"""
from rest_framework import permissions


class IsOrganizadorDoEvento(permissions.BasePermission):
    """Escrita em atividade apenas para o organizador do evento dela."""
    message = 'Acesso negado: este evento não é seu.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.evento.organizador == request.user
