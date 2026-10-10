from django.contrib import admin

from .models import Membership, MembershipInvitation, Organization, Role

admin.site.register(Membership)
admin.site.register(Organization)
admin.site.register(Role)
admin.site.register(MembershipInvitation)
