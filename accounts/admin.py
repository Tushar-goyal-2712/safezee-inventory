from django.contrib import admin
from .models import PasskeyCredential


@admin.register(PasskeyCredential)
class PasskeyCredentialAdmin(admin.ModelAdmin):
    list_display = ("id", "device_label", "created_at", "last_used_at", "sign_count")
    readonly_fields = ("credential_id", "public_key", "sign_count", "created_at", "last_used_at")
