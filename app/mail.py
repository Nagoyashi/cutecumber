"""Email sending via Resend's HTTP API — stdlib urllib only, no SDK
(DECISIONS.md #26: a JSON POST doesn't justify a dependency).

Dev mode: with RESEND_API_KEY unset, the email body is logged to the console
instead of sent, so the whole reset flow works locally without an account.

Resend free-tier reality check: until the cutecumber.cc domain is verified in
the Resend dashboard, the onboarding@resend.dev sender can only deliver to
the account owner's own email address. Verify the domain and set MAIL_FROM
before real users need this.
"""

import json
import os
import urllib.error
import urllib.request

from flask import current_app

_RESEND_ENDPOINT = "https://api.resend.com/emails"


def send_email(to: str, subject: str, text: str) -> bool:
    """Send a plain-text email. Returns False on failure (and logs loudly);
    callers decide whether the user should know."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    sender = os.environ.get("MAIL_FROM", "cutecumber <onboarding@resend.dev>")

    if not api_key:
        current_app.logger.warning(
            "RESEND_API_KEY not set — email NOT sent.\nTo: %s\nSubject: %s\n%s",
            to, subject, text,
        )
        return True

    payload = json.dumps(
        {"from": sender, "to": [to], "subject": subject, "text": text}
    ).encode("utf-8")
    request = urllib.request.Request(
        _RESEND_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError) as exc:
        current_app.logger.error("email send failed for %s: %s", to, exc)
        return False
