import os
import base64
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging


_default_app = None


def _get_app():
    global _default_app
    if _default_app is not None:
        return _default_app

    service_account_json_b64 = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_JSON_B64"
    ) or os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON_B64")

    if not service_account_json_b64:
        raise RuntimeError(
            "Firebase credentials not configured. Set "
            "FIREBASE_SERVICE_ACCOUNT_JSON_B64 (or GOOGLE_APPLICATION_CREDENTIALS_JSON_B64) "
            "to base64(JSON)."
        )

    try:
        decoded = base64.b64decode(service_account_json_b64).decode("utf-8")
    except Exception as e:
        raise RuntimeError(
            "Firebase service account base64 env var could not be decoded. "
            "Set FIREBASE_SERVICE_ACCOUNT_JSON_B64 (or GOOGLE_APPLICATION_CREDENTIALS_JSON_B64) "
            "to base64(JSON)."
        ) from e

    import json

    info = json.loads(decoded)

    cred = credentials.Certificate(info)
    _default_app = firebase_admin.initialize_app(cred)
    return _default_app


def send_push_to_tokens(
    tokens: list[str],
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Send a push notification to a list of FCM registration tokens."""
    if not tokens:
        return {"success": 0, "failure": 0, "responses": []}

    _get_app()

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )

    # firebase-admin API differs across versions.
    # - Newer versions provide send_each_for_multicast
    # - Some versions provide send_multicast
    # - Fallback: send one-by-one
    if hasattr(messaging, "send_each_for_multicast"):
        batch_response = messaging.send_each_for_multicast(message)
        responses = batch_response.responses
        success_count = batch_response.success_count
        failure_count = batch_response.failure_count
    elif hasattr(messaging, "send_multicast"):
        batch_response = messaging.send_multicast(message)
        responses = batch_response.responses
        success_count = batch_response.success_count
        failure_count = batch_response.failure_count
    else:
        responses = []
        success_count = 0
        failure_count = 0
        for token in tokens:
            try:
                msg = messaging.Message(
                    token=token,
                    notification=messaging.Notification(title=title, body=body),
                    data=data or {},
                )
                message_id = messaging.send(msg)
                responses.append(
                    {
                        "success": True,
                        "message_id": message_id,
                        "exception": None,
                    }
                )
                success_count += 1
            except Exception as e:  # pragma: no cover
                responses.append(
                    {
                        "success": False,
                        "message_id": None,
                        "exception": str(e),
                    }
                )
                failure_count += 1

    return {
        "success": success_count,
        "failure": failure_count,
        "responses": [
            (
                {
                    "success": r.success,
                    "message_id": r.message_id,
                    "exception": str(r.exception) if r.exception else None,
                }
                if hasattr(r, "success")
                else r
            )
            for r in responses
        ],
    }
