from app.services.cache import TtlCache


def test_ttl_cache_returns_value_until_expiry(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("app.services.cache.time.time", lambda: now)
    cache = TtlCache[str](ttl_seconds=10)

    cache.set("destination:munich", "cached")

    assert cache.get("destination:munich") == "cached"


def test_ttl_cache_expires_and_removes_value(monkeypatch):
    current_time = {"value": 1000.0}
    monkeypatch.setattr("app.services.cache.time.time", lambda: current_time["value"])
    cache = TtlCache[str](ttl_seconds=10)
    cache.set("destination:munich", "cached")

    current_time["value"] = 1011.0

    assert cache.get("destination:munich") is None
    assert cache.get("destination:munich") is None
