import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from utils.tasks import send_email_task

from .base_view import OrgAPIView
from .models import Membership, MembershipInvitation, Organization
from .serializers import (
    InvitationCreateSerializer,
    InvitationSerializer,
    MembershipDetailSerializer,
    OrganizationListSerializer,
    OrganizationSerializer,
)


def can_assign_role(perm_ids, role):
    """perm_ids is request.org_perm_ids. None means owner, so unrestricted."""
    return perm_ids is None or not role.permissions.exclude(id__in=perm_ids).exists()


class OrganizationListCreateView(APIView):
    permission_classes = [IsAuthenticated]  # noqa: RUF012

    def get(self, request):
        user = request.user
        organizations = Membership.objects.filter(user=user).select_related(
            "organization", "role"
        )
        serializer = OrganizationListSerializer(organizations, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                organization = serializer.save()
                Membership.objects.create(
                    user=request.user, organization=organization, is_owner=True
                )
        except IntegrityError:
            return Response(
                {"error": "Could not create the organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrganizationDetailView(OrgAPIView):
    model = Organization
    serializer_class = OrganizationSerializer
    own_serializer_class = OrganizationSerializer
    org_lookup = "id"

    def get_organization(self, request):
        return self.get_object(pk=request.organization_id)

    def get(self, request):
        organization = self.get_organization(request)
        serializer = self.get_serializer(organization)
        return Response(serializer.data)

    def put(self, request):
        organization = self.get_organization(request)
        serializer = self.get_serializer(organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        organization = self.get_organization(request)
        organization.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MembershipListView(OrgAPIView):
    model = Membership
    serializer_class = MembershipDetailSerializer
    permission_map = {  # noqa: RUF012
        "GET": "organizations.view_membership",
    }

    def get(self, request):
        memberships = self.get_queryset()
        serializer = self.get_serializer(memberships, many=True)
        return Response(serializer.data)


class MembershipInvitationListCreateView(OrgAPIView):
    model = MembershipInvitation
    serializer_class = InvitationSerializer
    create_serializer_class = InvitationCreateSerializer
    expiration_time = 24

    def _expire_pending_invitations(self, organization, email, now):
        MembershipInvitation.objects.filter(
            organization=organization,
            email=email,
            status=MembershipInvitation.Status.PENDING,
            expires_at__lte=now,
        ).update(status=MembershipInvitation.Status.EXPIRED)

    def _create_token(self):
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        return raw_token, token_hash

    def can_assign_role(self, membership, role):
        if membership.is_owner:
            return True
        mine = (
            set(membership.role.permissions.values_list("id", flat=True))
            if membership.role
            else set()
        )
        return set(role.permissions.values_list("id", flat=True)) <= mine

    def get(self, request):
        invitations = self.get_queryset()
        serializer = self.get_serializer(invitations, many=True)
        return Response(serializer.data)

    def post(self, request):
        try:
            serializer = self.get_serializer(
                data=request.data,
                context={"organization_id": request.organization_id},
            )
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            role = data.get("role")
            if role and not can_assign_role(request.org_perm_ids, role):
                raise PermissionDenied(
                    "You cannot invite someone with a role that has permissions you do not have."
                )
            organization = request.org_membership.organization
            now = timezone.now()
            raw_token, token_hash = self._create_token()

            with transaction.atomic():
                now = timezone.now()
                self._expire_pending_invitations(organization, data["email"], now)
                invitation = serializer.save(
                    invited_by=request.user,
                    organization=organization,
                    token_hash=token_hash,
                    expires_at=now + timedelta(hours=self.expiration_time),
                    status=MembershipInvitation.Status.PENDING,
                )

                accept_url = f"{settings.INVITATION_ACCEPT_URL.rstrip('/')}/{raw_token}"
                organization_name = invitation.organization.name
                existing_user = User.objects.filter(
                    email__iexact=invitation.email
                ).exists()

                transaction.on_commit(
                    lambda: send_email_task.delay(
                        subject=f"Invitation to join {organization_name}",
                        message=(
                            f"You have been invited to join {organization_name}.\n"
                            f"Accept your invitation here: {accept_url}"
                        ),
                        recipient_list=[invitation.email],
                        template_path="membership_invitation.html",
                        message_data={
                            "existing_user": existing_user,
                            "invited_by_email": invitation.invited_by.email,
                            "accept_url": accept_url,
                            "organization_name": organization_name,
                        },
                    )
                )
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.__cause__, "diag", None),
                "constraint_name",
                None,
            )

            if constraint_name == "uniq_pend_inv_org_email":
                return Response(
                    {"error": "An active invitation already exists for this user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise

        return Response(
            self.serializer_class(
                invitation,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )
