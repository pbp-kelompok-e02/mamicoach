import json
import re
import time
import urllib.parse
from decimal import Decimal
from typing import Any, Dict, List, Tuple

import requests
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from main.models import Coach, Course

# ---- Config ----
DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari",
    "Referer": "https://www.superprof.co.id/",
}
REQUEST_TIMEOUT = 20  # seconds
PRICE_MIN_RP = 10_000  # if parsed price < 10k, assume it's in thousands (120 -> 120_000)

# in-run cache: name(lower) -> user id
_USER_BY_NAME_CACHE: dict[str, int] = {}


# ---- Name / User helpers (reuse User by same name) ----
def split_name(full_name: str) -> tuple[str, str]:
    full_name = (full_name or "").strip()
    if not full_name:
        return ("Coach", "")
    parts = full_name.split()
    return (parts[0], " ".join(parts[1:]) if len(parts) > 1 else "")

def unique_username_from_name(name: str) -> str:
    base = slugify(name or "coach") or "coach"
    uname = base
    i = 2
    while User.objects.filter(username=uname).exists():
        uname = f"{base}-{i}"
        i += 1
    return uname

def get_or_create_user_by_name(teacher_name: str) -> User:
    key = (teacher_name or "").strip().lower()
    if key in _USER_BY_NAME_CACHE:
        return User.objects.get(id=_USER_BY_NAME_CACHE[key])
    first, last = split_name(teacher_name)
    user = (
        User.objects
        .filter(first_name__iexact=first, last_name__iexact=last)
        .order_by("id")
        .first()
    )
    if user is None:
        username = unique_username_from_name(teacher_name)
        user = User.objects.create(
            username=username,
            first_name=first[:30],
            last_name=last[:150],
            email=f"{slugify(teacher_name) or 'coach'}@example.com",
        )
    _USER_BY_NAME_CACHE[key] = user.id
    return user


# ---- Normalizers ----
def _digits(s: str) -> str:
    return re.sub(r"[^\d]", "", s or "")

def parse_price(item: Dict[str, Any]) -> int:
    raw = (item.get("price") or "").strip()
    if not _digits(raw):
        raw = item.get("price_html") or ""
    n = _digits(raw)
    if not n:
        return 0
    val = int(n)
    if val < PRICE_MIN_RP:
        val *= 1000
    return val

def best_thumbnail(item: Dict[str, Any]) -> str:
    if item.get("teacherPhoto"):
        return item["teacherPhoto"]
    default = (item.get("teacherPhotos") or {}).get("default") or {}
    return default.get("photo") or ""

def parse_duration_minutes(_: Dict[str, Any]) -> int:
    return 60  # default; tweak if you scrape real durations later

def compute_location(item: Dict[str, Any]) -> str:
    city = (item.get("teacherCity") or "").strip()
    f2f = bool(item.get("faceToFace"))
    webcam = bool(item.get("webcam"))
    if f2f and webcam:
        return city + (" / Online" if city else "Online")
    if f2f:
        return city or "Setempat"
    if webcam:
        return "Online"
    return city or "Tidak disebutkan"

def safe_decimal(x: Any) -> Decimal:
    try:
        return Decimal(str(x)).quantize(Decimal("0.00"))
    except Exception:
        return Decimal("0.00")

def normalize_superprof_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for it in payload.get("mainResults", []):
        title = (it.get("title") or "").strip()
        url_path = (it.get("url") or "").strip()
        source_url = ("https://www.superprof.co.id" + url_path) if url_path.startswith("/") else url_path

        flags = []
        if it.get("firstHourFree"):
            dur = it.get("firstFreeDuration") or ""
            flags.append(f"Free trial: {dur or 'yes'}")
        if it.get("faceToFace"):
            flags.append("Tatap muka")
        if it.get("webcam"):
            flags.append("Online")
        if it.get("verified"):
            flags.append("Verified")

        description = f"{title}\n\nSumber: {source_url}\n" + (" • ".join(flags) if flags else "")

        rows.append(
            {
                "coach_name": it.get("teacherName") or "",
                "rating": safe_decimal(((it.get("teacherRating") or {}).get("average"))),
                "title": title or "(Tanpa judul)",
                "description": description.strip(),
                "price": parse_price(it),
                "location": compute_location(it),
                "duration": parse_duration_minutes(it),
                "thumbnail_url": best_thumbnail(it),
            }
        )
    return rows


# ---- DB ingest ----
@transaction.atomic
def ingest_rows(rows: List[Dict[str, Any]]) -> Tuple[int, int]:
    coach_touched = 0
    course_touched = 0

    for row in rows:
        user = get_or_create_user_by_name(row["coach_name"])
        coach, _ = Coach.objects.get_or_create(user=user)
        coach.rating = row["rating"] or Decimal("0.00")
        coach.save(update_fields=["rating"])
        coach_touched += 1

        # Upsert Course by (coach, title)
        course, created = Course.objects.get_or_create(
            coach=coach,
            title=row["title"],
            defaults={
                "description": row["description"],
                "price": row["price"],
                "location": row["location"],
                "duration": row["duration"],
                "thumbnail_url": row["thumbnail_url"],
            },
        )
        if not created:
            course.description = row["description"]
            course.price = row["price"]
            course.location = row["location"]
            course.duration = row["duration"]
            course.thumbnail_url = row["thumbnail_url"]
            course.save(update_fields=["description", "price", "location", "duration", "thumbnail_url"])

        course_touched += 1

    return coach_touched, course_touched


# ---- Fetching / Paging ----
def set_page_in_url(url: str, page: int) -> str:
    """Replace or inject 'page' query param."""
    parsed = urllib.parse.urlsplit(url)
    q = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    q["page"] = str(page)
    new_query = urllib.parse.urlencode(q, doseq=True)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))

def fetch_json(url: str, session: requests.Session, sleep: float, max_retries: int) -> Dict[str, Any]:
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code >= 500:
                raise RuntimeError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_error = e
            time.sleep(min(sleep * attempt, 10))  # simple backoff
    raise CommandError(f"Failed to fetch {url}: {last_error}")

def crawl_once(base_url: str, start_page: int, end_page: int | None, sleep: float, max_retries: int) -> tuple[int, int]:
    """
    Crawl pages from start_page..end_page (inclusive). If end_page is None, use nbPagesTotal from page 1.
    Returns total (coaches_touched, courses_upserted).
    """
    coaches_total = 0
    courses_total = 0

    with requests.Session() as s:
        # Determine last page if not provided
        if end_page is None:
            first_url = set_page_in_url(base_url, start_page)
            payload = fetch_json(first_url, s, sleep, max_retries)
            last = int(payload.get("nbPagesTotal") or payload.get("nb_pages_total") or 1)
            end_page = last

            rows = normalize_superprof_payload(payload)
            c1, c2 = ingest_rows(rows)
            coaches_total += c1
            courses_total += c2
            time.sleep(sleep)

        # Remaining pages
        for page in range(start_page + 1, end_page + 1):
            url = set_page_in_url(base_url, page)
            payload = fetch_json(url, s, sleep, max_retries)
            rows = normalize_superprof_payload(payload)
            c1, c2 = ingest_rows(rows)
            coaches_total += c1
            courses_total += c2
            time.sleep(sleep)

    return coaches_total, courses_total


# ---- Management command ----
class Command(BaseCommand):
    help = "Crawl Superprof JSON pages and ingest into Coach/Course. Supports looping pages and optional repetition."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="Base Superprof JSON URL (with any page=... value).")
        parser.add_argument("--start-page", type=int, default=1, help="First page to crawl (default: 1).")
        parser.add_argument("--end-page", type=int, default=None, help="Last page to crawl. Omit to auto-detect.")
        parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between requests (default: 1.0).")
        parser.add_argument("--max-retries", type=int, default=3, help="Max retries per request (default: 3).")
        parser.add_argument("--repeat-every", type=int, default=None,
                            help="If set (seconds), repeat the whole crawl indefinitely at this interval.")

    def handle(self, *args, **opts):
        base_url = opts["url"]
        start_page = int(opts["start_page"])
        end_page = opts["end_page"]
        sleep = float(opts["sleep"])
        max_retries = int(opts["max_retries"])
        repeat_every = opts["repeat_every"]

        if start_page < 1:
            raise CommandError("start-page must be >= 1")

        try:
            while True:
                # reset user cache per run so merges are stable but memory stays bounded
                _USER_BY_NAME_CACHE.clear()

                coaches, courses = crawl_once(
                    base_url=base_url,
                    start_page=start_page,
                    end_page=end_page,
                    sleep=sleep,
                    max_retries=max_retries,
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Crawl OK: touched {coaches} coaches; upserted {courses} courses."
                ))

                if not repeat_every:
                    break
                time.sleep(repeat_every)

        except Exception as e:
            raise CommandError(str(e)) from e
