from django.contrib import admin

from .models import ActivityLog, LoginAttempt


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'target')
    search_fields = ('action', 'target')


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'ip', 'username', 'success')
    list_filter = ('success',)
