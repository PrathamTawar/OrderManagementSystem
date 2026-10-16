import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import SignupSerializer
from utils.tasks import send_email_task

from .base_view import OrgAPIView
from .models import Membership, MembershipInvitation, Organization, Role
from .role_utils import assignable_apps, grantable_keys
from .serializers import (
    InvitationCreateSerializer,
    InvitationSerializer,
    MembershipCreateSerializer,
    MembershipDetailSerializer,
    MembershipListSerializer,
    MembershipOwnDetailSerializer,
    MembershipUpdateSerializer,
    OrganizationListSerializer,
    OrganizationSerializer,
    PermissionListSerializer,
    RoleCreateSerializer,
    RoleListSerializer,
    RoleSerializer,
)


def can_assign_role(membership, role):
    if membership.is_owner:
        return True
    target = set(role.permissions.values_list("content_type__app_label", "codename"))
    return target <= grantable_keys(membership)


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
    serializer_class = MembershipListSerializer
    permission_map = {  # noqa: RUF012
        "GET": "organizations.view_membership",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "user",
                "organization",
                "role",
                "created_by__user",
                "last_updated_by__user",
            )
        )

    def get(self, request):
        memberships = self.get_queryset()
        serializer = self.get_serializer(memberships, many=True)
        return Response(serializer.data)


class MembershipDetailView(OrgAPIView):
    model = Membership
    serializer_class = MembershipDetailSerializer
    create_serializer_class = MembershipCreateSerializer
    update_serializer_class = MembershipUpdateSerializer
    permission_map = {  # noqa: RUF012
        "GET": "organizations.view_membership",
        "PUT": "organizations.edit_membership",
        "DELETE": "organizations.delete_membership",
    }

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related(
                "user",
                "organization",
                "role",
                "role__created_by__user",
                "role__last_updated_by__user",
                "created_by__user",
                "created_by__role",
                "last_updated_by__user",
                "last_updated_by__role",
            )
        )

        # Only the full serializer returns the role's permissions.
        if self.request.org_scope == "all":
            queryset = queryset.prefetch_related(
                Prefetch(
                    "role__permissions",
                    queryset=Permission.objects.select_related("content_type"),
                )
            )

        return queryset

    def get(self, request, pk):
        membership = self.get_object(pk=pk)
        serializer = self.get_serializer(membership)
        return Response(serializer.data)

    def put(self, request, pk):
        membership = self.get_object(pk=pk)
        serializer = self.get_serializer(
            membership,
            data=request.data,
            partial=True,
            context={"membership": request.org_membership},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        membership = self.get_object(pk=pk)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MembershipOwnDetailView(OrgAPIView):
    model = Membership
    serializer_class = MembershipOwnDetailSerializer
    own_serializer_class = MembershipOwnDetailSerializer

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "user",
                "organization",
                "role",
                "role__created_by__user",
                "role__last_updated_by__user",
                "created_by__user",
                "created_by__role",
                "last_updated_by__user",
                "last_updated_by__role",
            )
        )

    def get(self, request):
        membership = request.org_membership
        serializer = self.get_serializer(membership)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
            if role and not can_assign_role(request.org_membership, role):
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
                    invited_by=request.org_membership,
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

                message_data = {
                    "existing_user": existing_user,
                    "invited_by_email": request.user.email,
                    "accept_url": accept_url,
                    "organization_name": organization_name,
                }

                transaction.on_commit(
                    lambda: send_email_task.delay(
                        subject=f"Invitation to join {organization_name}",
                        message=(
                            f"You have been invited to join {organization_name}.\n"
                            f"Accept your invitation here: {accept_url}"
                        ),
                        recipient_list=[invitation.email],
                        template_path="membership_invitation.html",
                        message_data=message_data,
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


class RoleListCreateView(OrgAPIView):
    model = Role
    serializer_class = RoleListSerializer
    create_serializer_class = RoleCreateSerializer
    update_serializer_class = RoleCreateSerializer

    def get(self, request):
        roles = self.get_queryset()
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)

    def post(self, request):
        try:
            with transaction.atomic():
                serializer = self.get_serializer(
                    data=request.data, context={"membership": request.org_membership}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save(organization_id=request.organization_id)
        except IntegrityError:
            return Response(
                {"error": "Role already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RoleDetailView(OrgAPIView):
    model = Role
    serializer_class = RoleSerializer
    create_serializer_class = RoleCreateSerializer
    update_serializer_class = RoleCreateSerializer
    permission_map = {  # noqa: RUF012
        "GET": "organizations.view_role",
        "PUT": "organizations.edit_role",
        "DELETE": "organizations.delete_role",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("organization", "created_by", "last_updated_by")
        )

    def get(self, request, pk):
        role = self.get_object(pk=pk)
        serializer = self.get_serializer(role)
        return Response(serializer.data)

    def put(self, request, pk):
        role = self.get_object(pk=pk)
        serializer = self.get_serializer(
            role,
            data=request.data,
            partial=True,
            context={"membership": request.org_membership},
        )
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        return Response(self.serializer_class(role).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        role = self.get_object(pk=pk)
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PermissionListView(OrgAPIView):
    required_permission = "organizations.add_role"
    serializer_class = PermissionListSerializer

    def get(self, request):
        perms = (
            Permission.objects.filter(content_type__app_label__in=assignable_apps())
            .select_related("content_type")
            .order_by("content_type__app_label", "codename")
        )
        return Response(
            PermissionListSerializer(
                perms, many=True, context={"membership": request.org_membership}
            ).data
        )


class InvitationAcceptView(APIView):
    permission_classes = [AllowAny]  # noqa: RUF012

    def get_invitation(self, request, *, for_update=False):
        raw_token = request.headers.get("X-Invitation-Token")

        if not raw_token:
            raise ValidationError("Missing or invalid invitation token.")

        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        invitations = MembershipInvitation.objects.filter(
            token_hash=token_hash,
            status=MembershipInvitation.Status.PENDING,
            expires_at__gt=timezone.now(),
        )

        if for_update:
            invitations = invitations.select_for_update()

        invitation = invitations.first()

        if invitation is None:
            raise ValidationError("Invitation has expired or already accepted.")

        return invitation

    def get(self, request):
        invitation = self.get_invitation(request)
        serializer = InvitationSerializer(invitation)
        return Response(serializer.data)

    def post(self, request):
        try:
            with transaction.atomic():
                # Lock and validate the invitation inside the transaction.
                invitation = self.get_invitation(
                    request,
                    for_update=True,
                )

                if request.user.is_authenticated:
                    # EXISTING AUTHENTICATED USER
                    user = request.user

                    if (
                        user.email or ""
                    ).strip().casefold() != invitation.email.strip().casefold():
                        raise PermissionDenied(
                            "This invitation belongs to a different "
                            "email address. Sign in with the invited account."
                        )

                else:
                    # UNAUTHENTICATED USER
                    if User.objects.filter(email__iexact=invitation.email).exists():
                        return Response(
                            {
                                "code": "account_exists",
                                "detail": (
                                    "An account already exists for this "
                                    "email. Sign in to accept the invitation."
                                ),
                            },
                            status=status.HTTP_409_CONFLICT,
                        )

                    # NEW USER: do not trust client-supplied invitation details.
                    data = request.data.copy()
                    data["email"] = invitation.email
                    data["full_name"] = invitation.full_name

                    user_serializer = SignupSerializer(data=data)
                    user_serializer.is_valid(raise_exception=True)
                    user = user_serializer.save()

                # Create membership for either type of user.
                membership_serializer = MembershipCreateSerializer(
                    data={
                        "user": user.pk,
                        "role": invitation.role_id,
                    },
                    context={
                        "organization_id": invitation.organization_id,
                    },
                )
                membership_serializer.is_valid(raise_exception=True)
                membership_serializer.save(
                    organization=invitation.organization,
                    created_by=invitation.invited_by,
                )

                invitation.status = MembershipInvitation.Status.ACCEPTED
                invitation.accepted_at = timezone.now()
                invitation.save(update_fields=["status", "accepted_at"])

        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "Unable to accept invitation. The account or "
                        "membership may already exist, or the invitation "
                        "may have been consumed."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {"detail": "Invitation accepted successfully."},
            status=status.HTTP_201_CREATED,
        )
