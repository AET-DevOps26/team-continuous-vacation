from __future__ import annotations

import logging

import httpx

from app.models.schemas import Coordinates, GeocodedLocation

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Raised when destination geocoding fails."""


class NominatimProvider:
    def __init__(self, base_url: str, user_agent: str):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent

    async def geocode(self, destination: str) -> GeocodedLocation:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/search",
                params={
                    "q": destination,
                    "format": "jsonv2",
                    "limit": 1,
                    "addressdetails": 1,
                },
                headers={"User-Agent": self.user_agent},
            )
            logger.info(
                "Nominatim response status=%s response_bytes=%s",
                response.status_code,
                len(response.content),
            )
            if response.status_code >= 400:
                logger.warning(
                    "Nominatim error status=%s body=%r",
                    response.status_code,
                    response.text[:1000],
                )
            response.raise_for_status()
            results = response.json()

        if not results:
            raise GeocodingError(f"Could not geocode destination: {destination}")

        first_result = results[0]
        logger.info(
            "Nominatim selected destination=%s display_name=%r country_code=%r lat=%s lon=%s",
            destination,
            first_result.get("display_name"),
            (first_result.get("address") or {}).get("country_code"),
            first_result.get("lat"),
            first_result.get("lon"),
        )
        address = first_result.get("address") or {}
        return GeocodedLocation(
            name=first_result.get("name") or destination,
            displayName=first_result.get("display_name"),
            countryCode=address.get("country_code"),
            coordinates=Coordinates(
                lat=float(first_result["lat"]),
                lon=float(first_result["lon"]),
            ),
        )
