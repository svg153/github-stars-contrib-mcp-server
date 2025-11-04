from __future__ import annotations

import time

import httpx
import structlog

from ..config.settings import settings

logger = structlog.get_logger(__name__)


_cache: dict[str, tuple[float, tuple[bool, str | None]]] = {}


async def check_url_head(
    url: str, timeout_s: int | None = None
) -> tuple[bool, str | None]:
    """Perform a lightweight HEAD request to validate URL accessibility.

    Returns (ok, reason). On success, reason is None. Results are cached for TTL.
    """
    ttl = max(0, int(settings.url_validation_ttl_s))
    now = time.time()
    cached = _cache.get(url)
    if cached and (now - cached[0]) < ttl:
        return cached[1]

    timeout = (
        timeout_s if timeout_s is not None else int(settings.url_validation_timeout_s)
    )
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.head(url)
            if resp.status_code >= 400:
                result = (False, f"status {resp.status_code}")
            else:
                result = (True, None)
    except httpx.TimeoutException:
        result = (False, "timeout")
    except Exception as e:  # Broad but logged; we only need a boolean gate
        logger.debug("url_check.error", url=url, error=str(e))
        result = (False, "error")

    _cache[url] = (now, result)
    return result
