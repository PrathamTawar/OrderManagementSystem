from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.AccountHealth.as_view()),
    path("user/", views.UserListView.as_view()),
    path("user/<int:pk>/", views.UserListView.as_view()),
    path("signup/", views.SignUpView.as_view()),
    path("signin/", views.SignInView.as_view()),
]
