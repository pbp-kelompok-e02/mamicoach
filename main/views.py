from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.core.files.storage import default_storage

from urllib.parse import urlparse
from urllib.request import Request, urlopen
import socket
import ipaddress
import mimetypes
from pathlib import PurePosixPath
from reviews.models import Review
from courses_and_coach.models import Course, Category
from user_profile.models import CoachProfile


_PROXY_TIMEOUT_SECONDS = 8
_PROXY_MAX_BYTES = 5 * 1024 * 1024  # 5MB


def _normalized_media_url() -> str:
    media_url = (getattr(settings, "MEDIA_URL", None) or "/media/")
    if not media_url.startswith("/"):
        media_url = f"/{media_url}"
    if not media_url.endswith("/"):
        media_url = f"{media_url}/"
    return media_url


def _try_serve_local_media_image(request, parsed):
    """Serve /media/... files directly from storage when target host is local.

    Returns an HttpResponse/JsonResponse if handled, otherwise None.
    """
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return None

    request_host = request.get_host().split(":")[0].lower() if request.get_host() else ""
    local_hosts = {"localhost", "127.0.0.1", "0.0.0.0"}
    is_our_host = bool(request_host) and hostname == request_host

    media_url = _normalized_media_url()
    media_prefixes = {media_url, "/media/"}
    matched_prefix = next((p for p in media_prefixes if parsed.path.startswith(p)), None)
    if not matched_prefix:
        return None

    # Only serve from storage when it is our own host or a loopback host.
    if not (is_our_host or hostname in local_hosts):
        return None

    rel_path = parsed.path[len(matched_prefix) :].lstrip("/")
    if not rel_path:
        return JsonResponse({"error": "Invalid media path"}, status=400)

    # Guard against path traversal attempts.
    parts = PurePosixPath(rel_path).parts
    if any(part in ("..", "") for part in parts):
        return JsonResponse({"error": "Invalid media path"}, status=400)

    guessed_type, _ = mimetypes.guess_type(rel_path)
    content_type = guessed_type or "application/octet-stream"
    if not content_type.lower().startswith("image/"):
        return JsonResponse({"error": "URL did not return an image"}, status=415)

    # Best-effort size check if supported by the storage.
    try:
        size = default_storage.size(rel_path)
        if size and size > _PROXY_MAX_BYTES:
            return JsonResponse({"error": "Image exceeds size limit"}, status=413)
    except Exception:
        pass

    try:
        with default_storage.open(rel_path, "rb") as fh:
            data = fh.read(_PROXY_MAX_BYTES + 1)
            if len(data) > _PROXY_MAX_BYTES:
                return JsonResponse({"error": "Image exceeds size limit"}, status=413)

        out = HttpResponse(data, content_type=content_type)
        out["Cache-Control"] = "public, max-age=3600"
        return out
    except Exception as e:
        return JsonResponse({"error": f"Proxy failed: {str(e)}"}, status=502)


# Create your views here.
def show_main(request):
    # Fetch top 10 reviews by highest rating
    top_reviews = Review.objects.select_related(
        "user", "course", "coach", "coach__user"
    ).order_by("-rating", "-created_at")[:10]

    featured_courses = (
        Course.objects.all()
        .select_related("coach", "category")
        .order_by("-coach__rating")[:4]
    )

    # Get all categories
    categories = Category.objects.all().order_by("name")

    # Get top 6 coaches by rating
    top_coaches = CoachProfile.objects.filter(verified=True).order_by("-rating")[:6]

    context = {
        "featured_courses": featured_courses,
        "categories": categories,
        "top_coaches": top_coaches,
        "top_reviews": top_reviews,
    }
    return render(request, "pages/landing_page/index.html", context)


# Error handlers
def handler_404(request, exception=None):
    """Handle 404 Not Found errors"""
    return render(request, "404.html", status=404)


def handler_500(request):
    """Handle 500 Internal Server errors"""
    return render(request, "500.html", status=500)


def _is_public_ip(hostname: str) -> bool:
    """Return True only if hostname resolves exclusively to public IPs."""
    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    ips = []
    for family, _, _, _, sockaddr in addrinfo:
        ip_str = sockaddr[0]
        try:
            ips.append(ipaddress.ip_address(ip_str))
        except ValueError:
            continue

    if not ips:
        return False

    for ip in ips:
        # Block any internal / non-public ranges
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False

    return True


def proxy_image(request):
    """Public image proxy.

    Usage: /proxy/image/?url=https://example.com/image.png

    NOTE: This endpoint is intentionally unauthenticated.
    - In production (DEBUG=False), it blocks localhost/private IPs to reduce SSRF risk.
    - In development (DEBUG=True), proxying to local/private addresses is allowed.
    """
    debug = bool(getattr(settings, "DEBUG", False))

    raw_url = request.GET.get("url")
    if not raw_url:
        return JsonResponse({"error": "Missing url parameter"}, status=400)

    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        return JsonResponse({"error": "Only http/https URLs are allowed"}, status=400)

    if not parsed.netloc:
        return JsonResponse({"error": "Invalid URL"}, status=400)

    hostname = parsed.hostname
    if not hostname:
        return JsonResponse({"error": "Invalid URL hostname"}, status=400)

    local_media_response = _try_serve_local_media_image(request, parsed)
    if local_media_response is not None:
        return local_media_response

    # SSRF protections (production only)
    if not debug:
        if hostname.lower() in ("localhost",):
            return JsonResponse({"error": "Blocked host"}, status=403)
        if not _is_public_ip(hostname):
            return JsonResponse({"error": "Blocked host"}, status=403)

    try:
        req = Request(
            raw_url,
            headers={
                "User-Agent": "mamicoach-image-proxy/1.0",
                "Accept": "image/*",
            },
        )

        with urlopen(req, timeout=_PROXY_TIMEOUT_SECONDS) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if not content_type.lower().startswith("image/"):
                return JsonResponse({"error": "URL did not return an image"}, status=415)

            # Enforce size limit. Some servers provide Content-Length, but we still cap reads.
            content_length = resp.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > _PROXY_MAX_BYTES:
                        return JsonResponse({"error": "Image exceeds size limit"}, status=413)
                except ValueError:
                    pass

            data = resp.read(_PROXY_MAX_BYTES + 1)
            if len(data) > _PROXY_MAX_BYTES:
                return JsonResponse({"error": "Image exceeds size limit"}, status=413)

            out = HttpResponse(data, content_type=content_type)
            out["Cache-Control"] = "public, max-age=3600"
            return out

    except Exception as e:
        return JsonResponse({"error": f"Proxy failed: {str(e)}"}, status=502)
