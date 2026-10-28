from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from apps.accounts.serializers import UserDetailSerializer

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


# * role serializer W
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
    remove_permissions = PermissionField(
        many=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = Role
        fields = ["id", "name", "permissions", "remove_permissions"]  # noqa: RUF012

    def _validate_permissions(self, ids, *, removing=False):
        ids = set(ids)

        perms = list(
            Permission.objects.filter(
                id__in=ids,
                content_type__app_label__in=assignable_apps(),
            ).select_related("content_type")
        )

        if missing := ids - {p.pk for p in perms}:
            raise serializers.ValidationError(
                f"Invalid permission ids: {sorted(missing)}"
            )

        membership = self.context["membership"]

        current_ids = set()
        current_keys = set()

        if self.instance:
            current_permissions = list(
                self.instance.permissions.select_related("content_type")
            )
            current_ids = {p.pk for p in current_permissions}
            current_keys = {
                (p.content_type.app_label, p.codename) for p in current_permissions
            }

        if removing:
            if self.instance is None:
                raise serializers.ValidationError(
                    "Permissions can only be removed when updating a role."
                )

            if missing_from_role := ids - current_ids:
                raise serializers.ValidationError(
                    f"Permissions are not assigned to this role: "
                    f"{sorted(missing_from_role)}"
                )

        if not membership.is_owner:
            requested_keys = {(p.content_type.app_label, p.codename) for p in perms}
            grantable = grantable_keys(membership)

            if removing:
                forbidden = requested_keys - grantable
            else:
                forbidden = (requested_keys - current_keys) - grantable

            if forbidden:
                action = "remove" if removing else "grant"
                raise serializers.ValidationError(
                    f"You cannot {action} permissions you do not have "
                    "permission to manage."
                )

        return perms

    def validate_permissions(self, ids):
        return self._validate_permissions(ids)

    def validate_remove_permissions(self, ids):
        return self._validate_permissions(ids, removing=True)

    def validate(self, attrs):
        if self.instance is None and "remove_permissions" in attrs:
            raise serializers.ValidationError(
                {
                    "remove_permissions": (
                        "Permissions can only be removed when updating a role."
                    )
                }
            )

        added = {p.pk for p in attrs.get("permissions", [])}
        removed = {p.pk for p in attrs.get("remove_permissions", [])}

        if added & removed:
            raise serializers.ValidationError(
                {
                    "permissions": (
                        "A permission cannot be added and removed in the same request."
                    )
                }
            )

        return attrs

    def update(self, instance, validated_data):
        membership = self.context["membership"]

        permissions = validated_data.pop("permissions", None)
        remove_permissions = validated_data.pop("remove_permissions", None)

        validated_data["last_updated_by"] = membership

        with transaction.atomic():
            instance = super().update(instance, validated_data)

            if remove_permissions:
                instance.permissions.remove(*remove_permissions)

            if permissions:
                instance.permissions.add(*permissions)

        return instance

    def create(self, validated_data):
        membership = self.context["membership"]

        validated_data.pop("remove_permissions", None)
        validated_data["organization"] = membership.organization
        validated_data["created_by"] = membership

        return super().create(validated_data)


# * membership serializer R
class MembershipListSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    created_by_name = serializers.CharField(
        source="created_by.user.full_name", read_only=True
    )
    last_updated_by_name = serializers.CharField(
        source="last_updated_by.user.full_name", read_only=True
    )

    class Meta:
        model = Membership
        fields = [  # noqa: RUF012
            "id",
            "user_name",
            "role_name",
            "organization_name",
            "created_by_name",
            "last_updated_by_name",
            "is_owner",
        ]

    def get_fields(self):
        fields = super().get_fields()

        for field in fields.values():
            field.read_only = True

        return fields


class MembershipActorSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user_name", "role_name", "is_owner"]  # noqa: RUF012


# * role serializer R
class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(
        source="content_type.app_label",
        read_only=True,
    )

    class Meta:
        model = Permission
        fields = ["id", "app_label", "codename", "name"]  # noqa: RUF012


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.user.full_name", read_only=True
    )
    last_updated_by_name = serializers.CharField(
        source="last_updated_by.user.full_name", read_only=True
    )

    class Meta:
        model = Role
        fields = [  # noqa: RUF012
            "id",
            "name",
            "permissions",
            "created_by_name",
            "last_updated_by_name",
            "created_at",
            "updated_at",
        ]


class RoleListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.user.full_name", read_only=True
    )

    class Meta:
        model = Role
        fields = ["id", "name", "created_by_name", "created_at"]  # noqa: RUF012


# * membership serializer R
class MembershipDetailSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    created_by = MembershipActorSerializer(read_only=True)
    last_updated_by = MembershipActorSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = [  # noqa: RUF012
            "id",
            "user",
            "role",
            "organization_name",
            "created_by",
            "last_updated_by",
            "is_owner",
        ]


class MembershipOwnDetailSerializer(MembershipListSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    created_by_name = serializers.CharField(
        source="created_by.user.full_name", read_only=True
    )
    last_updated_by_name = serializers.CharField(
        source="last_updated_by.user.full_name", read_only=True
    )

    class Meta:
        model = Membership
        fields = [  # noqa: RUF012
            "id",
            "user",
            "role_name",
            "organization_name",
            "created_by_name",
            "last_updated_by_name",
            "created_at",
            "updated_at",
            "is_owner",
        ]


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
    role_name = serializers.CharField(source="role.name", read_only=True)

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
            "role_name",
            "is_owner",
        ]


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


class MembershipUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["role", "is_owner"]  # noqa: RUF012

    def validate_is_owner(self, value):
        membership = self.context["membership"]
        if value and not membership.is_owner:
            raise serializers.ValidationError("You cannot change this.")
        return value

    def update(self, instance, validated_data):
        membership = self.context["membership"]

        validated_data["last_updated_by"] = membership
        return super().update(instance, validated_data)


# * invitation serializer W/R
class InvitationSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", default=None, read_only=True)
    invited_by_name = serializers.CharField(
        source="invited_by.user.full_name", read_only=True
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
