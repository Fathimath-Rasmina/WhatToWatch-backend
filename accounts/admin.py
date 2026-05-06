from django.contrib import admin
from .models import UserPreference


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'updated_at')
    list_filter = ('content_type',)
    search_fields = ('user__username', 'user__email')
