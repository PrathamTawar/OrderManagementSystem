from rest_framework.views import APIView
from rest_framework.response import Response


class AccountHealth(APIView):
    def get(self, request):
        return Response({"status": "Account service is healthy."})
