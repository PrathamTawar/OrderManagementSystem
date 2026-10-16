from django.contrib.auth.models import Permission
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from phonenumber_field.modelfields import PhoneNumberField


class Organization(models.Model):
    # * basic info
    name = models.CharField(max_length=255)
    phone_number = PhoneNumberField(unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)

    # * address info
    address_line1 = models.TextField()
    address_line2 = models.TextField(null=True, blank=True)
    city = models.CharField(blank=True, null=True, max_length=100)
    state = models.CharField(blank=True, null=True, max_length=100)
    country = models.CharField(blank=True, null=True, max_length=100)
    zip_code = models.CharField(blank=True, null=True, max_length=20)

    # * other info
    profile_picture = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="roles"
    )
    permissions = models.ManyToManyField(
        Permission, blank=True, related_name="organization_roles"
    )
    created_by = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    last_updated_by = models.ForeignKey(
        "organizations.Membership",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                Lower("name"),
                "organization",
                name="uniq_name_org_roles",
            ),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class Membership(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="organization_relationships",
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="user_relationships"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_relationships",
    )
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    last_updated_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(app_label)s_%(class)s_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_owner = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "organization")
        permissions = [  # noqa: RUF012
            ("view_own_membership", "Can view own membership")
        ]

    def __str__(self):
        return f"{self.user.email} - {self.organization.name}"


class MembershipInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    email = models.EmailField()
    full_name = models.CharField(max_length=150)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
    )
    role = models.ForeignKey(
        "organizations.Role",
        on_delete=models.PROTECT,
    )
    invited_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(app_label)s_%(class)s_invited",
    )

    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                Lower("email"),
                "organization",
                condition=Q(status="pending"),
                name="uniq_pend_inv_org_email",
            ),
        ]

    def __str__(self):
        return f"{self.email} - {self.organization.name}"
