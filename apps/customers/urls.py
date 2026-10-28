from django.urls import path

from .views import (
    CustomerDetailView,
    CustomerListCreateView,
    CustomerTypeDetailView,
    CustomerTypeListCreateView,
    Health,
)

urlpatterns = [
    path("", CustomerListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", CustomerDetailView.as_view(), name="detail-update"),
    path("type/", CustomerTypeListCreateView.as_view(), name="type-list-create"),
    path("type/<int:pk>/", CustomerTypeDetailView.as_view(), name="type-detail-update"),
    path("health/", Health.as_view(), name="health"),
]
