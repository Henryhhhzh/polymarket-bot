from llm_scorer import score_market
from risk_engine import (
    calculate_quote_width,
    calculate_risk_score,
    choose_trading_mode,
)


def main() -> None:
    market_question = "Will the Fed cut interest rates before July 2026?"

    resolution_criteria = (
        "This market resolves YES if the Federal Reserve announces an interest "
        "rate cut before July 1, 2026."
    )

    market_data = {
        "mid_price": 0.47,
        "spread": 0.04,
        "volume_24h": 180000,
        "liquidity": 42000,
        "volatility_5m": 0.018,
        "volatility_1h": 0.044,
        "days_to_resolution": 38,
    }

    headlines = [
        "Fed officials signal caution on inflation.",
        "Markets reduce expectations for near-term rate cuts.",
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

    print("Market:", market_question)
    print("Mode:", mode.value)
    print("Risk score:", risk_score)
    print("Quote width:", quote_width)
    print("LLM scores:")
    print(scores.model_dump_json(indent=2))


if __name__ == "__main__":
    main()