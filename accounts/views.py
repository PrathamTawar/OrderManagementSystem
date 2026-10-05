from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import UserSerializer


class UserListView(APIView):
    Permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            try:
                user = User.objects.get(pk=pk)
                serializer = UserSerializer(user)
                return Response(serializer.data, status=200)
            except User.DoesNotExist:
                return Response({"error": "User not found."}, status=404)

        if request.user.is_superuser:
            users = User.objects.all()
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data, status=200)
        else:
            return Response(
                {"error": "You do not have permission to view this resource."},
                status=403,
            )


class SignUpView(APIView):
    def post(self, request):
        data = request.data
        serializer = UserSerializer(data=data)
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

        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
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
