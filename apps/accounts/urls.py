from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AccountHealth, SignInView, SignUpView, UserDetailView, UserListView

urlpatterns = [
    path("health/", AccountHealth.as_view(), name="account_health"),
    path("user/list/", UserListView.as_view(), name="user_list"),
    path("user/detail/", UserDetailView.as_view(), name="user_detail"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signin"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
