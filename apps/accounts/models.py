from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")

        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(
            email=email,
            password=password,
            **extra_fields
        )


class User(AbstractUser):
    username = None  # Remove the username field

    full_name = models.CharField(max_length=255, blank=True, null=True)

    # * contact info
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(unique=True, blank=True, null=True)

    # * address info
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)

    # * other info
    profile_picture = models.URLField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()
