# src/services/scraper/providers/bookmyshow/scraper.py

import logging
import re
import asyncio
from urllib.parse import urlparse
from typing import List, Tuple, Optional, Dict, Any

import httpx
from bs4 import BeautifulSoup

from ..base import BookingChecker

logger = logging.getLogger(__name__)

# Browser-like headers to bypass bot detection
_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Service-Worker-Navigation-Preload": "true",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
    ),
    "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Microsoft Edge";v="150"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def _build_date_url(url: str, date_str: str) -> str:
    """
    Rewrites the date segment at the end of a BMS buy-tickets URL.
    E.g. .../buytickets/ET00480917/20260720  ->  .../buytickets/ET00480917/20260721
    If the URL already ends with the correct date (or has no date segment), returns it as-is.
    """
    match = re.search(r'(/buytickets/[^/]+/)(\d{8})', url)
    if match:
        return url[:match.start(2)] + date_str + url[match.end(2):]
    return url.rstrip("/") + "/" + date_str


def _extract_movie_name(soup: BeautifulSoup, url: str) -> str:
    """
    Attempts to extract the movie name from the parsed HTML.
    Falls back to a humanised slug from the URL if not found.
    """
    parsed = urlparse(url)
    slug_match = re.search(r'/movies/[^/]+/([^/]+)', parsed.path)
    fallback = slug_match.group(1).replace("-", " ").title() if slug_match else "Movie"

    try:
        code_match = re.search(r'/buytickets/([^/]+)', parsed.path)
        if code_match:
            event_code = code_match.group(1)
            link = soup.find("a", href=re.compile(re.escape(event_code)))
            if link:
                name = link.get_text(strip=True)
                if name:
                    return name
    except Exception:
        pass

    return fallback


def _get_not_allowed_classes(soup: BeautifulSoup) -> set:
    """
    Parses every <style> block in the page and collects CSS class names
    whose rules contain 'cursor:not-allowed' (BMS uses this for unavailable dates).
    Returns a set of bare class names (without the leading dot).
    """
    not_allowed: set = set()
    rule_re = re.compile(
        r'([.][\w-]+(?:[,\s]*[.][\w-]+)*)\s*\{[^}]*cursor\s*:\s*not-allowed[^}]*\}',
        re.IGNORECASE,
    )
    selector_re = re.compile(r'[.][\w-]+')

    for style_tag in soup.find_all("style"):
        css = style_tag.get_text()
        for rule_match in rule_re.finditer(css):
            for sel in selector_re.finditer(rule_match.group(1)):
                not_allowed.add(sel.group(0)[1:])  # strip leading dot

    return not_allowed


def _is_date_disabled(date_el, not_allowed_classes: set) -> bool:
    """
    Returns True if the date element carries any CSS class that is
    associated with cursor:not-allowed in the page's stylesheets.
    """
    element_classes = set(date_el.get("class", []))
    return bool(element_classes & not_allowed_classes)


def _fmt_date(date_str: str) -> str:
    """Formats YYYYMMDD as a readable date string, e.g. '21 Jul 2026'."""
    try:
        from datetime import datetime
        return datetime.strptime(date_str, "%Y%m%d").strftime("%d %b %Y")
    except Exception:
        return date_str


class BookMyShowBookingChecker(BookingChecker):
    """
    Concrete scraper implementing the BookingChecker interface for BookMyShow
    using httpx (HTTP) + BeautifulSoup (HTML parsing). No browser required.
    """

    @classmethod
    def get_required_fields(cls) -> Dict[str, Dict[str, Any]]:
        """
        Declares metadata about BookMyShow required inputs.
        """
        return {
            "url": {
                "type": "text",
                "label": "Movie Page URL 🔗",
                "placeholder": "https://in.bookmyshow.com/buytickets/movie-name/...",
                "help": "Copy the exact URL of the movie booking page containing the date selectors.",
            },
            "date_str": {
                "type": "date",
                "label": "Target Date 📅",
                "help": "Select the date you want to monitor.",
            },
            "theatres": {
                "type": "text_area",
                "label": "Target Theatre Name(s) 🏢",
                "placeholder": "PVR: ECX Chanakyapuri\nINOX: Insignia Epicuria",
                "help": (
                    "Enter one theatre name per line. "
                    "Substring match is supported, but it is strictly case-sensitive!"
                ),
            },
        }

    async def check_booking(
        self,
        params: Dict[str, Any],
        **kwargs,
    ) -> Tuple[bool, str, Optional[str], List[str], List[str]]:
        url = params.get("url", "")
        date_str = params.get("date_str", "")
        theatres = params.get("theatres", [])

        log = kwargs.get("logger", logger)
        date_display = _fmt_date(date_str)

        target_url = _build_date_url(url, date_str)
        log.debug(f"Fetching: {target_url}")

        # --- 1. Fetch the page ---
        try:
            html = await asyncio.to_thread(self._fetch, target_url, log)
        except Exception as exc:
            log.error(
                f"⚠️  Could not reach BookMyShow. "
                f"Please check your internet connection and try again. ({exc})"
            )
            return (
                False,
                "Could not reach BookMyShow. Will retry shortly.",
                None,
                [],
                theatres,
            )

        # --- 2. Parse HTML ---
        soup = BeautifulSoup(html, "html.parser")
        movie_name = _extract_movie_name(soup, url)
        not_allowed_classes = _get_not_allowed_classes(soup)
        log.debug(f"cursor:not-allowed classes: {not_allowed_classes}")

        # --- 3. Check the date ---
        date_el = soup.find(id=date_str)
        if date_el is None:
            log.info(
                f"📅  {date_display} — Booking has not opened yet. "
                f"Tickets for \"{movie_name}\" are not available on this date. Will keep checking..."
            )
            return (
                False,
                f"Booking has not opened for {date_display} yet.",
                movie_name,
                [],
                theatres,
            )

        if _is_date_disabled(date_el, not_allowed_classes):
            log.info(
                f"📅  {date_display} — This date is not yet bookable. "
                f"Tickets for \"{movie_name}\" are greyed out. Will keep checking..."
            )
            return (
                False,
                f"Booking has not opened for {date_display} yet.",
                movie_name,
                [],
                theatres,
            )

        log.info(f"✅  {date_display} — Booking is open for \"{movie_name}\"! Now checking your theatres...")

        # --- 4. Check theatre availability ---
        # Collect candidate venue strings from HTML elements, <span> tags, and embedded JSON scripts
        candidate_venue_texts: List[str] = []

        # 1. Local cinema <a> links (excluding general chain directory links)
        for a_tag in soup.find_all("a", href=re.compile(r'/cinemas/', re.IGNORECASE)):
            href = a_tag.get("href", "")
            if "/cinemas-list/" not in href:
                txt = a_tag.get_text(strip=True)
                if txt:
                    candidate_venue_texts.append(txt)
                for span in a_tag.find_all("span"):
                    stxt = span.get_text(strip=True)
                    if stxt:
                        candidate_venue_texts.append(stxt)

        # 2. Venue card containers (class names containing venue/cinema/facility/showtime)
        for el in soup.find_all(class_=re.compile(r'venue|cinema|facility|showtime', re.IGNORECASE)):
            txt = el.get_text(strip=True)
            if txt and len(txt) < 200:
                candidate_venue_texts.append(txt)

        # 3. Embedded JSON script tags (window.__INITIAL_STATE__ contains all active showing cinemas)
        for s_tag in soup.find_all("script"):
            if s_tag.string and "venueName" in s_tag.string:
                for match in re.findall(r'"venueName"\s*:\s*"([^"]+)"', s_tag.string):
                    cleaned = match.encode('utf-8').decode('unicode_escape', errors='ignore') if '\\u' in match else match
                    if cleaned:
                        candidate_venue_texts.append(cleaned)

        available_theatres: List[str] = []
        missing_theatres: List[str] = []

        for theatre in theatres:
            if not theatre:
                continue

            # Exact case-sensitive substring match
            found = any(theatre in text for text in candidate_venue_texts)

            if found:
                available_theatres.append(theatre)
                log.info(f"🎬  Found: \"{theatre}\" is showing on {date_display}.")
            else:
                missing_theatres.append(theatre)
                log.info(f"🔍  Not yet listed: \"{theatre}\" has no shows on {date_display} yet.")

        if not available_theatres:
            log.info(
                f"⏳  {date_display} — Booking is open but none of your selected theatres "
                f"have shows yet. Will keep checking..."
            )
            return (
                False,
                f"Booking is open for {date_display}, but your selected theatres are not showing yet.",
                movie_name,
                [],
                theatres,
            )

        # --- 5. Success ---
        found_list = ", ".join(available_theatres)
        missing_list = ", ".join(missing_theatres)

        log.info(
            f"🎉  Tickets available! \"{movie_name}\" on {date_display} "
            f"is now showing at: {found_list}."
            + (f" (Not yet listed: {missing_list})" if missing_theatres else "")
        )

        success_details = (
            f"Booking is OPEN for {date_display}! "
            f"Found theatres: {found_list}."
        )
        if missing_theatres:
            success_details += f" (Unavailable: {missing_list})"

        return True, success_details, movie_name, available_theatres, missing_theatres

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch(self, url: str, log) -> str:
        """
        Synchronous HTTP GET using browser impersonation (curl_cffi / system curl)
        to bypass Cloudflare TLS fingerprinting (403 Forbidden).
        Runs in a thread via asyncio.to_thread so it doesn't block the event loop.
        """
        log.debug(f"GET {url}")

        # 1. Try curl_cffi for browser TLS fingerprint impersonation (bypasses WAF 403)
        try:
            from curl_cffi import requests as curl_requests
            res = curl_requests.get(
                url,
                headers=_HEADERS,
                impersonate="chrome",
                timeout=30.0,
                allow_redirects=True,
            )
            res.raise_for_status()
            log.debug(f"HTTP {res.status_code} (via curl_cffi) — {len(res.text):,} bytes received")
            return res.text
        except Exception as exc:
            log.debug(f"curl_cffi fetch failed ({exc}), attempting system curl fallback...")

        # 2. Try system curl subprocess (uses native OS TLS stack)
        import subprocess
        try:
            cmd = [
                "curl.exe" if subprocess.os.name == "nt" else "curl",
                "-s", "-L",
                "-A", _HEADERS.get("User-Agent", "Mozilla/5.0"),
                url,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            if proc.stdout and len(proc.stdout) > 500:
                log.debug(f"HTTP 200 (via system curl) — {len(proc.stdout):,} bytes received")
                return proc.stdout
        except Exception as exc:
            log.debug(f"System curl subprocess failed ({exc}), falling back to httpx...")

        # 3. Fallback to httpx
        with httpx.Client(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=30.0,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            log.debug(f"HTTP {response.status_code} (via httpx) — {len(response.text):,} bytes received")
            return response.text

    async def close(self) -> None:
        """No persistent resources to release."""
        pass

