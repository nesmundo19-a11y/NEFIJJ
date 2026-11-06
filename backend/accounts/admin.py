from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Location,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    User,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "location", "role", "is_active", "created_at")
    list_filter = ("organization", "role", "is_active")
    search_fields = ("user__username", "user__email", "organization__name")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = ("organization", "created_by", "created_at", "expires_at", "used_at", "revoked_at")
    list_filter = ("organization", "created_at", "expires_at", "used_at", "revoked_at")
    readonly_fields = (
        "organization",
        "token_hash",
        "created_by",
        "expires_at",
        "created_at",
        "used_at",
        "used_by",
        "revoked_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "code", "organization__name")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(User)
class NEFIJJUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("NEFIJJ", {"fields": ("role", "location")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("NEFIJJ", {"fields": ("email", "role", "location")}),
    )
    list_display = ("username", "email", "role", "location", "is_active")
    list_filter = ("role", "location", "is_active")
    search_fields = ("username", "email")

    def has_delete_permission(self, request, obj=None):
        return False
