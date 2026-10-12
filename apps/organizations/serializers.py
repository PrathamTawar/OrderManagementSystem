from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Membership, MembershipInvitation, Organization, Role
from .role_utils import assignable_apps, grantable_keys


# * permission list serializer R
class PermissionListSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    can_grant = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "app_label", "codename", "name", "can_grant"]  # noqa: RUF012

    def get_can_grant(self, obj):
        if not hasattr(self, "_grantable"):
            m = self.context["membership"]
            self._grantable = None if m.is_owner else grantable_keys(m)
        return (
            self._grantable is None
            or (obj.content_type.app_label, obj.codename) in self._grantable
        )


# *role serializer R
class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(
        source="content_type.app_label",
        read_only=True,
    )

    class Meta:
        model = Permission
        fields = ["app_label", "codename", "name"]  # noqa: RUF012


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "permissions"]  # noqa: RUF012


# *role serializer W
class PermissionField(serializers.RelatedField):
    queryset = (
        Permission.objects.none()
    )  # RelatedField requires one; lookups happen in the serializer

    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, int):
            raise serializers.ValidationError("Permission must be an integer id.")
        return data  # no DB hit here

    def to_representation(self, value):
        return {
            "id": value.pk,
            # get_for_id is cached in process, so no query per permission
            "app_label": ContentType.objects.get_for_id(
                value.content_type_id
            ).app_label,
            "codename": value.codename,
        }


class RoleCreateSerializer(serializers.ModelSerializer):
    permissions = PermissionField(many=True, required=False)

    class Meta:
        model = Role
        fields = ["id", "name", "permissions"]  # noqa: RUF012

    def validate_permissions(self, ids):
        ids = set(ids)

        # 1. existence + assignable apps in one query; unknown and blocked ids fail the same way
        perms = list(
            Permission.objects.filter(
                id__in=ids, content_type__app_label__in=assignable_apps()
            ).select_related("content_type")
        )
        if missing := ids - {p.id for p in perms}:
            raise serializers.ValidationError(
                f"Invalid permission ids: {sorted(missing)}"
            )

        wanted = {(p.content_type.app_label, p.codename) for p in perms}

        # 2. escalation check, owner is exempt (owner has no role, so never touch it)
        membership = self.context["membership"]
        if not membership.is_owner:
            current = (
                set(
                    self.instance.permissions.values_list(
                        "content_type__app_label", "codename"
                    )
                )
                if self.instance
                else set()
            )
            if (wanted ^ current) - grantable_keys(membership):
                raise serializers.ValidationError(
                    "You cannot grant or remove permissions you do not have"
                )
        return perms  # Permission objects, so ModelSerializer sets the M2M


# *organization serializer W/R
class OrganizationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    phone_number = PhoneNumberField(required=True)

    class Meta:
        model = Organization
        fields = "__all__"


class OrganizationListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="organization.id")
    name = serializers.CharField(source="organization.name")
    email = serializers.EmailField(source="organization.email")
    profile_picture = serializers.URLField(source="organization.profile_picture")
    city = serializers.CharField(source="organization.city")
    state = serializers.CharField(source="organization.state")
    country = serializers.CharField(source="organization.country")
    role = RoleSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = [  # noqa: RUF012
            "id",
            "name",
            "email",
            "profile_picture",
            "city",
            "state",
            "country",
            "role",
            "is_owner",
        ]


# * membership serializer R
class MembershipSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )

    class Meta:
        model = Membership
        fields = [  # noqa: RUF012
            "id",
            "user",
            "role_name",
            "organization_name",
            "is_owner",
        ]

    def get_fields(self):
        fields = super().get_fields()

        for field in fields.values():
            field.read_only = True

        return fields


class MembershipDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )

    class Meta:
        model = Membership
        fields = ["id", "user", "role", "organization_name", "is_owner"]  # noqa: RUF012


# * membership serializer W
class MembershipCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["user", "role"]  # noqa: RUF012

    def validate_role(self, role):
        if not role:
            return role
        organization_id = self.context["organization_id"]

        if role.organization_id != organization_id:
            raise serializers.ValidationError("Invalid role.")

        return role


class InvitationSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", default=None, read_only=True)
    invited_by_name = serializers.CharField(
        source="invited_by.full_name", read_only=True
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = MembershipInvitation
        fields = [  # noqa: RUF012
            "email",
            "full_name",
            "role_name",
            "invited_by",
            "invited_by_name",
            "expires_at",
            "status",
            "accepted_at",
            "created_at",
        ]

    def get_status(self, obj):
        if (
            obj.status == MembershipInvitation.Status.PENDING
            and obj.expires_at <= timezone.now()
        ):
            return MembershipInvitation.Status.EXPIRED

        return obj.status


class InvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipInvitation
        fields = ["email", "full_name", "role"]  # noqa: RUF012

    def validate_role(self, role):
        if not role:
            raise serializers.ValidationError("Role is required.")

        organization_id = self.context["organization_id"]

        if role.organization_id != organization_id:
            raise serializers.ValidationError("Invalid role.")

        return role

    def validate_email(self, email):
        organization_id = self.context["organization_id"]
        if Membership.objects.filter(
            user__email__iexact=email,
            organization_id=organization_id,
        ).exists():
            raise serializers.ValidationError(
                "This user is already a member of the organization."
            )
        return email
