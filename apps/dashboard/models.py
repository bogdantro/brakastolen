"""Dashboard bookkeeping: who did what (ActivityLog) and login attempts for rate limiting."""
from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField('Handling', max_length=200)
    target = models.CharField('Gjelder', max_length=200, blank=True)
    url = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Aktivitet'
        verbose_name_plural = 'Aktivitetslogg'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} – {self.action} {self.target}'


class LoginAttempt(models.Model):
    ip = models.GenericIPAddressField(null=True, blank=True)
    username = models.CharField(max_length=150, blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Innloggingsforsøk'
        verbose_name_plural = 'Innloggingsforsøk'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.ip} ({"ok" if self.success else "feilet"})'
