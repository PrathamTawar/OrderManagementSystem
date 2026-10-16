from django.db import models
from django.db.models.functions import Lower
from phonenumber_field.modelfields import PhoneNumberField


class CustomerType(models.Model):
    # * basic info
    name = models.CharField(max_length=100)

    # * relationships
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="org_customer_types",
    )
    created_by = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="customer_types_created_by",
    )
    last_updated_by = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="customer_types_updated_by",
    )

    # * flags
    is_active = models.BooleanField(default=True)

    # * timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                Lower("name"),
                "organization",
                name="uniq_cus_type_per_org",
            ),
        ]


class Customer(models.Model):
    # * basic info
    name = models.CharField(max_length=255)

    # * contact info
    email = models.EmailField(blank=True, null=True)
    phone_number = PhoneNumberField(blank=True, null=True)
    alt_phone_number = PhoneNumberField(blank=True, null=True)

    # * relationships
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="org_customers",
    )
    created_by = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.SET_NULL,
        related_name="customers_created_by",
        null=True,
        blank=True,
    )
    last_updated_by = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers_last_updated_by",
    )
    customer_type = models.ForeignKey(
        CustomerType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers_customer_type",
    )

    #  * address info
    address_line1 = models.TextField(blank=True, null=True)
    address_line2 = models.TextField(null=True, blank=True)
    city = models.CharField(blank=True, null=True, max_length=100)
    state = models.CharField(blank=True, null=True, max_length=100)
    country = models.CharField(blank=True, null=True, max_length=100)
    zip_code = models.CharField(blank=True, null=True, max_length=20)

    # * timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                "phone_number",
                "organization",
                name="uniq_cus_phone_per_org",
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.email}"
