from app.models.schemas import PlaceCandidate
from app.services.ranking import PlaceRanker


def place(name, tags, lat=48.13, lon=11.57):
    return PlaceCandidate(
        source="openstreetmap",
        sourceId=f"relation:{name}",
        name=name,
        category=None,
        latitude=lat,
        longitude=lon,
        website=tags.get("website"),
        wikipedia=tags.get("wikipedia"),
        openingHours=tags.get("opening_hours"),
        osmTags=tags,
    )


def test_munich_reference_landmarks_rank_near_top():
    ranker = PlaceRanker()
    candidates = [
        place("Unnamed lawn", {"leisure": "park"}, 48.10, 11.50),
        place("Administrative Area", {"boundary": "administrative", "admin_level": "10"}, 48.10, 11.51),
        place(
            "Olympiapark",
            {"leisure": "park", "wikidata": "Q639679", "wikipedia": "de:Olympiapark München"},
            48.17,
            11.55,
        ),
        place(
            "Marienplatz",
            {"place": "square", "wikidata": "Q324144", "wikipedia": "de:Marienplatz"},
            48.13,
            11.57,
        ),
        place(
            "Englischer Garten",
            {"leisure": "park", "wikidata": "Q147487", "wikipedia": "de:Englischer Garten"},
            48.16,
            11.60,
        ),
        place(
            "Schloss Nymphenburg",
            {"historic": "castle", "tourism": "attraction", "website": "https://example.invalid"},
            48.15,
            11.50,
        ),
        place(
            "Tierpark Hellabrunn",
            {"tourism": "zoo", "wikidata": "Q688515", "opening_hours": "Mo-Su 09:00-18:00"},
            48.10,
            11.55,
        ),
        place("Eisbach", {"waterway": "stream", "wikidata": "Q707787", "wikipedia": "de:Eisbach"}, 48.14, 11.58),
        place("Generic office", {"office": "company", "website": "https://example.invalid"}, 48.11, 11.52),
    ]

    ranked = ranker.rank(candidates, limit=8)
    top_names = [candidate.name for candidate in ranked[:6]]

    assert "Olympiapark" in top_names
    assert "Marienplatz" in top_names
    assert "Englischer Garten" in top_names
    assert "Schloss Nymphenburg" in top_names
    assert "Tierpark Hellabrunn" in top_names
    assert "Eisbach" in top_names


def test_metadata_rich_places_outrank_low_information_objects():
    ranker = PlaceRanker()
    ranked = ranker.rank(
        [
            place("Small Park", {"leisure": "park"}, 48.1, 11.5),
            place("Known Museum", {"tourism": "museum", "wikidata": "Q1", "website": "https://example.invalid"}, 48.2, 11.6),
        ],
        limit=2,
    )

    assert ranked[0].name == "Known Museum"


def test_duplicates_are_collapsed_by_name_and_nearby_coordinates():
    ranker = PlaceRanker()
    ranked = ranker.rank(
        [
            place("Marienplatz", {"place": "square"}, 48.137, 11.575),
            place("Marienplatz", {"place": "square", "wikidata": "Q324144"}, 48.1371, 11.5751),
        ],
        limit=10,
    )

    assert len(ranked) == 1
    assert ranked[0].osmTags["wikidata"] == "Q324144"


def test_nameless_and_admin_only_objects_are_filtered_or_low_ranked():
    ranker = PlaceRanker()
    ranked = ranker.rank(
        [
            PlaceCandidate(
                source="openstreetmap",
                sourceId="way:1",
                name="",
                latitude=48.1,
                longitude=11.5,
                osmTags={"leisure": "park"},
            ),
            place("Admin Boundary", {"boundary": "administrative", "admin_level": "8"}, 48.1, 11.5),
        ],
        limit=10,
    )

    assert ranked == []
