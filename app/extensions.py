"""Extension instances, importable by blueprints without circular imports.

flask-limiter uses in-memory storage: single process, single box (DECISIONS.md
#7 — revisit before running gunicorn with more than one worker).
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=[],  # opt-in per route; only mutating auth/save routes are limited
)
