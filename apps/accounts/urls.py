from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("health/", views.AccountHealth.as_view(), name="account_health"),
    path("user/list/", views.UserListView.as_view(), name="user_list"),
    path("user/detail/", views.UserDetailView.as_view(), name="user_detail"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("signin/", views.SignInView.as_view(), name="signin"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
