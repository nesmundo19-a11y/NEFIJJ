from rest_framework.permissions import BasePermission

from .tenancy import is_organization_admin


def is_admin_user(request):
    return request.user.is_authenticated and is_organization_admin(request)


class IsNEFIJJAdmin(BasePermission):
    message = "Se requiere rol de administrador de organización."

    def has_permission(self, request, view):
        return is_admin_user(request)


class IsPlatformSuperAdmin(BasePermission):
    message = "Se requiere rol de superadministrador de plataforma."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser
