from django.urls import path

from . import views

urlpatterns = [
    path("create/", views.OrganizationCreateView.as_view(), name="organization-create"),
    path("all/my/", views.MyOrganizationListView.as_view(), name="my-organization"),
    path("my/", views.OrganizationDetailView.as_view(), name="my-organization-detail"),
    path("all/members/", views.AllMembershipView.as_view(), name="all-membership"),
]
