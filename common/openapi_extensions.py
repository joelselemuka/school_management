"""
Extensions OpenAPI pour la documentation Spectacular.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    """
    Extension pour la documentation de l'authentification par cookies JWT.
    """
    target_class = 'common.authentication.CookieJWTAuthentication'
    name = 'cookieAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'cookie',
            'name': 'access_token',
            'description': 'JWT token stored in HTTP-only cookie'
        }