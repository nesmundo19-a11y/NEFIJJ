from django.contrib import admin

from .models import Category, EmergencyProtocol, Incident, IncidentEvent


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "organization__name")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "organization",
        "location",
        "status",
        "priority",
        "assigned_to",
        "created_at",
    )
    list_filter = ("organization", "location", "status", "priority", "category")
    search_fields = ("title", "description", "reported_by__username", "organization__name")
    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IncidentEvent)
class IncidentEventAdmin(admin.ModelAdmin):
    list_display = ("incident", "event_type", "actor", "created_at")
    readonly_fields = ("incident", "actor", "event_type", "old_value", "new_value", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EmergencyProtocol)
class EmergencyProtocolAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "contact_phone", "is_active")
    list_filter = ("location__organization", "location", "is_active")

    def has_delete_permission(self, request, obj=None):
        return False
