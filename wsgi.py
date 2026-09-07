#!/usr/bin/env python3
"""
WSGI entry point for BrickTracker - Production Docker deployment
This ensures proper gevent monkey patching before any imports
"""

# CRITICAL: Monkey patch must be first, before ANY other imports
import gevent.monkey
gevent.monkey.patch_all()

# Now import the regular app factory
from app import create_app


# Local patch: run correctly behind a reverse proxy that serves the
# application under a path prefix, such as Home Assistant ingress.
#
# The proxy strips the prefix before forwarding, so PATH_INFO is already
# correct and routing works untouched. What breaks is URL *generation*:
# url_for() would emit links relative to the server root, which do not
# exist as far as the proxy is concerned. Moving the prefix into
# SCRIPT_NAME makes Flask prepend it to every generated URL.
#
# Home Assistant announces the prefix in X-Ingress-Path; the generic
# X-Forwarded-Prefix is accepted too so this also covers nginx/Traefik.
# Without either header nothing changes, so plain deployments are
# unaffected.
class PathPrefixMiddleware(object):
    def __init__(self, wsgi_app, /):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response, /):
        prefix = (
            environ.get('HTTP_X_INGRESS_PATH')
            or environ.get('HTTP_X_FORWARDED_PREFIX')
        )

        if prefix:
            environ['SCRIPT_NAME'] = '/' + prefix.strip('/')

        return self.wsgi_app(environ, start_response)


# Create the application - this will be a BrickSocket instance
app_instance = create_app()

# For gunicorn, we need the Flask app, not the BrickSocket wrapper
application = app_instance.app if hasattr(app_instance, 'app') else app_instance

# Wrap outside of the Socket.IO middleware: the prefix has to be resolved
# before anything inspects the request, and PATH_INFO is deliberately left
# alone so the Socket.IO path keeps matching.
application.wsgi_app = PathPrefixMiddleware(application.wsgi_app)