#!/usr/bin/env python3
"""Small deterministic concurrency check for the mocked Compose stack."""

import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta


def post(url: str, payload: bytes) -> float:
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        json.load(response)
    return time.perf_counter() - started


def run(name: str, url: str, payload: bytes, requests: int, concurrency: int) -> None:
    latencies = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(post, url, payload) for _ in range(requests)]
        for future in as_completed(futures):
            latencies.append(future.result())
    ordered = sorted(latencies)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    print(
        f"{name}: {len(latencies)}/{requests} succeeded; "
        f"mean={statistics.mean(latencies):.3f}s p95={p95:.3f}s"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--genai-url", default="http://localhost:8000")
    parser.add_argument("--travel-context-url", default="http://localhost:8090")
    args = parser.parse_args()
    if args.requests <= 0 or args.concurrency <= 0:
        parser.error("requests and concurrency must be positive")

    start = date.today() + timedelta(days=1)
    payload = json.dumps(
        {
            "destination": "Munich",
            "startDate": start.isoformat(),
            "endDate": (start + timedelta(days=1)).isoformat(),
            "vibe": "cultural",
        }
    ).encode()
    run(
        "travel-context",
        f"{args.travel_context_url}/trip-context",
        payload,
        args.requests,
        args.concurrency,
    )
    run(
        "genai",
        f"{args.genai_url}/schedules/generate",
        payload,
        args.requests,
        args.concurrency,
    )


if __name__ == "__main__":
    main()
