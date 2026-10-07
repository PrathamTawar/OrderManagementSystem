from django.contrib.auth.models import Permission
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from .models import Membership, Organization, Role


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
    queryset = Permission.objects.select_related("content_type")

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                "Permission must contain app_label and codename."
            )

        app_label = data.get("app_label")
        codename = data.get("codename")

        if not app_label or not codename:
            raise serializers.ValidationError(
                "Both app_label and codename are required."
            )

        try:
            return self.get_queryset().get(
                content_type__app_label=app_label,
                codename=codename,
            )
        except Permission.DoesNotExist as e:
            raise serializers.ValidationError(
                f"Invalid permission: {app_label}.{codename}"
            ) from e

    def to_representation(self, value):
        return {
            "app_label": value.content_type.app_label,
            "codename": value.codename,
        }


class RoleCreateSerializer(serializers.ModelSerializer):
    permissions = PermissionField(many=True, required=False)

    class Meta:
        model = Role
        fields = ["id", "name", "permissions"]  # noqa: RUF012


# * membership serializer R
class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()

        for field in fields.values():
            field.read_only = True

        return fields


# * membership serializer W
class MembershipCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["user", "organization", "role"]  # noqa: RUF012

    def validate_role(self, role):
        if not role:
            return role
        organization = self.context["organization"]

        if role.organization_id != organization.id:
            raise serializers.ValidationError("Invalid role.")

        return role


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
        fields = ["id", "name", "email", "profile_picture", "city", "state", "country", "role", "is_owner"]  # noqa: RUF012
