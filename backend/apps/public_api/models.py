"""Public API models — API key management.

The raw API key is NEVER stored: only its SHA-256 hash lives in the database
(`key`). The plaintext is shown exactly once, right after creation. On every
request the incoming key is hashed and looked up by hash, so a database dump
leaks no usable credentials.
"""
import hashlib
import secrets

from django.db import models
from django.contrib.auth.models import User


class ApiKey(models.Model):
    """API key for external/public API access (stored hashed)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    # SHA-256 hex digest of the raw key (64 chars). NOT the key itself.
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

    @staticmethod
    def generate_raw_key() -> str:
        """A fresh, URL-safe random secret (the value the client keeps)."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """Deterministic SHA-256 hex digest used for storage and lookup."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def create_for_user(cls, user, name: str) -> "ApiKey":
        """Create a key, persisting only its hash.

        The plaintext is attached to the returned instance as `plain_key` so the
        caller can show it once; it is never written to the database.
        """
        raw = cls.generate_raw_key()
        instance = cls.objects.create(user=user, name=name, key=cls.hash_key(raw))
        instance.plain_key = raw
        return instance

    @property
    def masked_key(self) -> str:
        """Opaque, non-reversible hint for list views (no plaintext available)."""
        return "••••" + self.key[-4:]
