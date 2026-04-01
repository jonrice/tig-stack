"""
APNs (Apple Push Notification service) client.

Uses token-based (JWT) authentication over HTTP/2 to send push notifications
to iOS devices.  Credentials are read from environment variables so that
nothing sensitive is baked into the image.

Required environment variables
--------------------------------
APNS_KEY_ID        – 10-character Key ID from the Apple Developer portal
APNS_TEAM_ID       – 10-character Apple Developer Team ID
APNS_BUNDLE_ID     – App bundle identifier (e.g. com.example.myapp)
APNS_PRIVATE_KEY   – Full contents of the .p8 private key file, including
                     the -----BEGIN/END PRIVATE KEY----- lines.

Optional environment variables
--------------------------------
APNS_SANDBOX       – Set to "false" to target the production APNs endpoint.
                     Defaults to "true" (sandbox).
"""

import os
import time

import httpx
import jwt


APNS_SANDBOX_HOST = "api.sandbox.push.apple.com"
APNS_PRODUCTION_HOST = "api.push.apple.com"

# APNs auth tokens are valid for at most 60 minutes; rotate every 50 minutes.
_TOKEN_TTL = 50 * 60  # seconds


class APNsError(Exception):
    """Raised when APNs returns a non-200 response."""


class APNsClient:
    """Thin wrapper around the APNs HTTP/2 API."""

    def __init__(self) -> None:
        self.key_id = os.environ["APNS_KEY_ID"]
        self.team_id = os.environ["APNS_TEAM_ID"]
        self.bundle_id = os.environ["APNS_BUNDLE_ID"]
        self.private_key = os.environ["APNS_PRIVATE_KEY"]
        self.sandbox = os.environ.get("APNS_SANDBOX", "true").lower() == "true"

        self._cached_token: str | None = None
        self._token_issued_at: float = 0.0
        # Reuse a single HTTP/2 client to benefit from connection pooling.
        self._http_client = httpx.Client(http2=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _host(self) -> str:
        return APNS_SANDBOX_HOST if self.sandbox else APNS_PRODUCTION_HOST

    def _get_auth_token(self) -> str:
        """Return a cached JWT bearer token, refreshing it when near expiry."""
        now = time.time()
        if self._cached_token and (now - self._token_issued_at) < _TOKEN_TTL:
            return self._cached_token

        issued_at = int(now)
        self._cached_token = jwt.encode(
            {"iss": self.team_id, "iat": issued_at},
            self.private_key,
            algorithm="ES256",
            headers={"alg": "ES256", "kid": self.key_id},
        )
        self._token_issued_at = now
        return self._cached_token

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_notification(
        self,
        device_token: str,
        title: str,
        body: str,
        extra: dict | None = None,
    ) -> httpx.Response:
        """Send an alert push notification to a single device.

        Parameters
        ----------
        device_token:
            Hex-encoded APNs device token for the target device.
        title:
            Notification title shown in the banner.
        body:
            Notification body text.
        extra:
            Optional dictionary that is merged into the top-level APNs
            payload (outside the ``aps`` key).  Useful for passing custom
            data to the app.

        Returns
        -------
        httpx.Response
            The raw HTTP response from APNs.

        Raises
        ------
        APNsError
            If APNs returns a non-200 status code.
        """
        url = f"https://{self._host}/3/device/{device_token}"

        payload: dict = {
            "aps": {
                "alert": {"title": title, "body": body},
                "sound": "default",
            }
        }
        if extra:
            payload.update(extra)

        headers = {
            "authorization": f"bearer {self._get_auth_token()}",
            "apns-topic": self.bundle_id,
            "apns-push-type": "alert",
        }

        response = self._http_client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            raise APNsError(
                f"APNs rejected notification for device {device_token[:8]}…: "
                f"HTTP {response.status_code} – {response.text}"
            )

        return response
