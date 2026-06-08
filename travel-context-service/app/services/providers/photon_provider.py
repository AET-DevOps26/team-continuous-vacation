from __future__ import annotations

import logging

import httpx

from app.models.schemas import Coordinates, GeocodedLocation
from app.services.providers.nominatim_provider import GeocodingError

logger = logging.getLogger(__name__)


class PhotonProvider:
    def __init__(self, base_url: str, user_agent: str):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent

    async def geocode(self, destination: str) -> GeocodedLocation:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/api/",
                params={
                    "q": destination,
                    "limit": 1,
                },
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                },
            )
            logger.info(
                "Photon response status=%s response_bytes=%s",
                response.status_code,
                len(response.content),
            )
            if response.status_code >= 400:
                logger.warning(
                    "Photon error status=%s body=%r",
                    response.status_code,
                    response.text[:1000],
                )
            response.raise_for_status()
            payload = response.json()

        features = payload.get("features") or []
        if not features:
            raise GeocodingError(f"Could not geocode destination with Photon: {destination}")

        first_feature = features[0]
        coordinates = first_feature.get("geometry", {}).get("coordinates")
        if not coordinates or len(coordinates) < 2:
            raise GeocodingError(f"Photon response did not include coordinates for: {destination}")

        lon, lat = coordinates[:2]
        properties = first_feature.get("properties") or {}
        country_code = (properties.get("countrycode") or "").lower() or None
        name = properties.get("name") or destination
        logger.info(
            "Photon selected destination=%s name=%r country_code=%r lat=%s lon=%s",
            destination,
            name,
            country_code,
            lat,
            lon,
        )
        return GeocodedLocation(
            name=name,
            displayName=name,
            countryCode=country_code,
            coordinates=Coordinates(lat=float(lat), lon=float(lon)),
        )
