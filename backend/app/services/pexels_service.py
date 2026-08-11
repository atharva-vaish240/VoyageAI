"""Pexels service for retrieving destination photos safely."""

import logging
from typing import Optional
import httpx

from app.core.config import get_settings
from app.schemas.recommendation import RecommendationImage

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"


def search_destination_image(search_term: str) -> Optional[RecommendationImage]:
    """
    Search Pexels for a landscape photo matching the search term.
    
    Returns a RecommendationImage if successful, or None on any error/missing key/no results.
    Never raises an exception to ensure recommendation generation never fails due to image lookup.
    """
    if not search_term or not search_term.strip():
        return None

    settings = get_settings()
    api_key = settings.PEXELS_API_KEY
    if not api_key:
        logger.warning("PEXELS_API_KEY is not configured. Skipping image search.")
        return None

    try:
        headers = {"Authorization": api_key}
        params = {
            "query": search_term.strip(),
            "orientation": "landscape",
            "per_page": 1,
        }

        with httpx.Client(timeout=5.0) as client:
            response = client.get(PEXELS_SEARCH_URL, headers=headers, params=params)

        if response.status_code != 200:
            logger.warning(f"Pexels API responded with status {response.status_code} for term '{search_term}'")
            return None

        data = response.json()
        photos = data.get("photos", [])
        if not photos:
            logger.info(f"No Pexels photo results for term '{search_term}'")
            return None

        photo = photos[0]
        src = photo.get("src", {})
        image_url = src.get("large") or src.get("medium") or src.get("original")

        if not image_url:
            return None

        return RecommendationImage(
            url=image_url,
            photographer=photo.get("photographer", "Pexels Contributor"),
            photographer_url=photo.get("photographer_url", "https://www.pexels.com"),
            pexels_url=photo.get("url", "https://www.pexels.com"),
        )

    except Exception as e:
        logger.warning(f"Failed to fetch Pexels image for term '{search_term}': {e}")
        return None
