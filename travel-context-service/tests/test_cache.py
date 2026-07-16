from app.services.cache import TtlCache


def test_ttl_cache_returns_value_until_expiry(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: now)
    cache = TtlCache[str](ttl_seconds=10)

    cache.set("destination:munich", "cached")

    assert cache.get("destination:munich") == "cached"


def test_ttl_cache_expires_and_removes_value(monkeypatch):
    current_time = {"value": 1000.0}
    monkeypatch.setattr(
        "app.services.cache.time.monotonic", lambda: current_time["value"]
    )
    cache = TtlCache[str](ttl_seconds=10)
    cache.set("destination:munich", "cached")

    current_time["value"] = 1011.0

    assert cache.get("destination:munich") is None
    assert cache.get("destination:munich") is None


def test_ttl_cache_rejects_invalid_configuration():
    import pytest

    with pytest.raises(ValueError):
        TtlCache(ttl_seconds=0)
    with pytest.raises(ValueError):
        TtlCache(ttl_seconds=1, max_entries=0)


def test_ttl_cache_evicts_least_recently_used_entry(monkeypatch):
    monkeypatch.setattr("app.services.cache.time.monotonic", lambda: 100.0)
    cache = TtlCache[str](ttl_seconds=60, max_entries=2)
    cache.set("a", "A")
    cache.set("b", "B")
    assert cache.get("a") == "A"
    cache.set("c", "C")

    assert cache.get("b") is None
    assert cache.get("a") == "A"
    assert cache.get("c") == "C"
