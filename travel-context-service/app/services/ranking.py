from __future__ import annotations

import math
import re
from typing import Optional

from app.models.schemas import PlaceCandidate


LOW_INFORMATION_TAGS = {
    "boundary",
    "admin_level",
    "source",
    "type",
}

TOURIST_CATEGORY_WEIGHTS = {
    ("tourism", "attraction"): 50,
    ("tourism", "museum"): 48,
    ("tourism", "zoo"): 52,
    ("tourism", "gallery"): 36,
    ("tourism", "viewpoint"): 42,
    ("tourism", "artwork"): 25,
    ("historic", "castle"): 52,
    ("historic", "palace"): 52,
    ("historic", "monument"): 44,
    ("historic", "memorial"): 30,
    ("historic", "city_gate"): 38,
    ("leisure", "park"): 45,
    ("leisure", "garden"): 38,
    ("leisure", "stadium"): 28,
    ("place", "square"): 50,
    ("amenity", "marketplace"): 38,
    ("amenity", "theatre"): 34,
    ("amenity", "arts_centre"): 32,
    ("amenity", "place_of_worship"): 28,
    ("natural", "water"): 24,
    ("waterway", "river"): 24,
    ("waterway", "stream"): 20,
    ("building", "church"): 24,
    ("building", "cathedral"): 30,
}

LANDMARK_NAME_WORDS = {
    "altstadt",
    "arena",
    "castle",
    "cathedral",
    "church",
    "garten",
    "garden",
    "gate",
    "historic",
    "museum",
    "olympia",
    "palace",
    "park",
    "platz",
    "river",
    "schloss",
    "square",
    "stadium",
    "tierpark",
    "view",
    "zoo",
}


class PlaceRanker:
    """Ranks raw OSM place candidates by expected tourist usefulness."""

    def rank(self, places: list[PlaceCandidate], limit: int) -> list[PlaceCandidate]:
        scored = []
        for place in places:
            if not place.name.strip():
                continue
            place.score = round(self.score(place), 3)
            if place.score > 0:
                scored.append(place)

        deduped = self._deduplicate(scored)
        return sorted(deduped, key=lambda candidate: candidate.score, reverse=True)[:limit]

    def score(self, place: PlaceCandidate) -> float:
        tags = {key: str(value) for key, value in place.osmTags.items() if value is not None}
        score = 0.0

        score += self._category_score(tags)
        score += self._metadata_score(tags, place)
        score += self._name_score(place.name)

        if self._is_low_information(tags):
            score -= 35
        if len(tags) <= 2:
            score -= 8
        if place.name.lower() in {"yes", "unknown"}:
            score -= 50

        return max(score, 0.0)

    def category(self, tags: dict[str, str]) -> Optional[str]:
        for key, value in [
            ("tourism", None),
            ("historic", None),
            ("leisure", None),
            ("place", None),
            ("amenity", None),
            ("natural", None),
            ("waterway", None),
            ("building", None),
        ]:
            if key in tags:
                return f"{key}:{tags[key]}"
            if value is not None and tags.get(key) == value:
                return f"{key}:{value}"
        return None

    def _category_score(self, tags: dict[str, str]) -> float:
        score = 0.0
        for (key, value), weight in TOURIST_CATEGORY_WEIGHTS.items():
            if tags.get(key) == value:
                score += weight
        if tags.get("tourism"):
            score += 12
        if tags.get("historic"):
            score += 10
        return score

    def _metadata_score(self, tags: dict[str, str], place: PlaceCandidate) -> float:
        score = 0.0
        if tags.get("wikidata"):
            score += 28
        if tags.get("wikipedia") or place.wikipedia:
            score += 22
        if tags.get("website") or place.website:
            score += 10
        if tags.get("opening_hours") or place.openingHours:
            score += 8
        if tags.get("image"):
            score += 6
        return score

    def _name_score(self, name: str) -> float:
        normalized = normalize_name(name)
        words = set(normalized.split())
        score = min(len(name), 40) * 0.25
        if words & LANDMARK_NAME_WORDS:
            score += 16
        if len(words) >= 2:
            score += 4
        return score

    def _is_low_information(self, tags: dict[str, str]) -> bool:
        keys = set(tags.keys())
        meaningful_keys = keys - LOW_INFORMATION_TAGS - {"name"}
        if not meaningful_keys:
            return True
        if keys <= {"name", "boundary", "admin_level", "type"}:
            return True
        return False

    def _deduplicate(self, places: list[PlaceCandidate]) -> list[PlaceCandidate]:
        selected: dict[str, PlaceCandidate] = {}
        for place in sorted(places, key=lambda candidate: candidate.score, reverse=True):
            key = self._dedupe_key(place)
            existing = selected.get(key)
            if existing is None or place.score > existing.score:
                selected[key] = place
        return list(selected.values())

    def _dedupe_key(self, place: PlaceCandidate) -> str:
        rounded_lat = math.floor(place.latitude * 500) / 500
        rounded_lon = math.floor(place.longitude * 500) / 500
        return f"{normalize_name(place.name)}:{rounded_lat}:{rounded_lon}"


def normalize_name(name: str) -> str:
    normalized = name.lower()
    normalized = normalized.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()
