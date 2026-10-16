from django.urls import path

from . import views

urlpatterns = [
    path("", views.CustomerListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", views.CustomerDetailView.as_view(), name="detail-update"),
    path("type/", views.CustomerTypeListCreateView.as_view(), name="type-list-create"),
    path("type/<int:pk>/", views.CustomerTypeDetailView.as_view(), name="type-detail-update"),
    path("health/", views.Health.as_view(), name="health"),
]
