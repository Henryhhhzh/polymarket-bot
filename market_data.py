import json
from datetime import datetime, timezone
from typing import Any

import requests


GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"

CLOB_BOOK_URL = "https://clob.polymarket.com/book"


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

def fetch_order_book(token_id: str) -> dict[str, Any]:
    params = {"token_id": token_id}

    response = requests.get(CLOB_BOOK_URL, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Unexpected CLOB orderbook response format")

    return data


def calculate_orderbook_features(order_book: dict[str, Any]) -> dict[str, float]:
    bids = order_book.get("bids", [])
    asks = order_book.get("asks", [])

    if not bids or not asks:
        return {
            "best_bid": 0.0,
            "best_ask": 0.0,
            "mid_price": 0.5,
            "spread": 1.0,
            "bid_depth": 0.0,
            "ask_depth": 0.0,
            "orderbook_imbalance": 0.5,
        }

    bid_prices = [safe_float(level.get("price")) for level in bids]
    ask_prices = [safe_float(level.get("price")) for level in asks]

    best_bid = max(bid_prices)
    best_ask = min(ask_prices)

    bid_depth = sum(
        safe_float(level.get("price")) * safe_float(level.get("size"))
        for level in bids[:10]
    )

    ask_depth = sum(
        safe_float(level.get("price")) * safe_float(level.get("size"))
        for level in asks[:10]
    )

    total_depth = bid_depth + ask_depth

    if total_depth > 0:
        orderbook_imbalance = bid_depth / total_depth
    else:
        orderbook_imbalance = 0.5

    mid_price = (best_bid + best_ask) / 2
    spread = best_ask - best_bid

    return {
        "best_bid": round(best_bid, 4),
        "best_ask": round(best_ask, 4),
        "mid_price": round(mid_price, 4),
        "spread": round(spread, 4),
        "bid_depth": round(bid_depth, 2),
        "ask_depth": round(ask_depth, 2),
        "orderbook_imbalance": round(orderbook_imbalance, 3),
    }


def enrich_market_with_orderbook(market: dict[str, Any]) -> dict[str, Any]:
    token_ids = market.get("clob_token_ids", [])

    if not token_ids:
        raise ValueError("Market has no CLOB token IDs")

    yes_token_id = str(token_ids[0])

    order_book = fetch_order_book(yes_token_id)
    features = calculate_orderbook_features(order_book)

    enriched = market.copy()
    enriched["yes_token_id"] = yes_token_id
    enriched["orderbook"] = order_book
    enriched["orderbook_features"] = features

    return enriched

if __name__ == "__main__":
    events = fetch_active_events(limit=50)
    markets = extract_markets_from_events(events)
    candidates = choose_candidate_markets(markets)

    print(f"Fetched events: {len(events)}")
    print(f"Extracted markets: {len(markets)}")
    print(f"Candidate markets: {len(candidates)}")

    for candidate in candidates[:5]:
        print_market_summary(candidate)

        try:
            enriched = enrich_market_with_orderbook(candidate)
            print("Orderbook features:", enriched["orderbook_features"])
        except Exception as error:
            print("Could not fetch orderbook:", error)