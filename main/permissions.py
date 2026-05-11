"""Custom DRF permission classes."""
from __future__ import annotations

import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


API_KEY_HEADER = 'HTTP_X_API_KEY'


class HasDeviceApiKey(BasePermission):
    """Allow access only when the request carries the configured X-API-Key header.

    The comparison uses :func:`hmac.compare_digest` to avoid timing leaks that
    would let an attacker probe the secret one byte at a time.
    """

    message = 'Invalid or missing X-API-Key header.'

    def has_permission(self, request, view) -> bool:
        expected = getattr(settings, 'DEVICE_API_KEY', '') or ''
        provided = request.META.get(API_KEY_HEADER, '') or ''

        if not expected:
            # Deny by default if the server has not configured a key — better
            # than silently letting all requests through.
            return False

        return hmac.compare_digest(expected, provided)
