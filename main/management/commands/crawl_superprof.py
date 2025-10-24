"""
Superprof Crawler for MamiCoach

This script crawls course data from Superprof.co.id and populates the database
with coaches and courses for a specific category.

IMPORTANT: Cookie Management
-----------------------------
The cookies in DEFAULT_COOKIES may expire. If you get 401/403 errors:

1. Open https://www.superprof.co.id in your browser
2. Open DevTools (F12) → Network tab
3. Perform a search for any category
4. Find the /a/search/ XHR request
5. Copy the Cookie header value
6. Update DEFAULT_COOKIES dictionary below with new values

Example curl to get fresh cookies:
  curl 'https://www.superprof.co.id/a/search/?...' \
    -H 'cookie: YOUR_COOKIES_HERE'

Last updated: 2025-10-24
"""

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

from courses_and_coach.models import Course, Category
from user_profile.models import CoachProfile

# ---- HTTP / crawler config ----
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Referer": "https://www.superprof.co.id/",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "priority": "u=1, i",
}

DEFAULT_COOKIES = {
    "_ga": "GA1.1.593887945.1759888737",
    "FPAU": "1.3.707295259.1759888735",
    "_gcl_au": "1.1.1728353881.1759888739",
    "axeptio_cookies": '{"$$token":"1gwvc4m0dj7dnxbwexatv","$$date":"2025-10-08T01:59:00.712Z","$$cookiesVersion":{},"$$completed":false}',
    "axeptio_authorized_vendors": ",,",
    "axeptio_all_vendors": ",,",
    "PHPSESSID": "5215867079ad989e5ee2f1c5f728b160",
    "first_referrer": "direct",
    "datadome": "TmyxX8TNTZETE9ZmGcdnmqcRFNNHGvLWGk2SNpZ863ugM~gC9vxscFJCaeJXH_8jhhkAFC7d~m4eQ8Pjc6mluA3~k0CMvMNIcnaoO_Li7YR3rNW0YkAUHYTUhsBMO9Vq",
    "_ga_S08FDGF6K5": "GS2.1.s1761322099$o5$g1$t1761322112$j47$l0$h396286546",
}

REQUEST_TIMEOUT = 20  # seconds
MAX_RETRIES_DEFAULT = 3
SLEEP_DEFAULT = 1.0

# ---- Business rules ----
PRICE_MIN_RP = 10_000  # If parsed number < 10k, treat as thousands (e.g., "120" -> 120_000)

# in-run cache: name(lower) -> user id (to reduce DB hits per run)
_USER_BY_NAME_CACHE: dict[str, int] = {}


# ----------------------------
# Helpers: names / users
# ----------------------------
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
    """
    Reuse the same User if the same coach name appears (case-insensitive).
    """
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


# ----------------------------
# Normalizers
# ----------------------------
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
    return city[:200] or "Tidak disebutkan"

def safe_decimal(x: Any) -> Decimal:
    try:
        return Decimal(str(x)).quantize(Decimal("0.00"))
    except Exception:
        return Decimal("0.00")

def normalize_superprof_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Produce rows the DB layer expects.
    """
    rows: List[Dict[str, Any]] = []
    for it in payload.get("mainResults", []):
        title = (it.get("title") or "").strip()[:200]
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

        # teacher rating (sometimes count==0 but average present) -> we still set as initial value
        teacher_avg = safe_decimal(((it.get("teacherRating") or {}).get("average")))

        rows.append(
            {
                "coach_name": it.get("teacherName") or "",
                "coach_image_url": best_thumbnail(it),
                "coach_rating": teacher_avg,            # goes to Coach.rating (seed)
                "course_title": title or "(Tanpa judul)",
                "course_description": description.strip(),
                "course_price": parse_price(it),
                "course_location": compute_location(it),
                "course_duration": parse_duration_minutes(it),
                "course_thumbnail_url": best_thumbnail(it),
                "course_rating": teacher_avg,           # seed Course.rating too
            }
        )
    return rows


# ----------------------------
# DB ingest (with Category)
# ----------------------------
@transaction.atomic
def ingest_rows(rows: List[Dict[str, Any]], category: Category) -> Tuple[int, int]:
    """
    Upsert Users/Coaches/Courses and attach every course to `category`.
    Returns (coaches_touched, courses_upserted).
    """
    coach_touched = 0
    course_touched = 0

    for row in rows:
        # 1) User (reuse by same name)
        user = get_or_create_user_by_name(row["coach_name"])

        # 2) CoachProfile 1:1 with User, set rating + image_url (seed)
        coach, created = CoachProfile.objects.get_or_create(
            user=user,
            defaults={
                "bio": f"Pelatih profesional di bidang {category.name}",
                "expertise": [category.name],
            }
        )
        # Seed/refresh rating & image
        coach.rating = row["coach_rating"] or Decimal("0.00")
        if row.get("coach_image_url"):
            coach.profile_image_url = row["coach_image_url"]
            coach.save(update_fields=["rating", "profile_image_url"])
        else:
            coach.save(update_fields=["rating"])
        coach_touched += 1

        # 3) Course upsert by (coach, title), and force category for this run
        course, created = Course.objects.get_or_create(
            coach=coach,
            title=row["course_title"],
            defaults={
                "category": category,
                "rating": row["course_rating"] or Decimal("0.00"),
                "description": row["course_description"],
                "price": row["course_price"],
                "location": row["course_location"],
                "duration": row["course_duration"],
                "thumbnail_url": row["course_thumbnail_url"],
            },
        )

        if not created:
            # Update always; also **attach to this session’s category** as requested
            course.category = category
            course.rating = row["course_rating"] or Decimal("0.00")
            course.description = row["course_description"]
            course.price = row["course_price"]
            course.location = row["course_location"]
            course.duration = row["course_duration"]
            course.thumbnail_url = row["course_thumbnail_url"]
            course.save(update_fields=[
                "category", "rating", "description", "price", "location", "duration", "thumbnail_url"
            ])

        course_touched += 1

    return coach_touched, course_touched


# ----------------------------
# Fetching / Paging
# ----------------------------
def set_page_in_url(url: str, page: int) -> str:
    parsed = urllib.parse.urlsplit(url)
    q = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    q["page"] = str(page)
    new_query = urllib.parse.urlencode(q, doseq=True)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))

def fetch_json(url: str, session: requests.Session, sleep: float, max_retries: int) -> Dict[str, Any]:
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, headers=DEFAULT_HEADERS, cookies=DEFAULT_COOKIES, timeout=REQUEST_TIMEOUT)
            if resp.status_code >= 500:
                raise RuntimeError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_error = e
            time.sleep(min(sleep * attempt, 10))  # simple backoff
    raise CommandError(f"Failed to fetch {url}: {last_error}")

def crawl_once(base_url: str, start_page: int, end_page: int | None, sleep: float, max_retries: int, category: Category) -> tuple[int, int]:
    """
    Crawl pages start_page..end_page (inclusive). If end_page is None, use nbPagesTotal from the first page.
    """
    coaches_total = 0
    courses_total = 0

    with requests.Session() as s:
        # First page (and auto-detect last if needed)
        first_url = set_page_in_url(base_url, start_page)
        payload = fetch_json(first_url, s, sleep, max_retries)
        last = int(payload.get("nbPagesTotal") or payload.get("nb_pages_total") or (end_page or 1))
        if end_page is None:
            end_page = last

        rows = normalize_superprof_payload(payload)
        c1, c2 = ingest_rows(rows, category)
        coaches_total += c1
        courses_total += c2
        time.sleep(sleep)

        # Remaining pages
        for page in range(start_page + 1, end_page + 1):
            url = set_page_in_url(base_url, page)
            payload = fetch_json(url, s, sleep, max_retries)
            rows = normalize_superprof_payload(payload)
            c1, c2 = ingest_rows(rows, category)
            coaches_total += c1
            courses_total += c2
            time.sleep(sleep)

    return coaches_total, courses_total


# ----------------------------
# Management command
# ----------------------------
class Command(BaseCommand):
    help = "Crawl Superprof JSON pages and ingest into Coach/Course for a given Category."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="Base Superprof JSON URL (any page=... value is fine).")
        parser.add_argument("--category", required=True, help="Category name. Created if missing; all upserts linked to it.")
        parser.add_argument("--category-thumb", default=None, help="(Optional) Category thumbnail URL if creating new.")
        parser.add_argument("--category-desc", default=None, help="(Optional) Category description if creating new.")
        parser.add_argument("--start-page", type=int, default=1, help="First page to crawl (default: 1).")
        parser.add_argument("--end-page", type=int, default=None, help="Last page to crawl. Omit to auto-detect.")
        parser.add_argument("--sleep", type=float, default=SLEEP_DEFAULT, help="Seconds to sleep between requests.")
        parser.add_argument("--max-retries", type=int, default=MAX_RETRIES_DEFAULT, help="Max retries per request.")
        parser.add_argument("--repeat-every", type=int, default=None,
                            help="If set (seconds), repeat the whole crawl indefinitely at this interval.")

    def handle(self, *args, **opts):
        base_url = opts["url"]
        category_name = opts["category"].strip()
        category_thumb = opts.get("category_thumb")
        category_desc = opts.get("category_desc")
        start_page = int(opts["start_page"])
        end_page = opts["end_page"]
        sleep = float(opts["sleep"])
        max_retries = int(opts["max_retries"])
        repeat_every = opts["repeat_every"]

        if start_page < 1:
            raise CommandError("start-page must be >= 1")
        if not category_name:
            raise CommandError("--category cannot be empty")

        try:
            while True:
                # Reset cache per full run
                _USER_BY_NAME_CACHE.clear()

                # Get or create Category once per run
                category, created = Category.objects.get_or_create(
                    name=category_name,
                    defaults={"thumbnailUrl": category_thumb, "description": category_desc},
                )
                # If it existed and you passed new metadata, you can uncomment to update it:
                # else:
                #     changed = False
                #     if category_thumb and category.thumbnailUrl != category_thumb:
                #         category.thumbnailUrl = category_thumb; changed = True
                #     if category_desc and category.description != category_desc:
                #         category.description = category_desc; changed = True
                #     if changed: category.save(update_fields=["thumbnailUrl", "description"])

                coaches, courses = crawl_once(
                    base_url=base_url,
                    start_page=start_page,
                    end_page=end_page,
                    sleep=sleep,
                    max_retries=max_retries,
                    category=category,
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Crawl OK (category='{category.name}'): touched {coaches} coaches; upserted {courses} courses."
                ))

                if not repeat_every:
                    break
                time.sleep(repeat_every)

        except Exception as e:
            raise CommandError(str(e)) from e
