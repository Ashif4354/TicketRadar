# src/Backend/api/routers/bms_proxy.py

import re
import json
import logging
import time
import asyncio
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Set
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from lib.core.auth import get_authorized_user

logger = logging.getLogger("ticketradar.api.bms")

router = APIRouter(prefix="/api/bms", tags=["BookMyShow Proxy"])

_bms_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="bms_fetch")

REGION_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,20}$")
REGION_SLUG_PATTERN = re.compile(r"^[a-z0-9_-]{1,50}$")
LAT_LON_PATTERN = re.compile(r"^-?\d{1,3}\.\d{1,8}$")
GEOHASH_PATTERN = re.compile(r"^[a-z0-9]{1,12}$")
EVENT_CODE_PATTERN = re.compile(r"^ET\d{8}$", re.IGNORECASE)

_CITY_ALIASES_CACHE: Dict[str, Set[str]] = {}
_LOCATION_TAIL_RE = re.compile(r',\s*([^,]+),\s*([A-Z]{2}),\s*(\d{6})\s*$')


def _get_city_aliases(region_code: str, region_slug: str, city_name: str = "") -> Set[str]:
    """
    Returns a set of normalized name aliases and satellite names for a given city region.
    """
    global _CITY_ALIASES_CACHE
    if not _CITY_ALIASES_CACHE:
        try:
            p = Path(__file__).resolve().parents[3] / "UI" / "src" / "assets" / "cities.json"
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                bms = data.get("BookMyShow", {})
                for c in bms.get("TopCities", []) + bms.get("OtherCities", []):
                    code = (c.get("RegionCode") or c.get("SubRegionCode") or "").upper()
                    if not code:
                        continue
                    s = _CITY_ALIASES_CACHE.setdefault(code, set())
                    if c.get("RegionName"):
                        s.add(c["RegionName"].lower().strip())
                    if c.get("RegionSlug"):
                        s.add(c["RegionSlug"].lower().replace("-", " ").strip())
                    if c.get("Alias"):
                        for a in c["Alias"]:
                            if isinstance(a, str):
                                s.add(a.lower().replace("-", " ").strip())
                    for sub in c.get("SubRegions", []):
                        if sub.get("SubRegionName"):
                            s.add(sub["SubRegionName"].lower().strip())
                        if sub.get("SubRegionSlug"):
                            s.add(sub["SubRegionSlug"].lower().replace("-", " ").strip())
        except Exception as e:
            logger.warning(f"Could not load cities.json for aliases: {e}")

    r_code = (region_code or "").strip().upper()
    aliases = set(_CITY_ALIASES_CACHE.get(r_code, set()))
    if region_slug:
        aliases.add(region_slug.lower().replace("-", " ").strip())
    if city_name:
        aliases.add(city_name.lower().replace("-", " ").strip())

    # Well-known city synonyms and satellite hubs
    if r_code == "BANG":
        aliases.add("bangalore")
    elif r_code == "MUMBAI":
        aliases.update({"bombay", "navi mumbai", "thane", "kalyan", "ulhasnagar"})
    elif r_code == "NCR":
        aliases.update({"delhi", "new delhi", "noida", "greater noida", "gurugram", "gurgaon", "ghaziabad", "faridabad"})
    elif r_code == "CHEN":
        aliases.update({"chennai", "madras"})
    elif r_code == "KOLK":
        aliases.update({"kolkata", "calcutta", "howrah"})
    elif r_code == "PUNE":
        aliases.update({"pune", "pcmc", "pimpri", "chinchwad"})
    elif r_code == "HYD":
        aliases.update({"hyderabad", "secunderabad"})
    elif r_code in ("AHD", "AHMED"):
        aliases.update({"ahmedabad", "gandhinagar"})
    elif r_code in ("KOCH", "KOCHI"):
        aliases.update({"kochi", "cochin", "ernakulam"})

    return aliases


def _parse_venue_location(location: str):
    """
    Parses BMS venue location string:
    '...India, Chennai, TN, 600027' -> (city: 'Chennai', state: 'TN', pin: '600027')
    """
    if not location:
        return "", "", ""
    m = _LOCATION_TAIL_RE.search(location)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return "", "", ""


def _is_venue_in_city(
    title: str,
    location: str,
    bms_url: str,
    region_code: str,
    region_slug: str,
    city_name: str = ""
) -> bool:
    """
    Determines whether a theatre belongs to the target city/region.
    """
    aliases = _get_city_aliases(region_code, region_slug, city_name)
    if not aliases:
        return True

    parsed_city, _, _ = _parse_venue_location(location)
    parsed_city_lower = parsed_city.lower()

    # 1. Match against parsed city from location tail
    if parsed_city_lower:
        for a in aliases:
            if a == parsed_city_lower or a in parsed_city_lower or parsed_city_lower in a:
                return True

    # 2. Match against full location text or title
    loc_lower = location.lower()
    title_lower = title.lower()
    for a in aliases:
        if len(a) >= 3 and (a in loc_lower or a in title_lower):
            return True

    clean_region = region_code.upper()
    if f"/cinemas/{clean_region}/" in bms_url.upper() or f"-{clean_region.lower()}/" in bms_url.lower():
        return True

    return False


def _validate_param(value: str, pattern: re.Pattern, name: str) -> str:
    cleaned = value.strip()
    if not pattern.match(cleaned):
        raise HTTPException(status_code=400, detail=f"Invalid parameter format for '{name}'.")
    return cleaned



def _is_valid_bms_json(text: str) -> bool:
    """
    Determine whether response text appears to contain valid, unblocked JSON.
    
    Parameters:
        text (str): Response body to validate.
    
    Returns:
        bool: `true` if the text is sufficiently long, does not contain known Cloudflare challenge markers, and begins with a JSON object or array; `false` otherwise.
    """
    if not text or len(text) < 10:
        return False
    text_lower = text.lower()
    if "attention required" in text_lower or "just a moment" in text_lower or "cf-browser-verification" in text_lower:
        return False
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def _sanitize_header_value(val: str) -> str:
    return re.sub(r"[\r\n]+", "", str(val))


def _fetch_bms_api(url: str, api_headers: dict, log) -> dict:
    """
    Fetch and parse a BookMyShow API response using multiple HTTP strategies.
    
    Parameters:
        url (str): The BookMyShow API URL.
        api_headers (dict): HTTP headers required by the request.
    
    Returns:
        dict: The decoded JSON response.
    
    Raises:
        RuntimeError: If all request strategies fail or the response is blocked or invalid.
    """
    log.debug(f"GET BMS API: {url}")
    start_time = time.time()
    overall_deadline = 15.0

    # 1. Try curl_cffi with fresh impersonation per attempt
    try:
        from curl_cffi import requests as curl_requests
        impersonate_targets = ["chrome120", "chrome110", "chrome"]
        for attempt, imp in enumerate(impersonate_targets):
            elapsed = time.time() - start_time
            remaining = overall_deadline - elapsed
            if remaining <= 0:
                break
            if attempt > 0:
                time.sleep(min(0.2, remaining))
            try:
                attempt_timeout = min(5.0, remaining)
                res = curl_requests.get(
                    url,
                    headers=api_headers,
                    impersonate=imp,
                    timeout=attempt_timeout,
                    allow_redirects=True,
                )
                if res.status_code == 200 and _is_valid_bms_json(res.text):
                    log.debug(f"HTTP 200 (via curl_cffi:{imp}) — {len(res.text):,} bytes")
                    return json.loads(res.text)
            except Exception as attempt_exc:
                log.debug(f"curl_cffi:{imp} attempt failed ({attempt_exc}), trying next...")
    except ImportError:
        log.debug("curl_cffi not available, falling back to system curl...")

    # 2. Try system curl subprocess
    remaining = overall_deadline - (time.time() - start_time)
    if remaining > 1.0:
        import subprocess
        try:
            cmd = [
                "curl.exe" if subprocess.os.name == "nt" else "curl",
                "-s", "-L",
                url
            ]
            for k, v in api_headers.items():
                cmd.extend(["-H", f"{k}: {v}"])
            curl_timeout = max(1, int(min(8.0, remaining)))
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=curl_timeout)
            if proc.stdout and _is_valid_bms_json(proc.stdout):
                log.debug(f"HTTP 200 (via system curl) — {len(proc.stdout):,} bytes")
                return json.loads(proc.stdout)
        except Exception as exc:
            log.debug(f"System curl failed ({exc}), trying httpx...")

    # 3. Fallback to httpx
    remaining = overall_deadline - (time.time() - start_time)
    if remaining > 1.0:
        import httpx
        try:
            httpx_timeout = min(6.0, remaining)
            with httpx.Client(headers=api_headers, follow_redirects=True, timeout=httpx_timeout) as client:
                res = client.get(url)
                if res.status_code == 200 and _is_valid_bms_json(res.text):
                    log.debug(f"HTTP 200 (via httpx) — {len(res.text):,} bytes")
                    return json.loads(res.text)
                raise RuntimeError(f"HTTP {res.status_code} returned by BookMyShow API")
        except Exception as exc:
            raise RuntimeError(f"BookMyShow security check active. ({exc})") from exc

    raise RuntimeError("BookMyShow fetch request exceeded overall execution deadline.")


def _build_bms_headers(region_code: str, region_slug: str, lat: str, lon: str, geohash: str, is_movie: bool = False) -> dict:
    """
    Build request headers for BookMyShow API calls using region and location context.
    
    Parameters:
    	region_code (str): BookMyShow region code.
    	region_slug (str): URL-friendly region identifier used in the request context.
    	lat (str): Latitude for the request location.
    	lon (str): Longitude for the request location.
    	geohash (str): Geohash for the request location.
    	is_movie (bool): Whether to use the desktop movie platform code.
    
    Returns:
    	dict: Headers configured for a BookMyShow API request.
    """
    platform_code = "DESKTOP-WEB" if is_movie else "WEB"
    clean_slug = urllib.parse.quote(_sanitize_header_value(region_slug))
    clean_region = urllib.parse.quote(_sanitize_header_value(region_code))
    clean_geohash = _sanitize_header_value(geohash)
    clean_lat = _sanitize_header_value(lat)
    clean_lon = _sanitize_header_value(lon)
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "x-app-code": "WEB",
        "x-platform-code": platform_code,
        "x-platform": "WEB",
        "x-region-slug": clean_slug,
        "x-region-code": clean_region,
        "x-geohash": clean_geohash,
        "x-latitude": clean_lat,
        "x-longitude": clean_lon,
        "x-location-selection": "manual",
        "true-client-ip": "117.206.171.62",
        "x-bms-id": "1.753478738.1785071518301",
        "x-advertiser-id": "1532623275951006886",
        "x-segments": "",
        "Referer": f"https://in.bookmyshow.com/explore/home/{clean_slug}",
        "sentry-trace": "9a102aa3dbb3407aba2dc6dc64202968-96dd7e6f9b88f466-0",
        "baggage": "sentry-environment=production,sentry-release=release_543,sentry-public_key=4d17a59c2597410e714ab31d421148d9",
    }


@router.get("/search/theatres")
async def search_theatres(
    q: str = Query("", description="Search term for theatre"),
    region: str = Query("CHEN", description="Region Code"),
    regionSlug: str = Query("chennai", description="Region Slug"),
    lat: str = Query("13.056", description="Latitude"),
    lon: str = Query("80.206", description="Longitude"),
    geohash: str = Query("tf3", description="GeoHash"),
    city: str = Query("", description="City / Region Name"),
    claims: dict = Depends(get_authorized_user)
):
    """
    Searches BookMyShow for theatres matching the supplied query and filtered by the selected city/region.
    
    Parameters:
    	q (str): Theatre search term.
    	region (str): BookMyShow region code.
    	regionSlug (str): BookMyShow region slug.
    	lat (str): Search latitude.
    	lon (str): Search longitude.
    	geohash (str): Search location geohash.
    	city (str): City/region display name.
    """
    v_region = _validate_param(region, REGION_CODE_PATTERN, "region")
    v_region_slug = _validate_param(regionSlug, REGION_SLUG_PATTERN, "regionSlug")
    v_lat = _validate_param(lat, LAT_LON_PATTERN, "lat")
    v_lon = _validate_param(lon, LAT_LON_PATTERN, "lon")
    v_geohash = _validate_param(geohash, GEOHASH_PATTERN, "geohash")

    if not q.strip():
        return JSONResponse(content={"results": [], "total": 0})

    encoded_q = urllib.parse.quote(q.strip())
    target_url = f"https://in.bookmyshow.com/api/v1/search/dynamic?q={encoded_q}&instant=true&firstLoad=false"
    headers = _build_bms_headers(v_region, v_region_slug, v_lat, v_lon, v_geohash, is_movie=False)

    try:
        loop = asyncio.get_running_loop()
        raw_data = await loop.run_in_executor(_bms_executor, _fetch_bms_api, target_url, headers, logger)
    except Exception as e:
        logger.error(f"Error fetching BMS theatre search: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch theatre data from BookMyShow.") from e

    results = []

    # Process search-vi-v2-results widget
    try:
        data_obj = raw_data.get("data", {})
        widgets = data_obj.get("widgets", {})
        
        # Target explicitly search-vi-v2-results
        search_widget = widgets.get("search-vi-v2-results")
        if not search_widget:
            for w_key, w_val in widgets.items():
                if w_key == "search-vi-v2-results" or (isinstance(w_val, dict) and w_val.get("id") == "searchResultsV2"):
                    search_widget = w_val
                    break

        card_sources = [search_widget] if search_widget else list(widgets.values())

        for widget_val in card_sources:
            if not isinstance(widget_val, dict):
                continue
            cards_obj = widget_val.get("data", {}).get("cards", {})
            cards_list = cards_obj.get("data", []) if isinstance(cards_obj, dict) else cards_obj
            if not isinstance(cards_list, list):
                continue
            
            for card in cards_list:
                if not isinstance(card, dict):
                    continue
                c_data = card.get("data", {})
                title = c_data.get("result-title") or c_data.get("title") or ""
                if not title:
                    continue

                cta = c_data.get("cta", {})
                bms_url = cta.get("url", "")
                cta_analytics = cta.get("analytics", {})
                card_analytics = c_data.get("analytics", {})
                entity_code = cta_analytics.get("entity_code") or card_analytics.get("entity_code") or ""

                product_type = str(
                    card_analytics.get("product") or 
                    card_analytics.get("type") or 
                    cta_analytics.get("product") or 
                    cta_analytics.get("type") or 
                    ""
                ).lower()

                context = str(c_data.get("result-context") or "")
                context_lower = context.lower()
                bms_url_lower = str(bms_url).lower()

                # Filter strictly for venues / cinemas
                is_venue = (
                    product_type == "venues" or 
                    "venue" in product_type or 
                    "venue" in context_lower or 
                    "cinema" in context_lower or
                    "/cinemas/" in bms_url_lower or 
                    "/venues/" in bms_url_lower
                )
                if not is_venue:
                    continue

                location = c_data.get("result-location") or c_data.get("subtitle") or ""
                thumbnail = c_data.get("result-icon") or c_data.get("result-poster-url") or ""

                # Filter out theatres from other cities
                if not _is_venue_in_city(title, location, bms_url, v_region, v_region_slug, city):
                    continue

                parsed_city, _, _ = _parse_venue_location(location)

                results.append({
                    "name": title,
                    "thumbnail": thumbnail,
                    "location": location,
                    "city": parsed_city or city or v_region_slug.title(),
                    "category": context,
                    "entity_code": entity_code,
                    "bms_url": bms_url
                })

    except Exception as ex:
        logger.warning(f"Error parsing BMS theatre search structure: {ex}")

    return JSONResponse(content={"results": results, "total": len(results)})


def _extract_event_code(cta_url: str, analytics: dict = None) -> str:
    """Extracts BMS event code (e.g. ET00447840) from analytics or cta_url."""
    if analytics and isinstance(analytics, dict) and analytics.get("event_code"):
        return str(analytics.get("event_code")).upper()
    if cta_url:
        match = re.search(r"(ET\d{8})", cta_url, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return ""


@router.get("/movies")
async def get_movies(
    region: str = Query("CHEN", description="Region Code"),
    regionSlug: str = Query("chennai", description="Region Slug"),
    lat: str = Query("13.056", description="Latitude"),
    lon: str = Query("80.206", description="Longitude"),
    geohash: str = Query("tf3", description="GeoHash"),
    claims: dict = Depends(get_authorized_user)
):
    """
    Fetches currently listed movies for a region from BookMyShow.
    
    Parameters:
    	region (str): BookMyShow region code.
    	regionSlug (str): BookMyShow region slug.
    	lat (str): Latitude used for the regional request.
    	lon (str): Longitude used for the regional request.
    	geohash (str): Geohash used for the regional request.
    
    Returns:
    	JSONResponse: A response containing normalized movie listings.
    """
    v_region = _validate_param(region, REGION_CODE_PATTERN, "region")
    v_region_slug = _validate_param(regionSlug, REGION_SLUG_PATTERN, "regionSlug")
    v_lat = _validate_param(lat, LAT_LON_PATTERN, "lat")
    v_lon = _validate_param(lon, LAT_LON_PATTERN, "lon")
    v_geohash = _validate_param(geohash, GEOHASH_PATTERN, "geohash")

    encoded_slug = urllib.parse.quote(v_region_slug)
    target_url = f"https://in.bookmyshow.com/api/explore/v1/discover/movies-{encoded_slug}"
    headers = _build_bms_headers(v_region, v_region_slug, v_lat, v_lon, v_geohash, is_movie=True)

    try:
        loop = asyncio.get_running_loop()
        raw_data = await loop.run_in_executor(_bms_executor, _fetch_bms_api, target_url, headers, logger)
    except Exception as e:
        logger.error(f"Error fetching BMS movies listing: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch movies data from BookMyShow.") from e

    movies = []
    seen_titles = set()

    try:
        listings = raw_data.get("listings", [])
        for listing in listings:
            if not isinstance(listing, dict):
                continue
            listing_id = str(listing.get("id", "")).lower()
            if "coming_soon" in listing_id or "upcoming" in listing_id:
                continue

            cards = listing.get("cards", [])
            for card in cards:
                if not isinstance(card, dict):
                    continue
                cta_url = card.get("ctaUrl", "")
                if "upcoming-movies" in cta_url or "coming-soon" in cta_url or "coming_soon" in cta_url:
                    continue

                img_obj = card.get("image", {})
                alt_text = img_obj.get("altText", "")
                if "coming soon" in alt_text.lower() or "upcoming" in alt_text.lower():
                    continue

                # Extract title
                texts = card.get("text", [])
                title = ""
                rating = ""
                languages = ""
                
                if len(texts) > 0:
                    comps = texts[0].get("components", [])
                    if comps:
                        title = comps[0].get("text", "")
                if len(texts) > 1:
                    comps = texts[1].get("components", [])
                    if comps:
                        rating = comps[0].get("text", "")
                if len(texts) > 2:
                    comps = texts[2].get("components", [])
                    if comps:
                        languages = comps[0].get("text", "")

                poster = img_obj.get("url", "")
                if not title and alt_text:
                    title = alt_text

                analytics = card.get("analytics", {})
                if not title:
                    title = analytics.get("title", "")

                if "coming soon" in title.lower() or "upcoming" in title.lower():
                    continue

                if not cta_url or ("/movies/" not in cta_url and "/buytickets/" not in cta_url):
                    continue

                genre_str = analytics.get("genre", "")
                genres = [g.strip() for g in genre_str.split("|") if g.strip()]
                event_code = _extract_event_code(cta_url, analytics)

                if title and title.lower() not in seen_titles:
                    seen_titles.add(title.lower())
                    movies.append({
                        "title": title,
                        "poster": poster,
                        "rating": rating,
                        "genres": genres,
                        "languages": languages,
                        "ctaUrl": cta_url,
                        "eventCode": event_code
                    })

    except Exception as ex:
        logger.warning(f"Error parsing BMS movies structure: {ex}")

    return JSONResponse(content={"movies": movies})


@router.get("/movie-formats")
async def get_movie_formats(
    eventCode: str = Query(..., description="Event Code of the movie (e.g. ET00447840)"),
    dateCode: str = Query("", description="Date in YYYYMMDD format"),
    region: str = Query("CHEN", description="Region Code"),
    regionSlug: str = Query("chennai", description="Region Slug"),
    lat: str = Query("13.056", description="Latitude"),
    lon: str = Query("80.206", description="Longitude"),
    geohash: str = Query("tf3", description="GeoHash"),
    claims: dict = Depends(get_authorized_user)
):
    """
    Fetch available movie formats, languages, metadata, and show dates for an event code.
    
    Parameters:
    	eventCode (str): BookMyShow event code identifying the movie.
    	dateCode (str): Show date in YYYYMMDD format; defaults to the current date.
    	region (str): BookMyShow region code.
    	regionSlug (str): BookMyShow region slug.
    	lat (str): Latitude for the selected region.
    	lon (str): Longitude for the selected region.
    	geohash (str): Geohash for the selected location.
    
    Returns:
    	JSONResponse: Movie event code, metadata, format groups, and available show dates.
    
    Raises:
    	HTTPException: If eventCode is empty after trimming.
    """
    v_code = _validate_param(eventCode, EVENT_CODE_PATTERN, "eventCode").upper()
    v_region = _validate_param(region, REGION_CODE_PATTERN, "region")
    v_region_slug = _validate_param(regionSlug, REGION_SLUG_PATTERN, "regionSlug")
    v_lat = _validate_param(lat, LAT_LON_PATTERN, "lat")
    v_lon = _validate_param(lon, LAT_LON_PATTERN, "lon")
    v_geohash = _validate_param(geohash, GEOHASH_PATTERN, "geohash")

    date_str = dateCode.strip() if dateCode.strip() and dateCode.strip().isdigit() else time.strftime("%Y%m%d")

    headers = _build_bms_headers(v_region, v_region_slug, v_lat, v_lon, v_geohash, is_movie=True)

    encoded_code = urllib.parse.quote(v_code)
    encoded_region = urllib.parse.quote(v_region)

    # 1. Try Primary Showtimes API
    primary_url = (
        f"https://in.bookmyshow.com/api/movies-data/v5/showtimes-by-event/primary-dynamic"
        f"?etCodes={encoded_code}&dateCode={date_str}&isDesktop=true&regionCode={encoded_region}"
        f"&xLocationShared=false&memberId=&lsId=&subCode=&appCode=WEB"
        f"&language=english&refEventCode={encoded_code}"
    )

    groups = []
    show_dates = []
    movie_info = {}
    theatres = []

    try:
        loop = asyncio.get_running_loop()
        raw_data = await loop.run_in_executor(_bms_executor, _fetch_bms_api, primary_url, headers, logger)
        data_obj = raw_data.get("data", {})

        # Venues / Theatres screening the movie in this city
        for widget in data_obj.get("showtimeWidgets", []):
            if isinstance(widget, dict) and widget.get("type") == "groupList":
                for group in widget.get("data", []):
                    if not isinstance(group, dict):
                        continue
                    for v in group.get("data", []):
                        if not isinstance(v, dict):
                            continue
                        add_data = v.get("additionalData", {})
                        v_name = add_data.get("venueName") or ""
                        v_code = add_data.get("venueCode") or ""
                        if v_name and not any(x["name"].lower() == v_name.lower() for x in theatres):
                            theatres.append({
                                "name": v_name,
                                "code": v_code
                            })
        
        # Header info
        hdr = data_obj.get("header", {})
        if hdr:
            subtitle = hdr.get("subtitle", {}).get("text", "")
            title = hdr.get("title", {}).get("text", "")
            censor = hdr.get("additionalData", {}).get("eventCensor", "")
            genre = hdr.get("additionalData", {}).get("genre", "")
            movie_info = {
                "title": title,
                "runtime": subtitle,
                "censor": censor,
                "genre": genre
            }

        # Available show dates
        sticky = data_obj.get("topStickyWidgets", [])
        if sticky and isinstance(sticky, list):
            date_widget = sticky[0]
            if isinstance(date_widget, dict) and date_widget.get("type") == "horizontal-block-list":
                for date_item in date_widget.get("data", []):
                    if not isinstance(date_item, dict):
                        continue
                    d_id = date_item.get("id", "")
                    style_id = date_item.get("styleId", "")
                    d_texts = [t.get("text", "") for t in date_item.get("data", []) if isinstance(t, dict)]
                    label = " ".join(d_texts)
                    is_disabled = "disabled" in style_id.lower()
                    if d_id and len(d_id) == 8:
                        show_dates.append({
                            "dateCode": d_id,
                            "label": label,
                            "isDisabled": is_disabled
                        })

        # Format selector bottomSheetData
        bottom_sheet = data_obj.get("bottomSheetData", {}).get("format-selector", {})
        widgets = bottom_sheet.get("widgets", [])
        
        for widget in widgets:
            if not isinstance(widget, dict) or widget.get("type") != "chip-list":
                continue
            lang = widget.get("text", "")
            chip_data = widget.get("data", [])
            formats = []
            for chip in chip_data:
                if not isinstance(chip, dict):
                    continue
                c_title = chip.get("title", "")
                if not c_title or c_title.lower() == "select all":
                    continue
                cta = chip.get("cta", {})
                add_data = cta.get("additionalData", {})
                analytics = cta.get("analytics", {})
                
                f_event_code = add_data.get("eventCode") or analytics.get("event_code") or v_code
                if f_event_code == "*":
                    continue
                f_event_url = add_data.get("eventUrl") or ""
                ref_code = add_data.get("refEventCode") or v_code
                
                formats.append({
                    "label": c_title,
                    "eventCode": f_event_code,
                    "eventUrl": f_event_url,
                    "refEventCode": ref_code,
                    "language": lang
                })
            if formats:
                groups.append({
                    "language": lang,
                    "formats": formats
                })

    except Exception as e:
        logger.warning(f"Primary format search failed for {v_code}: {e}")

    # 2. Fallback to Synopsis Init API if primary returns no format options
    if not groups:
        logger.info(f"Falling back to synopsis init API for format selection of {v_code}")
        synopsis_url = (
            f"https://in.bookmyshow.com/api/movies/v1/synopsis/init/dynamic"
            f"?eventcode={encoded_code}&channel=web&isdesktop=true&isRnROnly=false&regionCode={encoded_region}"
        )
        try:
            loop = asyncio.get_running_loop()
            raw_syn = await loop.run_in_executor(_bms_executor, _fetch_bms_api, synopsis_url, headers, logger)
            data_syn = raw_syn.get("data", {}) if "data" in raw_syn else raw_syn
            banner = data_syn.get("bannerWidget", {})
            if banner:
                movie_info = {
                    "title": banner.get("heading", ""),
                    "runtime": banner.get("duration", ""),
                    "censor": banner.get("censor", ""),
                    "releaseDate": banner.get("releaseDate", "")
                }
                page_cta = data_syn.get("pageCta", []) or banner.get("pageCta", [])
                if page_cta and isinstance(page_cta, list):
                    meta_options = page_cta[0].get("meta", {}).get("options", [])
                    for opt in meta_options:
                        if not isinstance(opt, dict):
                            continue
                        lang = opt.get("language", "")
                        f_list = opt.get("formats", [])
                        formats = []
                        for fmt in f_list:
                            if not isinstance(fmt, dict):
                                continue
                            dim = fmt.get("dimension", "")
                            if not dim or dim.lower() == "select all":
                                continue
                            f_code = fmt.get("eventCode")
                            if not f_code or f_code == "*":
                                continue
                            ref_code = fmt.get("refEventCode") or f_code
                            formats.append({
                                "label": dim,
                                "eventCode": f_code,
                                "eventUrl": "",
                                "refEventCode": ref_code,
                                "language": lang
                            })
                        if formats:
                            groups.append({
                                "language": lang,
                                "formats": formats
                            })
        except Exception as syn_err:
            logger.warning(f"Synopsis format fallback failed for {v_code}: {syn_err}")

    return JSONResponse(content={
        "eventCode": v_code,
        "movieInfo": movie_info,
        "groups": groups,
        "showDates": show_dates,
        "theatres": theatres
    })
