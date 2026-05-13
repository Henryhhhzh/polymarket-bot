import json
from datetime import datetime, timezone
from typing import Any

import requests


GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return []

    return []


def days_until(date_text: str | None) -> int:
    if not date_text:
        return 0

    try:
        clean = date_text.replace("Z", "+00:00")
        end_date = datetime.fromisoformat(clean)
        now = datetime.now(timezone.utc)
        return max((end_date - now).days, 0)
    except ValueError:
        return 0


def fetch_active_events(limit: int = 20) -> list[dict[str, Any]]:
    params = {
        "active": "true",
        "closed": "false",
        "order": "volume_24hr",
        "ascending": "false",
        "limit": limit,
    }

    response = requests.get(GAMMA_EVENTS_URL, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise ValueError("Unexpected Gamma API response format")

    return data


def extract_markets_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    extracted = []

    for event in events:
        event_title = event.get("title") or event.get("slug") or "Unknown event"
        markets = event.get("markets", [])

        if not isinstance(markets, list):
            continue

        for market in markets:
            question = market.get("question") or market.get("title")

            if not question:
                continue

            outcomes = parse_json_list(market.get("outcomes"))
            outcome_prices = parse_json_list(market.get("outcomePrices"))
            clob_token_ids = parse_json_list(market.get("clobTokenIds"))

            extracted.append(
                {
                    "event_title": event_title,
                    "market_id": market.get("id"),
                    "condition_id": market.get("conditionId"),
                    "question": question,
                    "description": market.get("description", ""),
                    "end_date": market.get("endDate"),
                    "days_to_resolution": days_until(market.get("endDate")),
                    "volume": safe_float(market.get("volume")),
                    "volume_24h": safe_float(
                        market.get("volume24hr")
                        or market.get("volume_24hr")
                        or market.get("volume24H")
                    ),
                    "liquidity": safe_float(market.get("liquidity")),
                    "outcomes": outcomes,
                    "outcome_prices": outcome_prices,
                    "clob_token_ids": clob_token_ids,
                    "active": market.get("active"),
                    "closed": market.get("closed"),
                    "url": f"https://polymarket.com/event/{event.get('slug', '')}",
                }
            )

    return extracted


def choose_candidate_markets(
    markets: list[dict[str, Any]],
    min_liquidity: float = 10_000,
    min_volume_24h: float = 5_000,
    min_days_to_resolution: int = 14,
) -> list[dict[str, Any]]:
    candidates = []

    for market in markets:
        if market["days_to_resolution"] < min_days_to_resolution:
            continue

        if market["liquidity"] < min_liquidity:
            continue

        if market["volume_24h"] < min_volume_24h:
            continue

        candidates.append(market)

    candidates.sort(
        key=lambda item: (item["volume_24h"], item["liquidity"]),
        reverse=True,
    )

    return candidates


def print_market_summary(market: dict[str, Any]) -> None:
    print("=" * 80)
    print("Event:", market["event_title"])
    print("Question:", market["question"])
    print("Days to resolution:", market["days_to_resolution"])
    print("Volume 24h:", market["volume_24h"])
    print("Liquidity:", market["liquidity"])
    print("Outcomes:", market["outcomes"])
    print("Prices:", market["outcome_prices"])
    print("CLOB token IDs:", market["clob_token_ids"])
    print("URL:", market["url"])


if __name__ == "__main__":
    events = fetch_active_events(limit=50)
    markets = extract_markets_from_events(events)
    candidates = choose_candidate_markets(markets)

    print(f"Fetched events: {len(events)}")
    print(f"Extracted markets: {len(markets)}")
    print(f"Candidate markets: {len(candidates)}")

    for candidate in candidates[:5]:
        print_market_summary(candidate)