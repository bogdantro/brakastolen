from django.conf import settings


class SecurityHeadersMiddleware:
    """Adds the security headers Django doesn't set by itself:
    Content-Security-Policy (which scripts, styles, fonts and frames are allowed)
    and Permissions-Policy (browser features the site never uses are switched off).
    Both are configured in settings.py (CONTENT_SECURITY_POLICY / PERMISSIONS_POLICY).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        policy = getattr(settings, 'CONTENT_SECURITY_POLICY', {})
        self.csp = '; '.join(
            f"{directive} {' '.join(sources)}".strip()
            for directive, sources in policy.items()
        )
        self.csp_header = (
            'Content-Security-Policy-Report-Only'
            if getattr(settings, 'CSP_REPORT_ONLY', False)
            else 'Content-Security-Policy'
        )
        self.permissions = ', '.join(
            f'{feature}=({" ".join(allow)})'
            for feature, allow in getattr(settings, 'PERMISSIONS_POLICY', {}).items()
        )

    def __call__(self, request):
        response = self.get_response(request)
        if self.csp and getattr(settings, 'CSP_ENABLED', True):
            response.headers.setdefault(self.csp_header, self.csp)
        if self.permissions:
            response.headers.setdefault('Permissions-Policy', self.permissions)
        if not getattr(settings, 'ALLOW_INDEXING', True):
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        return response
