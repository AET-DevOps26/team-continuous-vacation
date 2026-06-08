from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.models.schemas import PlaceCandidate
from app.services.ranking import PlaceRanker

logger = logging.getLogger(__name__)


class OverpassProvider:
    def __init__(self, base_url: str, user_agent: str):
        self.base_url = base_url
        self.user_agent = user_agent
        self.ranker = PlaceRanker()

    async def search_places(
        self,
        lat: float,
        lon: float,
        radius_meters: int,
        overpass_timeout_seconds: int = 12,
    ) -> list[PlaceCandidate]:
        query = build_overpass_query(lat, lon, radius_meters, overpass_timeout_seconds)
        logger.info(
            "Starting Overpass place search lat=%s lon=%s radius_meters=%s query_length=%s",
            lat,
            lon,
            radius_meters,
            len(query),
        )
        logger.debug("Overpass query:\n%s", query)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    content=query,
                    headers={
                        "Content-Type": "text/plain; charset=utf-8",
                        "User-Agent": self.user_agent,
                    },
                )
                logger.info(
                    "Overpass response status=%s response_bytes=%s",
                    response.status_code,
                    len(response.content),
                )
                if response.status_code >= 400:
                    logger.warning(
                        "Overpass error status=%s body=%r",
                        response.status_code,
                        response.text[:1000],
                    )
                response.raise_for_status()
            except httpx.HTTPError as error:
                logger.warning("Overpass request failed error=%s", error)
                raise

            payload = response.json()

        elements = payload.get("elements", [])
        logger.info("Overpass returned elements=%s", len(elements))

        places = [place for element in elements if (place := self._to_place(element)) is not None]
        logger.info("Parsed Overpass places=%s", len(places))
        logger.debug(
            "Parsed Overpass place sample=%s",
            [
                {
                    "sourceId": place.sourceId,
                    "name": place.name,
                    "category": place.category,
                    "lat": place.latitude,
                    "lon": place.longitude,
                }
                for place in places[:10]
            ],
        )
        return places

    def _to_place(self, element: dict[str, Any]) -> Optional[PlaceCandidate]:
        tags = element.get("tags") or {}
        name = tags.get("name")
        if not name:
            return None

        coordinates = self._coordinates(element)
        if coordinates is None:
            return None

        source_id = f"{element.get('type')}:{element.get('id')}"
        website = tags.get("website") or tags.get("contact:website") or tags.get("url")
        wikipedia = tags.get("wikipedia")
        opening_hours = tags.get("opening_hours")
        category = self.ranker.category({key: str(value) for key, value in tags.items()})

        return PlaceCandidate(
            source="openstreetmap",
            sourceId=source_id,
            name=name,
            category=category,
            latitude=coordinates[0],
            longitude=coordinates[1],
            address=self._address(tags),
            website=website,
            wikipedia=wikipedia,
            openingHours=opening_hours,
            osmTags=tags,
        )

    def _coordinates(self, element: dict[str, Any]) -> Optional[tuple[float, float]]:
        if "lat" in element and "lon" in element:
            return float(element["lat"]), float(element["lon"])
        center = element.get("center")
        if center and "lat" in center and "lon" in center:
            return float(center["lat"]), float(center["lon"])
        return None

    def _address(self, tags: dict[str, Any]) -> Optional[str]:
        parts = [
            tags.get("addr:street"),
            tags.get("addr:housenumber"),
            tags.get("addr:postcode"),
            tags.get("addr:city"),
        ]
        address = " ".join(str(part) for part in parts if part)
        return address or None


def build_overpass_query(lat: float, lon: float, radius_meters: int, timeout_seconds: int = 12) -> str:
    selectors = [
        'nwr["tourism"~"attraction|museum|gallery|viewpoint|zoo|artwork|theme_park"]',
        'nwr["historic"~"castle|palace|monument|memorial|city_gate|archaeological_site"]',
        'nwr["leisure"~"park|garden|stadium|sports_centre"]',
        'nwr["amenity"~"theatre|arts_centre|marketplace|place_of_worship"]',
        'nwr["place"="square"]',
        'nwr["building"~"church|cathedral"]',
        'nwr["natural"="water"]["name"]',
        'nwr["waterway"~"river|stream"]["name"]',
    ]
    lines = [f"  {selector}(around:{radius_meters},{lat},{lon});" for selector in selectors]
    return "\n".join(
        [
            f"[out:json][timeout:{timeout_seconds}];",
            "(",
            *lines,
            ");",
            "out tags center 120;",
        ]
    )
