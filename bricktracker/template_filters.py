"""Custom Jinja2 template filters for BrickTracker."""

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def replace_query_filter(url, key, value):
    """Replace or add a query parameter in a URL, returning a root-relative URL

    The scheme and host are deliberately dropped. Callers pass request.url,
    which is built from the Host header as the application sees it. Behind a
    reverse proxy that is the internal address, so keeping it would send
    pagination links to something like http://172.30.33.2/... instead of the
    address the browser is actually using. A root-relative URL resolves
    against whatever origin the page was loaded from, which is correct both
    behind a proxy and on a plain deployment.

    The path is left untouched, so a prefix already present in request.url
    (Home Assistant ingress sets one) is preserved.
    """
    parsed = urlparse(url)
    query_dict = parse_qs(parsed.query, keep_blank_values=True)
    query_dict[key] = [str(value)]

    new_query = urlencode(query_dict, doseq=True)
    return urlunparse(('', '', parsed.path, parsed.params, new_query, parsed.fragment))