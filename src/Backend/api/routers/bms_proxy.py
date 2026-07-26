# src/Backend/api/routers/bms_proxy.py

import json
import logging
import time
import asyncio
import urllib.parse
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from lib.core.auth import get_authorized_user

logger = logging.getLogger("ticketradar.api.bms")

router = APIRouter(prefix="/api/bms", tags=["BookMyShow Proxy"])


def require_provider_search_access(provider_key: str, claims: dict):
    """Verifies that the user has search access for the given provider (or is admin)."""
    if claims.get("role") == "admin":
        return True
    claim_key = f"search_{provider_key.lower()}"
    if claims.get(claim_key) is True:
        return True
    raise HTTPException(
        status_code=403,
        detail=f"User does not have search permission for provider '{provider_key}'."
    )


def _is_valid_bms_json(text: str) -> bool:
    """Validates that response text is not a Cloudflare challenge page and is valid JSON."""
    if not text or len(text) < 10:
        return False
    text_lower = text.lower()
    if "attention required" in text_lower or "just a moment" in text_lower or "cf-browser-verification" in text_lower:
        return False
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def _fetch_bms_api(url: str, api_headers: dict, log) -> dict:
    """
    Synchronous HTTP GET using browser impersonation (curl_cffi / system curl / httpx)
    with Cloudflare challenge validation and automatic retry rotation.
    Runs in a worker thread via asyncio.to_thread.
    """
    log.debug(f"GET BMS API: {url}")

    # 1. Try curl_cffi with fresh impersonation per attempt
    try:
        from curl_cffi import requests as curl_requests
        impersonate_targets = ["chrome120", "chrome110", "chrome", "edge101", "safari15_5"]
        for attempt, imp in enumerate(impersonate_targets):
            if attempt > 0:
                time.sleep(0.3)
            try:
                res = curl_requests.get(
                    url,
                    headers=api_headers,
                    impersonate=imp,
                    timeout=12.0,
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
    import subprocess
    try:
        cmd = [
            "curl.exe" if subprocess.os.name == "nt" else "curl",
            "-s", "-L",
            url
        ]
        for k, v in api_headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=20)
        if proc.stdout and _is_valid_bms_json(proc.stdout):
            log.debug(f"HTTP 200 (via system curl) — {len(proc.stdout):,} bytes")
            return json.loads(proc.stdout)
    except Exception as exc:
        log.debug(f"System curl failed ({exc}), trying httpx...")

    # 3. Fallback to httpx
    import httpx
    try:
        with httpx.Client(headers=api_headers, follow_redirects=True, timeout=20.0) as client:
            res = client.get(url)
            if res.status_code == 200 and _is_valid_bms_json(res.text):
                log.debug(f"HTTP 200 (via httpx) — {len(res.text):,} bytes")
                return json.loads(res.text)
            raise RuntimeError(f"HTTP {res.status_code} returned by BookMyShow API")
    except Exception as exc:
        raise RuntimeError(f"BookMyShow security check active. ({exc})") from exc


def _build_bms_headers(region_code: str, region_slug: str, lat: str, lon: str, geohash: str, is_movie: bool = False) -> dict:
    """Builds standard BMS anti-bot API headers."""
    platform_code = "DESKTOP-WEB" if is_movie else "WEB"
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
        "x-region-slug": region_slug,
        "x-region-code": region_code,
        "x-geohash": geohash,
        "x-latitude": lat,
        "x-longitude": lon,
        "x-location-selection": "manual",
        "true-client-ip": "117.206.171.62",
        "x-bms-id": "1.753478738.1785071518301",
        "x-advertiser-id": "1532623275951006886",
        "x-segments": "",
        "Referer": f"https://in.bookmyshow.com/explore/home/{region_slug}",
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
    claims: dict = Depends(get_authorized_user)
):
    """Searches BookMyShow theatres dynamically."""
    require_provider_search_access("bookmyshow", claims)

    if not q.strip():
        return JSONResponse(content={"results": [], "total": 0})

    encoded_q = urllib.parse.quote(q.strip())
    target_url = f"https://in.bookmyshow.com/api/v1/search/dynamic?q={encoded_q}&instant=true&firstLoad=false"
    headers = _build_bms_headers(region, regionSlug, lat, lon, geohash, is_movie=False)

    try:
        raw_data = await asyncio.to_thread(_fetch_bms_api, target_url, headers, logger)
    except Exception as e:
        logger.error(f"Error fetching BMS theatre search: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch theatre data from BookMyShow: {e}")

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

                results.append({
                    "name": title,
                    "thumbnail": thumbnail,
                    "location": location,
                    "category": context,
                    "entity_code": entity_code,
                    "bms_url": bms_url
                })


    except Exception as ex:
        logger.warning(f"Error parsing BMS theatre search structure: {ex}")

    return JSONResponse(content={"results": results, "total": len(results)})


@router.get("/movies")
async def get_movies(
    region: str = Query("CHEN", description="Region Code"),
    regionSlug: str = Query("chennai", description="Region Slug"),
    lat: str = Query("13.056", description="Latitude"),
    lon: str = Query("80.206", description="Longitude"),
    geohash: str = Query("tf3", description="GeoHash"),
    claims: dict = Depends(get_authorized_user)
):
    """Fetches currently listed movies for a given region from BookMyShow."""
    require_provider_search_access("bookmyshow", claims)

    target_url = f"https://in.bookmyshow.com/api/explore/v1/discover/movies-{regionSlug}"
    headers = _build_bms_headers(region, regionSlug, lat, lon, geohash, is_movie=True)

    try:
        raw_data = await asyncio.to_thread(_fetch_bms_api, target_url, headers, logger)
    except Exception as e:
        logger.error(f"Error fetching BMS movies listing: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch movies data from BookMyShow: {e}")

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

                if title and title.lower() not in seen_titles:
                    seen_titles.add(title.lower())
                    movies.append({
                        "title": title,
                        "poster": poster,
                        "rating": rating,
                        "genres": genres,
                        "languages": languages,
                        "ctaUrl": cta_url
                    })

    except Exception as ex:
        logger.warning(f"Error parsing BMS movies structure: {ex}")

    return JSONResponse(content={"movies": movies})

