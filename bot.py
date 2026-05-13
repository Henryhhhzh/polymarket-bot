from config import (
    DEFAULT_VOLATILITY_1H,
    DEFAULT_VOLATILITY_5M,
    EVENT_FETCH_LIMIT,
    MAX_SPREAD,
    MIN_ASK_DEPTH,
    MIN_BID_DEPTH,
    MIN_DAYS_TO_RESOLUTION,
    MIN_LIQUIDITY,
    MIN_SPREAD,
    MIN_VOLUME_24H,
)
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
        "volatility_5m": DEFAULT_VOLATILITY_5M,
        "volatility_1h": DEFAULT_VOLATILITY_1H,
        "days_to_resolution": market["days_to_resolution"],
    }


def passes_basic_trade_filter(market_data: dict) -> bool:
    if market_data["best_bid"] <= 0 or market_data["best_ask"] <= 0:
        print("Skipped: empty orderbook")
        print("Best bid:", market_data["best_bid"])
        print("Best ask:", market_data["best_ask"])
        return False

    if market_data["spread"] < MIN_SPREAD:
        print("Skipped: spread too small")
        print("Spread:", market_data["spread"])
        print("Minimum spread:", MIN_SPREAD)
        return False

    if market_data["spread"] > MAX_SPREAD:
        print("Skipped: spread too large")
        print("Spread:", market_data["spread"])
        print("Maximum spread:", MAX_SPREAD)
        return False

    if market_data["bid_depth"] < MIN_BID_DEPTH:
        print("Skipped: bid depth too low")
        print("Bid depth:", market_data["bid_depth"])
        print("Minimum bid depth:", MIN_BID_DEPTH)
        return False

    if market_data["ask_depth"] < MIN_ASK_DEPTH:
        print("Skipped: ask depth too low")
        print("Ask depth:", market_data["ask_depth"])
        print("Minimum ask depth:", MIN_ASK_DEPTH)
        return False

    return True


def main() -> None:
    events = fetch_active_events(limit=EVENT_FETCH_LIMIT)
    markets = extract_markets_from_events(events)
    candidates = choose_candidate_markets(
        markets,
        min_liquidity=MIN_LIQUIDITY,
        min_volume_24h=MIN_VOLUME_24H,
        min_days_to_resolution=MIN_DAYS_TO_RESOLUTION,
    )

    if not candidates:
        print("No suitable markets found.")
        return

    selected_market = None
    selected_market_data = None

    for candidate in candidates:
        try:
            market = enrich_market_with_orderbook(candidate)
            market_data = build_market_data_for_scorer(market)
        except Exception as error:
            print("Skipped: could not load orderbook")
            print("Question:", candidate.get("question", "Unknown question"))
            print("Error:", error)
            continue

        print("Checking market:", market["question"])

        if not passes_basic_trade_filter(market_data):
            continue

        selected_market = market
        selected_market_data = market_data
        break

    if selected_market is None or selected_market_data is None:
        print("No candidate market passed the basic trade filter.")
        return

    market = selected_market
    market_data = selected_market_data

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