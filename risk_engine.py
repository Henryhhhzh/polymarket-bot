from enum import Enum
from typing import Any


class TradingMode(str, Enum):
    OFF = "OFF"
    NORMAL_MARKET_MAKE = "NORMAL_MARKET_MAKE"
    WIDE_MARKET_MAKE = "WIDE_MARKET_MAKE"
    INVENTORY_REBALANCE = "INVENTORY_REBALANCE"


def choose_trading_mode(scores: dict[str, Any], market_data: dict[str, Any]) -> TradingMode:
    news_risk = scores["news_risk"]
    event_sensitivity = scores["event_sensitivity"]
    resolution_ambiguity = scores["resolution_ambiguity"]
    tradeability = scores["tradeability"]

    days_to_resolution = market_data.get("days_to_resolution", 0)
    spread = market_data.get("spread", 0)
    liquidity = market_data.get("liquidity", 0)

    if days_to_resolution < 14:
        return TradingMode.OFF

    if resolution_ambiguity > 0.65:
        return TradingMode.OFF

    if tradeability < 0.40:
        return TradingMode.OFF

    if news_risk > 0.88:
        return TradingMode.OFF

    if liquidity < 10_000:
        return TradingMode.OFF

    if spread < 0.02:
        return TradingMode.OFF

    if news_risk > 0.70 or event_sensitivity > 0.70:
        return TradingMode.WIDE_MARKET_MAKE

    return TradingMode.NORMAL_MARKET_MAKE


def calculate_risk_score(scores: dict[str, Any], market_data: dict[str, Any]) -> float:
    volatility_5m = market_data.get("volatility_5m", 0)

    risk_score = (
        0.30 * scores["news_risk"]
        + 0.20 * scores["event_sensitivity"]
        + 0.20 * scores["resolution_ambiguity"]
        + 0.15 * scores["information_asymmetry"]
        + 0.10 * scores["manipulation_risk"]
        + 0.05 * min(volatility_5m * 10, 1)
    )

    return round(risk_score, 3)


def calculate_quote_width(scores: dict[str, Any], market_data: dict[str, Any]) -> float:
    volatility_5m = market_data.get("volatility_5m", 0)

    width = 0.015
    width += volatility_5m * 2.5
    width += scores["news_risk"] * 0.03
    width += scores["resolution_ambiguity"] * 0.02
    width += scores["information_asymmetry"] * 0.015

    return round(min(width, 0.12), 3)


if __name__ == "__main__":
    test_scores = {
        "news_risk": 0.85,
        "event_sensitivity": 0.9,
        "resolution_ambiguity": 0.1,
        "information_asymmetry": 0.5,
        "manipulation_risk": 0.2,
        "directional_bias_yes": 0.35,
        "confidence": 0.9,
        "tradeability": 0.75,
    }

    test_market_data = {
        "spread": 0.04,
        "liquidity": 42000,
        "volatility_5m": 0.018,
        "days_to_resolution": 38,
    }

    mode = choose_trading_mode(test_scores, test_market_data)
    risk_score = calculate_risk_score(test_scores, test_market_data)
    quote_width = calculate_quote_width(test_scores, test_market_data)

    print("Mode:", mode.value)
    print("Risk score:", risk_score)
    print("Quote width:", quote_width)