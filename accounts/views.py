from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import SignupSerializer, UserSerializer, UserUpdateSerializer


class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class UserListView(APIView):
    permission_classes = [IsAuthenticated]  # noqa: RUF012

    def get(self, request):
        if request.user.is_superuser:
            users = User.objects.all()
            paginator = UserPagination()
            page = paginator.paginate_queryset(users, request, view=self)
            serializer = UserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        else:
            return Response(
                {"error": "You do not have permission to view this resource."},
                status=403,
            )


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]  # noqa: RUF012

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=200)

    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"message": "User deleted successfully."}, status=204)


class SignUpView(APIView):
    def post(self, request):
        data = request.data
        serializer = SignupSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "user": serializer.data,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                status=201,
            )
        return Response(serializer.errors, status=400)


class SignInView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Credentials are required."}, status=400
            )

        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                user.last_login = timezone.now()
                user.save(update_fields=["last_login"])
                return Response(
                    {
                        "user": UserSerializer(user).data,
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    status=200,
                )
            else:
                return Response({"error": "Invalid credentials."}, status=401)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)


class AccountHealth(APIView):
    def get(self, request):
        return Response({"status": "Account service is healthy."}, status=200)
