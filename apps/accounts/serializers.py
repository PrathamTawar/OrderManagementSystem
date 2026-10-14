from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True}}  # noqa: RUF012


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [  # noqa: RUF012
            "id",
            "email",
            "full_name",
            "phone_number",
            "country",
            "state",
            "city",
            "profile_picture",
            "date_joined",
        ]
        read_only_fields = fields


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [  # noqa: RUF012
            "id",
            "full_name",
            "email",
            "phone_number",
            "profile_picture",
        ]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "full_name",
            "phone_number",
            "country",
            "state",
            "city",
            "profile_picture",
        ]


class SignupSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(required=True)
    phone_number = PhoneNumberField(required=True)

    class Meta:
        model = User
        fields = [  # noqa: RUF012
            "email",
            "full_name",
            "phone_number",
            "password",
            "country",
            "state",
            "city",
            "profile_picture",
        ]
        extra_kwargs = {"password": {"write_only": True, "required": True}}  # noqa: RUF012

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
