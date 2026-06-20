"""Optional error reporting — stdlib urllib only, no SDK (DECISIONS.md #36).

When ERROR_WEBHOOK_URL is set, every unhandled exception is POSTed as a small
JSON object to that URL (a Sentry ingest endpoint, a Slack/Discord incoming
webhook, or any JSON sink). Unset = no-op, so dev and self-hosters pay nothing
and add no dependency. Reporting NEVER raises: a monitoring outage must not
turn one 500 into two.

Privacy: we send the method, the (reset-token-scrubbed) path, and the exception
traceback only — never the request body, headers, cookies, or user identity.
"""

import json
import os
import traceback
import urllib.error
import urllib.request

from flask import got_request_exception, request

from .security import scrub_sensitive_path


def _report(sender, exception, **_extra) -> None:
    url = os.environ.get("ERROR_WEBHOOK_URL", "")
    if not url:
        return
    try:
        payload = json.dumps(
            {
                "service": "cutecumber",
                "method": request.method,
                "path": scrub_sensitive_path(request.path),
                "exception": f"{type(exception).__name__}: {exception}",
                # Tail only: stdlib tracebacks carry no local variables, and we
                # cap length so a deep stack can't bloat the webhook payload.
                "traceback": "".join(
                    traceback.format_exception(exception)
                )[-4000:],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "cutecumber/1.0 (+https://cutecumber.cc)",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5).close()
    except (urllib.error.URLError, TimeoutError, ValueError):
        # Last resort: the local log still has the original error via Flask.
        sender.logger.warning("error webhook delivery failed", exc_info=True)


def init_app(app) -> None:
    """Connect the reporter to Flask's unhandled-exception signal.

    No-op at runtime until ERROR_WEBHOOK_URL is set, so this is always safe to
    register; the env var alone arms it.
    """
    got_request_exception.connect(_report, app)
