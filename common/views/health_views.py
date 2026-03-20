from django.http import JsonResponse
from django.db import connections
from django.utils import timezone
from django.core.cache import cache


def _check_db():
    try:
        connection = connections["default"]
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, None
    except Exception as exc:
        return False, str(exc)


def _check_cache():
    try:
        key = "health_check_ping"
        cache.set(key, "pong", timeout=5)
        value = cache.get(key)
        return value == "pong", None if value == "pong" else "cache_miss"
    except Exception as exc:
        return False, str(exc)


def health(request):
    return JsonResponse(
        {"status": "ok", "time": timezone.now().isoformat()},
        status=200,
    )


def readiness(request):
    db_ok, db_err = _check_db()
    cache_ok, cache_err = _check_cache()
    ok = db_ok and cache_ok
    return JsonResponse(
        {
            "status": "ok" if ok else "degraded",
            "db": {"ok": db_ok, "error": db_err},
            "cache": {"ok": cache_ok, "error": cache_err},
            "time": timezone.now().isoformat(),
        },
        status=200 if ok else 503,
    )


def liveness(request):
    return JsonResponse(
        {"status": "alive", "time": timezone.now().isoformat()},
        status=200,
    )


def detailed(request):
    db_ok, db_err = _check_db()
    cache_ok, cache_err = _check_cache()
    return JsonResponse(
        {
            "status": "ok" if (db_ok and cache_ok) else "degraded",
            "checks": {
                "db": {"ok": db_ok, "error": db_err},
                "cache": {"ok": cache_ok, "error": cache_err},
            },
            "time": timezone.now().isoformat(),
        },
        status=200 if (db_ok and cache_ok) else 503,
    )
