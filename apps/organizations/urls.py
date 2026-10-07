from django.urls import path

from . import views

urlpatterns = [
    path(
        "create/", views.OrganizationCreateView.as_view(), name="organization-create"
    ),
]
