"""Gunicorn configuration (loaded via `-c gunicorn.conf.py` in entrypoint.sh).

Sole job: install an access logger that redacts the single-use password-reset
token from the logged request path (issue #11). Workers, bind, and
--access-logfile stay on the command line in entrypoint.sh; this file only adds
what the CLI can't express. See DEPLOY.md.
"""

from gunicorn.glogging import Logger

from app.security import scrub_sensitive_path


class ScrubbingLogger(Logger):
    """Access logger that strips the reset token from the request path/line."""

    def atoms(self, resp, req, environ, request_time):
        environ = dict(environ)
        for key in ("RAW_URI", "PATH_INFO"):
            if key in environ:
                environ[key] = scrub_sensitive_path(environ[key])
        return super().atoms(resp, req, environ, request_time)


logger_class = ScrubbingLogger
