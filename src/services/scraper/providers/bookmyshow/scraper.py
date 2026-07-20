# src/services/scraper/providers/bookmyshow/scraper.py

import logging
import re
import asyncio
from urllib.parse import urlparse
from typing import List, Tuple, Optional, Dict, Any

import httpx
from bs4 import BeautifulSoup

from src.services.scraper.providers.base import BookingChecker

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
    # Match: .../buytickets/<code>/<date>  (date is 8 digits)
    match = re.search(r'(/buytickets/[^/]+/)(\d{8})', url)
    if match:
        return url[:match.start(2)] + date_str + url[match.end(2):]
    # If no date in URL, just append
    return url.rstrip("/") + "/" + date_str


def _extract_movie_name(soup: BeautifulSoup, url: str) -> str:
    """
    Attempts to extract the movie name from the parsed HTML.
    Falls back to a humanised slug from the URL if not found.
    """
    # BMS renders the movie name as an <a> linking to /movies/<city>/<slug>/<code>
    parsed = urlparse(url)
    slug_match = re.search(r'/movies/[^/]+/([^/]+)', parsed.path)
    fallback = slug_match.group(1).replace("-", " ").title() if slug_match else "Movie"

    try:
        # The anchor that links back to the movie detail page
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
    # Regex: grab one or more .className selectors immediately before a { block
    # that contains cursor:not-allowed somewhere inside it.
    rule_re = re.compile(
        r'([.][\w-]+(?:[,\s]*[.][\w-]+)*)\s*\{[^}]*cursor\s*:\s*not-allowed[^}]*\}',
        re.IGNORECASE,
    )
    selector_re = re.compile(r'[.][\w-]+')

    for style_tag in soup.find_all("style"):
        css = style_tag.get_text()
        for rule_match in rule_re.finditer(css):
            # A selector block may contain multiple comma-separated classes
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
        headless: bool = True,       # kept for API compatibility, unused
        keep_browser_open: bool = True,  # kept for API compatibility, unused
        **kwargs,
    ) -> Tuple[bool, str, Optional[str], List[str], List[str]]:
        url = params.get("url", "")
        date_str = params.get("date_str", "")
        theatres = params.get("theatres", [])

        log = kwargs.get("logger", logger)

        # Build the URL that already points at the requested date
        target_url = _build_date_url(url, date_str)
        log.info(
            f"Starting BookMyShow booking check | URL: {target_url} | "
            f"Date: {date_str} | Theatres: {theatres}"
        )

        # --- 1. Fetch the page ---
        try:
            html = await asyncio.to_thread(self._fetch, target_url, log)
        except Exception as exc:
            log.error(f"HTTP request failed: {exc}")
            return (
                False,
                "A temporary error occurred while checking ticket availability. We will try again shortly.",
                None,
                [],
                theatres,
            )

        # --- 2. Parse HTML ---
        soup = BeautifulSoup(html, "html.parser")
        movie_name = _extract_movie_name(soup, url)
        log.info(f"Movie name resolved to: {movie_name!r}")

        # Collect classes that have cursor:not-allowed in the page CSS
        not_allowed_classes = _get_not_allowed_classes(soup)
        log.info(f"cursor:not-allowed classes found: {not_allowed_classes}")

        # --- 3. Check the date element ---
        date_el = soup.find(id=date_str)
        if date_el is None:
            log.warning(f"Date element '{date_str}' not found in page.")
            return (
                False,
                f"Booking has not opened for {date_str} yet.",
                movie_name,
                [],
                theatres,
            )

        if _is_date_disabled(date_el, not_allowed_classes):
            classes = " ".join(date_el.get("class", []))
            log.warning(
                f"Date '{date_str}' found but has cursor:not-allowed. Classes: {classes!r}"
            )
            return (
                False,
                f"Booking has not opened for {date_str} yet.",
                movie_name,
                [],
                theatres,
            )

        log.info(f"Date '{date_str}' is present and clickable (no cursor:not-allowed).")

        # --- 4. Check theatre availability ---
        # Theatre names are rendered inside <span> elements on the showtimes page.
        # We collect the text of every <span> and do a substring search.
        span_texts = [span.get_text(strip=True) for span in soup.find_all("span")]

        available_theatres: List[str] = []
        missing_theatres: List[str] = []

        for theatre in theatres:
            found = any(theatre in text for text in span_texts)
            if found:
                available_theatres.append(theatre)
                log.info(f"Theatre found in span: {theatre!r}")
            else:
                missing_theatres.append(theatre)
                log.warning(f"Theatre NOT found in any span: {theatre!r}")

        if not available_theatres:
            log.warning(
                f"Date '{date_str}' is clickable, but none of the specified theatres "
                f"were found ({', '.join(theatres)})."
            )
            return (
                False,
                f"Booking is open for {date_str}, but showtimes at your selected theatres are not available yet.",
                movie_name,
                [],
                theatres,
            )

        # --- 5. Success ---
        success_details = (
            f"Booking is OPEN for date {date_str}! "
            f"Found theatres: {', '.join(available_theatres)}."
        )
        if missing_theatres:
            success_details += f" (Unavailable: {', '.join(missing_theatres)})"

        log.info(success_details)
        return True, success_details, movie_name, available_theatres, missing_theatres

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch(self, url: str, log) -> str:
        """
        Synchronous HTTP GET with browser-like headers.
        Runs in a thread via asyncio.to_thread so it doesn't block the event loop.
        """
        log.info(f"Fetching URL: {url}")
        with httpx.Client(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=30.0,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            log.info(f"Response: HTTP {response.status_code} ({len(response.text)} chars)")
            return response.text

    async def close(self) -> None:
        """No persistent resources to release."""
        pass
