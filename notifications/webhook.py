"""
Webhook receiver that forwards Grafana (or any compatible) alert payloads as
iOS push notifications via APNs.

Endpoints
---------
GET  /health   – liveness check; returns 200 {"status": "ok"}
POST /webhook  – receives a JSON alert payload and sends iOS push
                 notifications to all configured device tokens.

Expected JSON body (Grafana-style)
-----------------------------------
{
  "title":   "Panel title",
  "message": "Alert description",
  "state":   "alerting" | "ok" | "no_data",
  ...        any additional fields are forwarded to the app as custom data
}

Required environment variables
--------------------------------
APNS_KEY_ID        – Apple Developer Key ID
APNS_TEAM_ID       – Apple Developer Team ID
APNS_BUNDLE_ID     – App bundle ID (e.g. com.example.myapp)
APNS_PRIVATE_KEY   – Full .p8 private key content (including header/footer)
APNS_DEVICE_TOKENS – Comma-separated list of target device tokens

Optional environment variables
--------------------------------
APNS_SANDBOX       – "true" (default) → sandbox; "false" → production
WEBHOOK_PORT       – Port to listen on (default: 8080)
"""

import logging
import os

from flask import Flask, jsonify, request

from apns_client import APNsClient, APNsError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = Flask(__name__)
apns = APNsClient()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> tuple:
    """Liveness probe."""
    return jsonify({"status": "ok"}), 200


@app.post("/webhook")
def webhook() -> tuple:
    """Receive an alert payload and dispatch iOS push notifications."""
    data = request.get_json(silent=True)
    if not data:
        logger.warning("Received webhook with invalid or missing JSON body")
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    # -----------------------------------------------------------------------
    # Build notification text from the incoming payload
    # -----------------------------------------------------------------------
    state: str = data.get("state", "")
    title: str = data.get("title", "Alert")
    message: str = data.get("message", "")

    if state:
        title = f"[{state.upper()}] {title}"

    # Pass the raw Grafana payload to the app so it can act on it
    extra: dict = {"grafana": data}

    # -----------------------------------------------------------------------
    # Resolve target device tokens
    # -----------------------------------------------------------------------
    raw_tokens = os.environ.get("APNS_DEVICE_TOKENS", "")
    device_tokens = [t.strip() for t in raw_tokens.split(",") if t.strip()]

    if not device_tokens:
        logger.error("APNS_DEVICE_TOKENS is not set or empty")
        return jsonify({"error": "No device tokens configured"}), 500

    # -----------------------------------------------------------------------
    # Send notifications
    # -----------------------------------------------------------------------
    results = []
    for token in device_tokens:
        masked = token[:8] + "…"
        try:
            apns.send_notification(token, title, message, extra=extra)
            logger.info("Notification sent to device %s", masked)
            results.append({"token": masked, "status": "sent"})
        except APNsError as exc:
            logger.error("Failed to notify device %s: %s", masked, exc)
            results.append({"token": masked, "status": "failed", "error": "APNs delivery failed"})

    sent_count = sum(1 for r in results if r["status"] == "sent")
    if sent_count == len(results):
        http_status = 200
    elif sent_count > 0:
        http_status = 207  # Multi-Status: partial success
    else:
        http_status = 500  # All notifications failed
    return jsonify({"results": results}), http_status


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("WEBHOOK_PORT", 8080))
    app.run(host="0.0.0.0", port=port)
