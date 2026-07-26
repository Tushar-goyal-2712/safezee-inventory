import base64


def bytes_to_b64url(data: bytes) -> str:
    """Encode raw bytes as an unpadded base64url string (WebAuthn's wire format)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_to_bytes(data: str) -> bytes:
    """Decode an unpadded base64url string back to raw bytes."""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
