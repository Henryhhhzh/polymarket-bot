
from enum import Enum
from typing import Any

from config import (
    AMBIGUITY_QUOTE_MULTIPLIER,
    BASE_QUOTE_WIDTH,
    HIGH_EVENT_SENSITIVITY,
    HIGH_NEWS_RISK,
    INFORMATION_ASYMMETRY_QUOTE_MULTIPLIER,
    MAX_NEWS_RISK_OFF,
    MAX_QUOTE_WIDTH,
    MAX_RESOLUTION_AMBIGUITY,
    MIN_DAYS_TO_RESOLUTION,
    MIN_LIQUIDITY_FOR_TRADING,
    MIN_SPREAD,
    MIN_TRADEABILITY,
    NEWS_RISK_QUOTE_MULTIPLIER,
    RISK_WEIGHT_AMBIGUITY,
    RISK_WEIGHT_EVENT,
    RISK_WEIGHT_INFORMATION_ASYMMETRY,
    RISK_WEIGHT_MANIPULATION,
    RISK_WEIGHT_NEWS,
    RISK_WEIGHT_VOLATILITY,
    VOLATILITY_QUOTE_MULTIPLIER,
)


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

    if days_to_resolution < MIN_DAYS_TO_RESOLUTION:
        return TradingMode.OFF

    if resolution_ambiguity > MAX_RESOLUTION_AMBIGUITY:
        return TradingMode.OFF

    if tradeability < MIN_TRADEABILITY:
        return TradingMode.OFF

    if news_risk > MAX_NEWS_RISK_OFF:
        return TradingMode.OFF

    if liquidity < MIN_LIQUIDITY_FOR_TRADING:
        return TradingMode.OFF

    if spread < MIN_SPREAD:
        return TradingMode.OFF

    if news_risk > HIGH_NEWS_RISK or event_sensitivity > HIGH_EVENT_SENSITIVITY:
        return TradingMode.WIDE_MARKET_MAKE

    return TradingMode.NORMAL_MARKET_MAKE


def calculate_risk_score(scores: dict[str, Any], market_data: dict[str, Any]) -> float:
    volatility_5m = market_data.get("volatility_5m", 0)

    risk_score = (
        RISK_WEIGHT_NEWS * scores["news_risk"]
        + RISK_WEIGHT_EVENT * scores["event_sensitivity"]
        + RISK_WEIGHT_AMBIGUITY * scores["resolution_ambiguity"]
        + RISK_WEIGHT_INFORMATION_ASYMMETRY * scores["information_asymmetry"]
        + RISK_WEIGHT_MANIPULATION * scores["manipulation_risk"]
        + RISK_WEIGHT_VOLATILITY * min(volatility_5m * 10, 1)
    )

    return round(risk_score, 3)


def calculate_quote_width(scores: dict[str, Any], market_data: dict[str, Any]) -> float:
    volatility_5m = market_data.get("volatility_5m", 0)

    width = BASE_QUOTE_WIDTH
    width += volatility_5m * VOLATILITY_QUOTE_MULTIPLIER
    width += scores["news_risk"] * NEWS_RISK_QUOTE_MULTIPLIER
    width += scores["resolution_ambiguity"] * AMBIGUITY_QUOTE_MULTIPLIER
    width += scores["information_asymmetry"] * INFORMATION_ASYMMETRY_QUOTE_MULTIPLIER

    return round(min(width, MAX_QUOTE_WIDTH), 3)


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