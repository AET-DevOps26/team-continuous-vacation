import json
import re
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/health":
            return self.respond({"status": "ok"})
        if parsed.path.endswith("/search"):
            return self.respond([{
                "lat": "48.137154", "lon": "11.576124", "name": "Munich",
                "display_name": "Munich, Germany", "address": {"country_code": "de"},
                "namedetails": {"name:en": "Munich"},
            }])
        if parsed.path == "/events":
            return self.respond({"events_results": [{
                "title": "Mock Summer Festival",
                "date": {"when": "This weekend"},
                "venue": {"name": "Mock Park"},
                "link": "https://example.invalid/events/1",
            }]})
        if parsed.path == "/weather":
            return self.respond(weather(query))
        self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != "/v1/chat/completions":
            return self.send_error(404)
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        prompt = payload.get("messages", [{}, {}])[-1].get("content", "")
        content = route(prompt)
        self.respond({
            "id": "mock-completion", "object": "chat.completion",
            "created": 0, "model": "mock-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(content)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        })

    def respond(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def route(prompt):
    if "Classify whether" in prompt:
        return classification()
    if "Create one replacement activity" in prompt:
        return alternative(prompt)
    return schedule(prompt)


def classification():
    return {"shouldFetchEventsContext": True, "reason": "Mock city trip"}


def alternative(prompt):
    # _validate_alternative_contract rejects a replacement that changes the time block, so
    # take it from the response shape the prompt asks for rather than guessing. The shape is
    # the only place the replaced activity's block appears unambiguously -- "timeBlock" also
    # occurs throughout the serialised trip context.
    match = re.search(r'exact shape:\s*\{\s*"timeBlock":\s*"(\w+)"', prompt)
    return {
        "timeBlock": match.group(1) if match else "AFTERNOON",
        # Must collide with neither the replaced title nor any other title in the trip, both
        # of which schedule() builds as "<name> <date>".
        "title": "Mock Replacement Activity",
        "description": "Deterministic mocked replacement.",
        "durationMinutes": 90,
        "isIndoor": True,
        "tags": ["INDOOR", "CULTURAL"],
    }


def schedule(prompt):
    start_match = re.search(r'"startDate"\s*:\s*"(\d{4}-\d{2}-\d{2})"', prompt)
    end_match = re.search(r'"endDate"\s*:\s*"(\d{4}-\d{2}-\d{2})"', prompt)
    start = date.fromisoformat(start_match.group(1)) if start_match else date.today()
    end = date.fromisoformat(end_match.group(1)) if end_match else start
    days = []
    current = start
    while current <= end:
        activities = []
        for block, title in (("MORNING", "Museum"), ("AFTERNOON", "City Walk"), ("EVENING", "Dinner")):
            activities.append({
                "timeBlock": block, "title": f"{title} {current.isoformat()}",
                "description": "Deterministic mocked activity.", "durationMinutes": 90,
                "isIndoor": block != "AFTERNOON", "tags": ["CULTURAL"],
            })
        days.append({"dayNumber": len(days) + 1, "date": current.isoformat(), "activities": activities})
        current += timedelta(days=1)
    return {"days": days}


def weather(query):
    start = date.fromisoformat(query.get("start_date", [date.today().isoformat()])[0])
    end = date.fromisoformat(query.get("end_date", [start.isoformat()])[0])
    times, temperatures, precipitation, probability, codes = [], [], [], [], []
    current = start
    while current <= end:
        for hour in range(24):
            times.append(f"{current.isoformat()}T{hour:02d}:00")
            temperatures.append(18.0)
            precipitation.append(0.0)
            probability.append(5)
            codes.append(0)
        current += timedelta(days=1)
    return {"hourly": {
        "time": times, "temperature_2m": temperatures,
        "precipitation": precipitation, "precipitation_probability": probability,
        "weather_code": codes,
    }}


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
