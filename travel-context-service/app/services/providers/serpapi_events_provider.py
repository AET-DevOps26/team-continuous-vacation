from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

from app.models.schemas import EventCandidate, TicketLink

logger = logging.getLogger(__name__)


class SerpApiEventsProvider:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def search_events(
        self,
        location_name: str,
        country_code: str,
        date_filter: str | None = None,
    ) -> list[EventCandidate]:
        if not self.api_key:
            logger.warning("SerpApi event lookup skipped because SERPAPI_API_KEY is not configured")
            return []

        params = {
            "engine": "google_events",
            "q": f"Events in {location_name}",
            "gl": country_code,
            "api_key": self.api_key,
            "no_cache": "false",
            "output": "json",
        }
        if date_filter:
            params["htichips"] = date_filter

        safe_params = {key: value for key, value in params.items() if key != "api_key"}
        logger.info("Starting SerpApi event search params=%s", safe_params)
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.base_url, params=params)
            logger.info(
                "SerpApi response status=%s response_bytes=%s",
                response.status_code,
                len(response.content),
            )
            if response.status_code >= 400:
                logger.warning(
                    "SerpApi error status=%s body=%r",
                    response.status_code,
                    response.text[:1000],
                )
            response.raise_for_status()
            payload = response.json()

        if payload.get("error"):
            raise RuntimeError(f"SerpApi event search failed: {payload['error']}")

        raw_events = payload.get("events_results") or []
        logger.info("SerpApi returned raw_events=%s", len(raw_events))
        events = [_map_event(raw_event) for raw_event in raw_events]
        ranked = _rank_events(events)
        logger.info(
            "Mapped SerpApi events=%s top_events=%s",
            len(ranked),
            [{"title": event.title, "score": event.score} for event in ranked[:10]],
        )
        return ranked


def _map_event(raw_event: dict[str, Any]) -> EventCandidate:
    date = raw_event.get("date") or {}
    venue = raw_event.get("venue") or {}
    ticket_info = raw_event.get("ticket_info") or []
    address = raw_event.get("address") or []
    title = str(raw_event.get("title") or "").strip()
    source_id = _source_id(raw_event)

    return EventCandidate(
        sourceId=source_id,
        title=title,
        description=raw_event.get("description"),
        dateText=date.get("when") or date.get("start_date"),
        startDate=date.get("start_date"),
        when=date.get("when"),
        venueName=venue.get("name"),
        address=[str(part) for part in address if part],
        link=raw_event.get("link"),
        ticketLinks=[
            TicketLink(
                source=item.get("source"),
                link=item["link"],
                linkType=item.get("link_type"),
            )
            for item in ticket_info
            if item.get("link")
        ],
        thumbnail=raw_event.get("thumbnail") or raw_event.get("image"),
        score=0.0,
    )


def _rank_events(events: list[EventCandidate]) -> list[EventCandidate]:
    ranked = []
    seen = set()
    for event in events:
        if not event.title:
            continue
        dedupe_key = (event.title.lower(), event.dateText or "", event.venueName or "")
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        event.score = _event_score(event)
        ranked.append(event)

    return sorted(ranked, key=lambda candidate: candidate.score, reverse=True)


def _event_score(event: EventCandidate) -> float:
    score = 20.0
    score += 8.0 if event.venueName else 0.0
    score += 8.0 if event.dateText else 0.0
    score += 5.0 if event.description else 0.0
    score += min(len(event.ticketLinks), 4) * 2.0
    score += 3.0 if event.link else 0.0
    score += 3.0 if event.thumbnail else 0.0
    if any("online" in part.lower() or "virtual" in part.lower() for part in event.address):
        score -= 10.0
    if event.description and ("online" in event.description.lower() or "virtual" in event.description.lower()):
        score -= 6.0
    return score


def _source_id(raw_event: dict[str, Any]) -> str:
    parts = [
        raw_event.get("title") or "",
        (raw_event.get("date") or {}).get("when") or "",
        raw_event.get("link") or "",
        ((raw_event.get("venue") or {}).get("name")) or "",
    ]
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return f"serpapi:{digest[:16]}"
