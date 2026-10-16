from django.contrib import admin

from .models import Customer, CustomerType

admin.site.register(Customer)
admin.site.register(CustomerType)
