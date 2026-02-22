"""Utility functions for HTTP requests using httpx async client."""

from urllib.parse import urljoin

import httpx

# Realistic browser headers to mimic a real user
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

REQUEST_TIMEOUT = 30.0  # seconds


def get_session(
    username: str = "",
    password: str = "",
) -> httpx.AsyncClient:
    """Create a configured async HTTP client.

    Includes realistic browser User-Agent and headers, optional HTTP Basic Auth,
    NO automatic redirect following (so we capture true 3xx status codes),
    and sensible timeouts.

    Args:
        username: HTTP Basic Auth username (empty string to skip auth).
        password: HTTP Basic Auth password.

    Returns:
        A configured httpx.AsyncClient instance.
    """
    auth = None
    if username:
        auth = httpx.BasicAuth(username, password)

    return httpx.AsyncClient(
        auth=auth,
        headers=DEFAULT_HEADERS,
        follow_redirects=False,
        timeout=httpx.Timeout(REQUEST_TIMEOUT),
        limits=httpx.Limits(
            max_connections=30,
            max_keepalive_connections=20,
        ),
    )


async def fetch_page(
    client: httpx.AsyncClient,
    url: str,
) -> tuple[int, str, str]:
    """Fetch a single URL and return its status, redirect target, and body.

    Does NOT follow redirects. For 3xx responses, the redirect target URL
    is extracted from the Location header and resolved to an absolute URL.

    Args:
        client: The httpx async client to use.
        url: The URL to fetch.

    Returns:
        A tuple of (status_code, redirect_url, response_body).
        - redirect_url: Absolute URL from Location header for 3xx, empty string otherwise.
        - On error: (0, "", error_message).
    """
    try:
        response = await client.get(url)
        redirect_url = ""
        if 300 <= response.status_code < 400:
            location = response.headers.get("location", "")
            if location:
                redirect_url = urljoin(url, location)
        return (response.status_code, redirect_url, response.text)
    except httpx.TimeoutException:
        print(f"  [TIMEOUT] {url}")
        return (0, "", "Error: request timed out")
    except httpx.RequestError as exc:
        print(f"  [ERROR] {url} - {exc}")
        return (0, "", f"Error: {exc}")


async def fetch_head(
    client: httpx.AsyncClient,
    url: str,
) -> tuple[int, str]:
    """Send a HEAD request and return its status and redirect target.

    Lightweight alternative to fetch_page — does not download the body.
    Useful for checking image/resource availability without transferring data.

    Args:
        client: The httpx async client to use.
        url: The URL to check.

    Returns:
        A tuple of (status_code, redirect_url).
        - redirect_url: Absolute URL from Location header for 3xx, empty string otherwise.
        - On error: (0, "").
    """
    try:
        response = await client.head(url)
        redirect_url = ""
        if 300 <= response.status_code < 400:
            location = response.headers.get("location", "")
            if location:
                redirect_url = urljoin(url, location)
        return (response.status_code, redirect_url)
    except httpx.TimeoutException:
        print(f"  [TIMEOUT] {url}")
        return (0, "")
    except httpx.RequestError as exc:
        print(f"  [ERROR] {url} - {exc}")
        return (0, "")
