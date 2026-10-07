# permissions.py
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission

from apps.organizations.models import Membership

ORG_HEADER = "X-Organization-Id"

METHOD_PREFIX = {
    "GET": "view",
    "HEAD": "view",
    "POST": "add",
    "PUT": "change",
    "PATCH": "change",
    "DELETE": "delete",
}


def get_organization_id(request):
    raw = request.headers.get(ORG_HEADER)
    try:
        organization_id = int(raw)
    except (TypeError, ValueError) as e:
        raise ValidationError({ORG_HEADER: "Missing or invalid organization id."})from e
    if organization_id <= 0:
        raise ValidationError({ORG_HEADER: "Missing or invalid organization id."})
    return organization_id


class HasOrgPermission(BasePermission):
    """
    View attributes (checked in this order):

    permission_map       {"POST": "organizations.add_membership"}  per-method override
    required_permission  "organizations.add_membership"            one permission for the whole view
    model                Role                                      auto-map: METHOD -> app_label.prefix_modelname

    If none resolves, access is denied.
    """

    def _required(self, request, view):
        method = request.method

        perm_map = getattr(view, "permission_map", None) or {}
        if method in perm_map:
            return perm_map[method]

        if explicit := getattr(view, "required_permission", None):
            return explicit

        model = getattr(view, "model", None)
        prefix = METHOD_PREFIX.get(method)
        if model and prefix:
            meta = model._meta
            return f"{meta.app_label}.{prefix}_{meta.model_name}"

        return None

    def has_permission(self, request, view):
        if request.method == "OPTIONS":
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        required = self._required(request, view)

        if not isinstance(required, str) or required.count(".") != 1:
            return False

        app_label, codename = required.split(".", 1)

        if not app_label or not codename:
            return False

        organization_id = get_organization_id(request)

        membership = (
            Membership.objects
            .select_related("role")
            .filter(
                user=request.user,
                organization_id=organization_id,
            )
            .first()
        )

        if membership is None:
            return False

        request.organization_id = organization_id

        if membership.is_owner:
            return True

        if membership.role is None:
            return False

        if membership.role.organization_id != organization_id:
            return False

        return membership.role.permissions.filter(
            content_type__app_label=app_label,
            codename=codename,
        ).exists()
