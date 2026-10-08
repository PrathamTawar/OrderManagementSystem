from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.permissions import HasOrgPermission


class OrgAPIView(APIView):
    permission_classes = [IsAuthenticated, HasOrgPermission]  # noqa: RUF012

    model = None

    """
    Serializer used when the user has organization-wide access.

    Example:
    A user with `view_membership` gets the full membership serializer.
    """
    serializer_class = None

    """
    Serializer used when the user has own-only access.

    Example:
    A user with `view_own_membership` gets the limited membership
    serializer.
    """
    own_serializer_class = None

    """
    Field used to restrict objects to the current organization.

    Example:
    Membership.organization_id
    Role.organization_id

    Organization itself uses:
    org_lookup = "id"
    """
    org_lookup = "organization_id"

    """
    Field used when org_scope == "own".

    Membership -> user
    Some other model might use -> created_by
    Another model might use -> assigned_to
    """
    owner_field = "user"

    def get_serializer_class(self):
        """
        Return the serializer class based on the user's organization scope.

        If the user has own-only access, `own_serializer_class` is used.

        If the user has organization-wide access, `serializer_class`
        is used.

        `HasOrgPermission` sets `request.org_scope` to either:

        "all" -> organization-wide access
        "own" -> own-only access
        """
        if self.request.org_scope == "own":
            if self.own_serializer_class is None:
                raise AttributeError(
                    f"{self.__class__.__name__} must define 'own_serializer_class'."
                )

            return self.own_serializer_class

        if self.serializer_class is None:
            raise AttributeError(
                f"{self.__class__.__name__} must define 'serializer_class'."
            )

        return self.serializer_class

    def get_serializer(self, *args, **kwargs):
        """
        Return an instance of the serializer appropriate for the
        user's organization scope.

        The serializer is selected automatically by get_serializer_class().
        """
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    def get_queryset(self):
        """
        Return the queryset scoped to the current organization.

        If HasOrgPermission determined that the user's permission is
        organization-wide, return all objects in the organization.

        If it determined that the permission is own-only, return only
        objects belonging to the current user.
        """
        if self.model is None:
            raise AttributeError(f"{self.__class__.__name__} must define 'model'.")

        qs = self.model.objects.filter(
            **{
                self.org_lookup: self.request.organization_id,
            }
        )

        if self.request.org_scope == "own":
            qs = qs.filter(
                **{
                    self.owner_field: self.request.user,
                }
            )

        return qs

    def get_object(self, pk):
        """
        Get an object using the already organization/scope-restricted
        queryset.

        This is important because an own-scoped user cannot bypass the
        scope simply by supplying another object's primary key.
        """
        return get_object_or_404(
            self.get_queryset(),
            pk=pk,
        )
