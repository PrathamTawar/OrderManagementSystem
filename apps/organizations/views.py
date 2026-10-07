from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.permissions import HasOrgPermission

from .models import Membership, Organization
from .serializers import OrganizationListSerializer, OrganizationSerializer


class OrganizationCreateView(APIView):
    permission_classes = [IsAuthenticated]  # noqa: RUF012

    def post(self, request):
        serializer = OrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                organization = serializer.save()
                Membership.objects.create(
                    user=request.user, organization=organization, is_owner=True
                )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MyOrganizationListView(APIView):
    permission_classes = [IsAuthenticated]  # noqa: RUF012
    model = Membership

    def get(self, request):
        user = request.user
        organizations = Membership.objects.filter(user=user).select_related(
            "organization", "role"
        )
        serializer = OrganizationListSerializer(organizations, many=True)
        return Response(serializer.data)


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasOrgPermission]  # noqa: RUF012
    model = Organization

    def get_queryset(self, request):
        if pk := int(request.headers.get("X-Organization-Id")):
            return Organization.objects.filter(id=pk).first()
        return Response(
            {"error": "Missing or invalid organization"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get(self, request):
        organization = self.get_queryset(request)
        serializer = OrganizationSerializer(organization)
        return Response(serializer.data)

    def put(self, request):
        organization = self.get_queryset(request)
        serializer = OrganizationSerializer(
            organization, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        organization = self.get_queryset(request)
        organization.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
