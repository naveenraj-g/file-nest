"""
filenest.namespaces.webhooks — WebhooksNamespace with signature verification.

Usage:
    from filenest import verify_webhook_signature
    is_valid = verify_webhook_signature(body, signature, secret)
"""

from __future__ import annotations

import hashlib
import hmac


def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Verify an incoming webhook payload using HMAC-SHA256.

    Args:
        body: Raw request body bytes (before JSON parsing).
        signature: Value of the x-filenest-signature header.
        secret: Webhook signing secret from the console.

    Returns:
        True if the signature is valid; False otherwise.
    """
    sig = signature.removeprefix("sha256=")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
