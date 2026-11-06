from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import Organization, OrganizationMembership


ORGANIZATION_HEADER = "HTTP_X_ORGANIZATION_ID"


def _requested_organization_id(request):
    value = request.META.get(ORGANIZATION_HEADER)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"organization": "El identificador de organización no es válido."}) from exc


def get_active_membership(request):
    if request.user.is_superuser:
        return None

    memberships = OrganizationMembership.objects.filter(
        user=request.user,
        is_active=True,
        organization__status=Organization.Status.ACTIVE,
    ).select_related("organization")
    requested_id = _requested_organization_id(request)
    if requested_id is not None:
        membership = memberships.filter(organization_id=requested_id).first()
        if membership is None:
            raise PermissionDenied("No tienes acceso a esa organización.")
        return membership

    memberships = list(memberships[:2])
    if not memberships:
        raise PermissionDenied("La cuenta no tiene una organización activa.")
    if len(memberships) > 1:
        raise ValidationError(
            {"organization": "Selecciona una organización mediante X-Organization-ID."}
        )
    return memberships[0]


def get_selected_organization(request):
    requested_id = _requested_organization_id(request)
    if request.user.is_superuser:
        if requested_id is None:
            return None
        try:
            organization = Organization.objects.get(pk=requested_id)
        except Organization.DoesNotExist as exc:
            raise NotFound("La organización no existe.") from exc
        request._selected_organization = organization
        return organization

    organization = get_active_membership(request).organization
    request._selected_organization = organization
    return organization


def get_request_role(request):
    if request.user.is_superuser:
        return "superadmin"
    return get_active_membership(request).role


def is_organization_admin(request):
    return request.user.is_superuser or get_request_role(request) == OrganizationMembership.Role.ADMIN


def require_active_organization(request):
    organization = get_selected_organization(request)
    if organization is None:
        raise ValidationError(
            {"organization": "Selecciona una organización para esta operación."}
        )
    if not organization.is_active:
        raise PermissionDenied("La organización está suspendida.")
    return organization


def scope_to_organization(queryset, request, field="organization_id"):
    organization = get_selected_organization(request)
    if organization is None:
        return queryset
    return queryset.filter(**{field: organization.pk})
