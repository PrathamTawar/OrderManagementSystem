from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


from .base_view import OrgAPIView
from .models import Membership, Organization
from .serializers import (
    MembershipDetailSerializer,
    MembershipSerializer,
    OrganizationListSerializer,
    OrganizationSerializer,
)


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


class OrganizationDetailView(OrgAPIView):
    model = Organization
    serializer_class = OrganizationSerializer
    own_serializer_class = OrganizationSerializer
    org_lookup = "id"

    def get(self, request):
        organization = self.get_queryset().get()
        serializer = self.get_serializer(organization)
        return Response(serializer.data)

    def put(self, request):
        organization = self.get_queryset().get()
        serializer = self.get_serializer(organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        organization = self.get_queryset().get()
        organization.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AllMembershipView(OrgAPIView):
    model = Membership
    serializer_class = MembershipDetailSerializer
    own_serializer_class = MembershipSerializer

    def get(self, request):
        memberships = self.get_queryset()
        serializer = self.get_serializer(memberships, many=True)
        return Response(serializer.data)
