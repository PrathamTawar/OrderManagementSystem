from django.urls import path

from . import views

urlpatterns = [
    path("", views.OrganizationListCreateView.as_view(), name="organization-list-create"),
    path("my/", views.OrganizationDetailView.as_view(), name="my-organization-detail"),
    path("membership/", views.MembershipListView.as_view(), name="membership-list"),
    path("membership/<int:pk>/", views.MembershipDetailView.as_view(), name="membership-detail"),
    path("membership/my/", views.MembershipOwnDetailView.as_view(), name="my-membership-detail"),
    path("invitation/", views.MembershipInvitationListCreateView.as_view(), name="membership-invitation-list-create"),
    path("invitation/accept/", views.InvitationAcceptView.as_view(), name="invitation-accept"),
    path("role/", views.RoleListCreateView.as_view(), name="role-list-create"),
    path("role/<int:pk>/", views.RoleDetailView.as_view(), name="role-detail"),
    path("permissions/", views.PermissionListView.as_view(), name="permission-list"),
]
