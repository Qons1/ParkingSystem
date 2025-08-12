from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "email", "is_mall_owner", "is_admin", "is_user")
    fieldsets = UserAdmin.fieldsets + (
        ("Role Permissions", {"fields": ("is_mall_owner", "is_admin", "is_user")}),
    )
    # hide is_staff in forms by not including it in add_fieldsets/fieldsets overrides
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role Permissions", {"classes": ("wide",), "fields": ("is_mall_owner", "is_admin", "is_user")}),
    )

admin.site.register(CustomUser, CustomUserAdmin)