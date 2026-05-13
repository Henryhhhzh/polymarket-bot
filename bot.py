from llm_scorer import score_market
from market_data import (
    choose_candidate_markets,
    extract_markets_from_events,
    fetch_active_events,
)
from risk_engine import (
    calculate_quote_width,
    calculate_risk_score,
    choose_trading_mode,
)


def build_market_data_for_scorer(market: dict) -> dict:
    prices = market.get("outcome_prices", [])

    mid_price = 0.5
    if prices:
        try:
            mid_price = float(prices[0])
        except (TypeError, ValueError):
            mid_price = 0.5

    return {
        "mid_price": mid_price,
        "spread": 0.04,  # placeholder until we read real order book
        "volume_24h": market["volume_24h"],
        "liquidity": market["liquidity"],
        "volatility_5m": 0.02,  # placeholder until price history exists
        "volatility_1h": 0.04,  # placeholder until price history exists
        "days_to_resolution": market["days_to_resolution"],
    }


def main() -> None:
    events = fetch_active_events(limit=50)
    markets = extract_markets_from_events(events)
    candidates = choose_candidate_markets(markets)

    if not candidates:
        print("No suitable markets found.")
        return

    market = candidates[0]
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
    print("=" * 80)
    print("Mode:", mode.value)
    print("Risk score:", risk_score)
    print("Quote width:", quote_width)
    print("=" * 80)
    print("LLM scores:")
    print(scores.model_dump_json(indent=2))


if __name__ == "__main__":
    main()