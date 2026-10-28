from django.urls import path

from .views import (
    InvitationAcceptView,
    MembershipDetailView,
    MembershipInvitationListCreateView,
    MembershipListView,
    MembershipOwnDetailView,
    OrganizationDetailView,
    OrganizationListCreateView,
    PermissionListView,
    RoleDetailView,
    RoleListCreateView,
)

urlpatterns = [
    path("", OrganizationListCreateView.as_view(), name="organization-list-create"),
    path("my/", OrganizationDetailView.as_view(), name="my-organization-detail"),
    path("membership/", MembershipListView.as_view(), name="membership-list"),
    path(
        "membership/<int:pk>/", MembershipDetailView.as_view(), name="membership-detail"
    ),
    path(
        "membership/my/", MembershipOwnDetailView.as_view(), name="my-membership-detail"
    ),
    path(
        "invitation/",
        MembershipInvitationListCreateView.as_view(),
        name="membership-invitation-list-create",
    ),
    path(
        "invitation/accept/", InvitationAcceptView.as_view(), name="invitation-accept"
    ),
    path("role/", RoleListCreateView.as_view(), name="role-list-create"),
    path("role/<int:pk>/", RoleDetailView.as_view(), name="role-detail"),
    path("permissions/", PermissionListView.as_view(), name="permission-list"),
]
