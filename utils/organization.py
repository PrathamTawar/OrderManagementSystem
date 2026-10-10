from rest_framework.exceptions import ValidationError

ORG_HEADER = "X-Organization-Id"


def get_organization_id(request):
    if hasattr(request, "organization_id"):
        return request.organization_id

    error = {ORG_HEADER: "Missing or invalid organization id"}
    raw = request.headers.get(ORG_HEADER)

    try:
        organization_id = int(raw)
    except (TypeError, ValueError) as e:
        raise ValidationError(error) from e

    if organization_id <= 0:
        raise ValidationError(error)

    request.organization_id = organization_id
    return organization_id
