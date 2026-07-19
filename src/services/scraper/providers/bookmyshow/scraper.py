# src/services/scraper/providers/bookmyshow/scraper.py

import logging
import re
from urllib.parse import urlparse
from typing import List, Tuple, Optional, Dict, Any
from playwright.async_api import async_playwright
from src.services.scraper.providers.base import BookingChecker
from src.config import settings

logger = logging.getLogger(__name__)

def extract_movie_href(url: str) -> str:
    """
    Extracts the movie details href path from the buy tickets URL.
    E.g. https://in.bookmyshow.com/movies/chennai/the-odyssey/buytickets/ET00452034/20260719
    -> /movies/chennai/the-odyssey/ET00452034
    """
    try:
        parsed = urlparse(url)
        path = parsed.path
        # Match pattern: /movies/{city}/{slug}/buytickets/{code}
        match = re.search(r'(/movies/[^/]+/[^/]+)/buytickets/([^/]+)', path)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    except Exception:
        pass
    return ""

class BookMyShowBookingChecker(BookingChecker):
    """
    Concrete scraper implementing the BookingChecker interface for BookMyShow using Playwright.
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
                "help": "Copy the exact URL of the movie booking page containing the date selectors."
            },
            "date_str": {
                "type": "date",
                "label": "Target Date 📅",
                "help": "Select the date you want to monitor."
            },
            "theatres": {
                "type": "text_area",
                "label": "Target Theatre Name(s) 🏢",
                "placeholder": "PVR: ECX Chanakyapuri\nINOX: Insignia Epicuria",
                "help": "Enter one theatre name per line. Substring match is supported, but it is strictly case-sensitive!"
            }
        }

    async def check_booking(
        self, 
        params: Dict[str, Any], 
        headless: bool = True
    ) -> Tuple[bool, str, Optional[str], List[str], List[str]]:
        url = params.get("url", "")
        date_str = params.get("date_str", "")
        theatres = params.get("theatres", [])

        logger.info(f"Starting BookMyShow booking check for URL: {url}, Date: {date_str}, Theatres: {theatres}, Headless: {headless}")
        
        async with async_playwright() as p:
            # Launch Chrome using system-installed application
            try:
                browser = await p.chromium.launch(
                    headless=headless,
                    channel=settings.playwright_channel
                )
            except Exception as e:
                logger.error(f"Failed to launch Chrome browser: {str(e)}")
                return False, "A temporary error occurred while checking ticket availability. We will try again shortly.", None, [], theatres

            # Use generic user-agent to prevent bot detection
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.set_default_timeout(settings.default_playwright_timeout)

            # Establish fallback movie name based on slug in case DOM parsing fails
            fallback_movie_name = "Movie"
            try:
                parsed_url = urlparse(url)
                match_slug = re.search(r'/movies/[^/]+/([^/]+)', parsed_url.path)
                if match_slug:
                    fallback_movie_name = match_slug.group(1).replace("-", " ").title()
            except Exception:
                pass

            movie_name = fallback_movie_name

            try:
                # Format URL to point directly to the target date from the form
                # (Only if it's not a local file:// URL used for testing)
                target_url = url
                if not url.startswith("file://"):
                    if re.search(r'/\d{8}$', url):
                        target_url = re.sub(r'/\d{8}$', f'/{date_str}', url)
                    else:
                        target_url = f"{url.rstrip('/')}/{date_str}"

                # 1. Open the target date URL
                logger.info(f"Opening target URL: {target_url} (original: {url})")
                await page.goto(target_url, wait_until="domcontentloaded")
                
                # Load page and log URL
                current_url = page.url
                logger.info(f"Loaded page URL: {current_url}")

                # Attempt to extract movie name using the User's requested XPath format
                try:
                    href = extract_movie_href(url)
                    if href:
                        movie_xpath = f"//a[@href='{href}']"
                        logger.info(f"Searching for movie name with XPath: {movie_xpath}")
                        movie_locator = page.locator(movie_xpath)
                        count = await movie_locator.count()
                        if count > 0:
                            extracted_name = (await movie_locator.first.inner_text()).strip()
                            if extracted_name:
                                movie_name = extracted_name
                                logger.info(f"Extracted movie name from DOM: {movie_name}")
                        else:
                            # Try matching contains just in case
                            movie_xpath_contains = f"//a[contains(@href, '{href}')]"
                            movie_locator_contains = page.locator(movie_xpath_contains)
                            if await movie_locator_contains.count() > 0:
                                extracted_name = (await movie_locator_contains.first.inner_text()).strip()
                                if extracted_name:
                                    movie_name = extracted_name
                                    logger.info(f"Extracted movie name (contains) from DOM: {movie_name}")
                except Exception as ex:
                    logger.warning(f"Could not extract movie name from page DOM: {ex}. Using fallback: {movie_name}")

                # 2. Check if requested date is locatable
                date_xpath = f'//*[@id="{date_str}"]'
                logger.info(f"Locating date element with XPath: {date_xpath}")
                date_locator = page.locator(date_xpath)
                
                count = await date_locator.count()
                if count == 0:
                    logger.warning(f"Date element '{date_str}' not found on page.")
                    return False, f"Booking has not opened for {date_str} yet.", movie_name, [], theatres
                
                date_element = date_locator.first
                is_visible = await date_element.is_visible()
                if not is_visible:
                    logger.warning(f"Date element '{date_str}' is present in DOM but not visible.")
                    return False, f"Booking has not opened for {date_str} yet.", movie_name, [], theatres

                # 3. Check if the date is clickable (i.e. booking is open)
                # Since date buttons can be <div> tags, standard Playwright is_enabled() check is not enough.
                # We check WAI-ARIA properties, custom disabled attributes, and class names (ancestors included).
                is_enabled = await date_element.is_enabled()
                
                # Check WAI-ARIA and custom attributes
                aria_disabled = await date_element.get_attribute("aria-disabled") or ""
                custom_disabled = await date_element.get_attribute("disabled") or ""
                is_disabled_attr = (
                    aria_disabled.lower() == "true" or 
                    custom_disabled.lower() in ["true", "disabled"]
                )
                
                # Retrieve classes of date element and its parent elements (grandparent included)
                classes_to_check = []
                try:
                    classes_to_check.append(await date_element.get_attribute("class") or "")
                    classes_to_check.append(await date_element.evaluate("el => el.parentElement ? el.parentElement.className : ''"))
                    classes_to_check.append(await date_element.evaluate("el => el.parentElement && el.parentElement.parentElement ? el.parentElement.parentElement.className : ''"))
                except Exception:
                    pass
                
                classes_str = " ".join(classes_to_check).lower()
                is_disabled_by_class = any(
                    term in classes_str
                    for term in ["disabled", "inactive", "blocked", "unclickable"]
                )

                if not is_enabled or is_disabled_by_class or is_disabled_attr:
                    logger.warning(
                        f"Date '{date_str}' is found but disabled. "
                        f"enabled={is_enabled}, classes='{classes_str}', aria-disabled='{aria_disabled}', custom-disabled='{custom_disabled}'"
                    )
                    return False, f"Booking has not opened for {date_str} yet.", movie_name, [], theatres

                # 4. Click the date element to load showtimes/theatres
                logger.info(f"Date '{date_str}' is clickable. Clicking to load theatres...")
                try:
                    await date_element.click(timeout=5000)
                    # Let DOM update/load theatres
                    await page.wait_for_timeout(2000)
                except Exception as click_err:
                    logger.error(f"Failed to click date element: {str(click_err)}")
                    return False, f"Booking has not opened for {date_str} yet.", movie_name, [], theatres

                # 4.5 Post-Click Verification: Ensure we have navigated to the correct date
                current_url = page.url
                logger.info(f"Current page URL after click: {current_url}")
                
                # Check active/selected classes on date element and ancestors
                post_classes = []
                try:
                    post_classes.append(await date_element.get_attribute("class") or "")
                    post_classes.append(await date_element.evaluate("el => el.parentElement ? el.parentElement.className : ''"))
                    post_classes.append(await date_element.evaluate("el => el.parentElement && el.parentElement.parentElement ? el.parentElement.parentElement.className : ''"))
                except Exception:
                    pass
                
                post_classes_str = " ".join(post_classes).lower()
                is_active_class = any(
                    term in post_classes_str 
                    for term in ["active", "selected", "current", "_active", "-active", "show", "select"]
                )
                
                # Check if the target date is active/selected in the DOM (regardless of URL)
                if not is_active_class:
                    logger.warning(f"Target date '{date_str}' is not active in the DOM. URL: {current_url}, Classes: {post_classes_str}")
                    return False, f"Booking has not opened for {date_str} yet.", movie_name, [], theatres

                # 5. Check if the specified theatre(s) are available
                available_theatres = []
                missing_theatres = []

                for theatre in theatres:
                    # Escape single quotes in theatre names for XPath safety
                    theatre_escaped = theatre.replace("'", "\\'")
                    theatre_xpath = f"//span[contains(text(), '{theatre_escaped}')]"
                    logger.info(f"Checking for theatre '{theatre}' using XPath: {theatre_xpath}")
                    theatre_locator = page.locator(theatre_xpath)

                    # Look for a visible instance of the theatre span
                    count = await theatre_locator.count()
                    is_visible = False
                    for idx in range(count):
                        is_nth_visible = await theatre_locator.nth(idx).is_visible()
                        if is_nth_visible:
                            is_visible = True
                            break

                    if is_visible:
                        available_theatres.append(theatre)
                    else:
                        missing_theatres.append(theatre)

                if not available_theatres:
                    logger.warning(f"Date '{date_str}' is clickable, but none of the specified theatres were found ({', '.join(theatres)}).")
                    return False, f"Booking is open for {date_str}, but showtimes at your selected theatres are not available yet.", movie_name, [], theatres

                # Success!
                success_details = f"Booking is OPEN for date {date_str}! Found theatres: {', '.join(available_theatres)}."
                if missing_theatres:
                    success_details += f" (Unavailable: {', '.join(missing_theatres)})"
                
                logger.info(success_details)
                return True, success_details, movie_name, available_theatres, missing_theatres

            except Exception as e:
                logger.exception(f"Scraper error while reading {url}")
                return False, "A temporary error occurred while checking ticket availability. We will try again shortly.", movie_name, [], theatres
            finally:
                await browser.close()
