"""Public API models — API key management."""
import secrets
from django.db import models
from django.contrib.auth.models import User


class ApiKey(models.Model):
    """API key for external/public API access."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100, help_text="Human-readable name for this key")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @classmethod
    def generate_key(cls) -> str:
        return secrets.token_urlsafe(32)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        super().save(*args, **kwargs)

    @property
    def masked_key(self) -> str:
        """Show only first 8 and last 4 chars."""
        if len(self.key) <= 12:
            return self.key[:4] + "****"
        return self.key[:8] + "..." + self.key[-4:]
