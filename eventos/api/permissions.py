"""Permissões da API (RF9)."""
from rest_framework import permissions


class IsOrganizadorDoEvento(permissions.BasePermission):
    """Escrita em atividade apenas para o organizador do evento dela."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        organizador = getattr(obj, 'organizador', None) or obj.evento.organizador
        return organizador == request.user

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated
