from django.urls import path

from . import views

urlpatterns = [
    path("", views.OrganizationListCreateView.as_view(), name="organization-list-create"),
    path("my/", views.OrganizationDetailView.as_view(), name="my-organization-detail"),
    path("membership/", views.MembershipListView.as_view(), name="membership-list-create"),
    path("invitation/", views.MembershipInvitationListCreateView.as_view(), name="membership-invitation-list-create"),
]
