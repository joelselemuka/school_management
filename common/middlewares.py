

from django.conf import settings
from django.db import connection
import logging
import time
from core.models import AnneeAcademique


class AcademicYearCookieMiddleware:

    def __init__(self, get_response):

        self.get_response = get_response


    def __call__(self, request):

        year_id = request.COOKIES.get("academic_year_id")

        year = None


        if year_id:

            year = AnneeAcademique.objects.filter(
                id=year_id,
                actif=True
            ).first()


        if not year:

            year = AnneeAcademique.objects.filter(
                actif=True
            ).order_by("-date_debut").first()


        request.academic_year = year


        response = self.get_response(request)


        if year and not year_id:

            response.set_cookie(

                "academic_year_id",

                year.id,

                httponly=True,

                samesite="Lax"

            )


        return response


class SecurityHeadersMiddleware:
    """
    Add security headers that are missing on the response.
    Configurable via settings:
      - CONTENT_SECURITY_POLICY
      - SECURE_REFERRER_POLICY
      - PERMISSIONS_POLICY
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        csp = getattr(settings, "CONTENT_SECURITY_POLICY", None)
        if csp and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = csp

        referrer = getattr(settings, "SECURE_REFERRER_POLICY", None)
        if referrer and "Referrer-Policy" not in response:
            response["Referrer-Policy"] = referrer

        permissions = getattr(settings, "PERMISSIONS_POLICY", None)
        if permissions and "Permissions-Policy" not in response:
            response["Permissions-Policy"] = permissions

        return response


class _QueryProfiler:
    def __init__(self):
        self.count = 0
        self.time = 0.0

    def __call__(self, execute, sql, params, many, context):
        start = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.count += 1
            self.time += time.perf_counter() - start


class RequestProfilingMiddleware:
    """
    Simple request profiler (time + DB queries).
    Enabled via settings.REQUEST_PROFILING_ENABLED = True
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("performance")

    def __call__(self, request):
        if not getattr(settings, "REQUEST_PROFILING_ENABLED", False):
            return self.get_response(request)

        start = time.perf_counter()
        profiler = _QueryProfiler()

        if hasattr(connection, "execute_wrapper"):
            with connection.execute_wrapper(profiler):
                response = self.get_response(request)
        else:
            response = self.get_response(request)

        total_ms = (time.perf_counter() - start) * 1000.0
        db_ms = profiler.time * 1000.0
        db_q = profiler.count

        threshold_ms = getattr(settings, "REQUEST_PROFILING_THRESHOLD_MS", 0)
        if threshold_ms and total_ms < threshold_ms:
            return response

        status = getattr(response, "status_code", "unknown")
        self.logger.info(
            "perf method=%s path=%s status=%s total_ms=%.2f db_ms=%.2f db_q=%s",
            request.method,
            request.path,
            status,
            total_ms,
            db_ms,
            db_q,
        )

        return response
