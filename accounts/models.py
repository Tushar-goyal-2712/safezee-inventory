from django.db import models


class PasskeyCredential(models.Model):
    """
    A single registered WebAuthn credential (Face ID, Touch ID,
    Windows Hello, a security key, etc). No User model needed —
    this app protects a single-person tool, not multi-user accounts.
    Any credential in this table is allowed to sign in.
    """

    # Stored as base64url text (not raw bytes) so it's easy to
    # inspect, query, and pass between Python and JavaScript safely.
    credential_id = models.CharField(max_length=255, unique=True)
    public_key = models.TextField()
    sign_count = models.PositiveIntegerField(default=0)

    device_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. 'Tushar's iPhone' — just for your own reference.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.device_label or f"Passkey #{self.pk}"
