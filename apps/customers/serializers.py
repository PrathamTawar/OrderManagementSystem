from rest_framework import serializers

from apps.organizations.serializers import MembershipActorSerializer

from .models import Customer, CustomerType


# * customer type serializer R
class CustomerTypeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerType
        fields = ["id", "name", "is_active"]  # noqa: RUF012


class CustomerTypeDetailSerializer(serializers.ModelSerializer):
    created_by = MembershipActorSerializer(read_only=True)
    last_updated_by = MembershipActorSerializer(read_only=True)

    class Meta:
        model = CustomerType
        fields = '__all__'


# * customer type serializer W
class CustomerTypeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerType
        fields = ["name", "is_active"]  # noqa: RUF012

    def update(self, instance, validated_data):
        membership = self.context["membership"]
        validated_data["last_updated_by"] = membership
        return super().update(instance, validated_data)

    def create(self, validated_data):
        membership = self.context["membership"]
        validated_data["organization"] = membership.organization
        validated_data["created_by"] = membership
        return super().create(validated_data)


# * customer serializer R
class CustomerListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.user.full_name")
    customer_type_name = serializers.CharField(source="customer_type.name")

    class Meta:
        model = Customer
        fields = [  # noqa: RUF012
            "id",
            "name",
            "email",
            "phone_number",
            "city",
            "state",
            "country",
            "created_by_name",
            "customer_type_name",
            "created_at",
            "updated_at",
        ]


class CustomerDetailSerializer(serializers.ModelSerializer):
    created_by = MembershipActorSerializer(read_only=True)
    customer_type_name = serializers.CharField(source="customer_type.name")
    last_updated_by = MembershipActorSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = [  # noqa: RUF012
            "id",
            "name",
            "email",
            "phone_number",
            "alt_phone_number",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "country",
            "zip_code",
            "created_by",
            "last_updated_by",
            "customer_type_name",
        ]


# * customer serializer W
class CustomerCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [  # noqa: RUF012
            "name",
            "email",
            "phone_number",
            "alt_phone_number",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "country",
            "zip_code",
            "customer_type",
        ]

        def get_fields(self):
            fields = super().get_fields()
            membership = self.context["membership"]
            fields["customer_type"].queryset = CustomerType.objects.filter(
                organization=membership.organization, is_active=True
            )
            return fields

    def update(self, instance, validated_data):
        membership = self.context["membership"]
        validated_data["updated_by"] = membership
        return super().update(instance, validated_data)

    def create(self, validated_data):
        membership = self.context["membership"]
        validated_data["organization"] = membership.organization
        validated_data["created_by"] = membership
        return super().create(validated_data)
