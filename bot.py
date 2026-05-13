from llm_scorer import score_market
from market_data import (
    choose_candidate_markets,
    enrich_market_with_orderbook,
    extract_markets_from_events,
    fetch_active_events,
)
from risk_engine import (
    calculate_quote_width,
    calculate_risk_score,
    choose_trading_mode,
)


def build_market_data_for_scorer(market: dict) -> dict:
    orderbook_features = market["orderbook_features"]

    return {
        "mid_price": orderbook_features["mid_price"],
        "spread": orderbook_features["spread"],
        "best_bid": orderbook_features["best_bid"],
        "best_ask": orderbook_features["best_ask"],
        "bid_depth": orderbook_features["bid_depth"],
        "ask_depth": orderbook_features["ask_depth"],
        "orderbook_imbalance": orderbook_features["orderbook_imbalance"],
        "volume_24h": market["volume_24h"],
        "liquidity": market["liquidity"],
        "volatility_5m": 0.02,
        "volatility_1h": 0.04,
        "days_to_resolution": market["days_to_resolution"],
    }


def main() -> None:
    events = fetch_active_events(limit=50)
    markets = extract_markets_from_events(events)
    candidates = choose_candidate_markets(markets)

    if not candidates:
        print("No suitable markets found.")
        return

    market = enrich_market_with_orderbook(candidates[0])
    market_data = build_market_data_for_scorer(market)

    market_question = market["question"]
    resolution_criteria = market.get("description") or "No resolution criteria provided."

    headlines = [
        "No external headlines connected yet.",
        "This score is based mainly on market metadata and resolution criteria.",
    ]

    scores = score_market(
        market_question=market_question,
        resolution_criteria=resolution_criteria,
        market_data=market_data,
        headlines=headlines,
    )

    scores_dict = scores.model_dump()

    mode = choose_trading_mode(scores_dict, market_data)
    risk_score = calculate_risk_score(scores_dict, market_data)
    quote_width = calculate_quote_width(scores_dict, market_data)

    print("=" * 80)
    print("Selected market:", market_question)
    print("Event:", market["event_title"])
    print("URL:", market["url"])
    print("Days to resolution:", market["days_to_resolution"])
    print("Volume 24h:", market["volume_24h"])
    print("Liquidity:", market["liquidity"])
    print("Outcome prices:", market["outcome_prices"])
    print("Best bid:", market_data["best_bid"])
    print("Best ask:", market_data["best_ask"])
    print("Real spread:", market_data["spread"])
    print("Bid depth:", market_data["bid_depth"])
    print("Ask depth:", market_data["ask_depth"])
    print("Orderbook imbalance:", market_data["orderbook_imbalance"])
    print("=" * 80)
    print("Mode:", mode.value)
    print("Risk score:", risk_score)
    print("Quote width:", quote_width)
    print("=" * 80)
    print("LLM scores:")
    print(scores.model_dump_json(indent=2))


if __name__ == "__main__":
    main()