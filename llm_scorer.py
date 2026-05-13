import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError


load_dotenv()


class MarketScores(BaseModel):
    news_risk: float = Field(ge=0.0, le=1.0)
    event_sensitivity: float = Field(ge=0.0, le=1.0)
    resolution_ambiguity: float = Field(ge=0.0, le=1.0)
    information_asymmetry: float = Field(ge=0.0, le=1.0)
    manipulation_risk: float = Field(ge=0.0, le=1.0)
    directional_bias_yes: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    tradeability: float = Field(ge=0.0, le=1.0)
    reason: str


def score_market(
    market_question: str,
    resolution_criteria: str,
    market_data: dict[str, Any],
    headlines: list[str],
) -> MarketScores:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in .env")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a prediction-market risk classifier.

Your job is not to recommend trades.
Your job is to convert qualitative and market information into numerical risk scores.

Score each field from 0.0 to 1.0.

Definitions:
- news_risk: likelihood that recent or upcoming news could cause sudden price movement
- event_sensitivity: how reactive this market is to new information
- resolution_ambiguity: how unclear or subjective the market resolution criteria are
- information_asymmetry: likelihood that some traders have faster or better information
- manipulation_risk: likelihood that the market can be moved by low liquidity, social media, or coordinated trading
- directional_bias_yes: whether recent context favours YES, where 0.5 is neutral
- confidence: how confident you are in the scores
- tradeability: how suitable this market is for passive market making

Market question:
{market_question}

Resolution criteria:
{resolution_criteria}

Current market data:
{json.dumps(market_data, indent=2)}

Recent headlines:
{json.dumps(headlines, indent=2)}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=MarketScores,
        ),
    )

    raw_text = response.text

    try:
        data = json.loads(raw_text)
        return MarketScores(**data)
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"Invalid Gemini output: {raw_text}") from error


if __name__ == "__main__":
    test_scores = score_market(
        market_question="Will the Fed cut interest rates before July 2026?",
        resolution_criteria="This market resolves YES if the Federal Reserve announces an interest rate cut before July 1, 2026.",
        market_data={
            "mid_price": 0.47,
            "spread": 0.04,
            "volume_24h": 180000,
            "liquidity": 42000,
            "volatility_5m": 0.018,
            "volatility_1h": 0.044,
            "days_to_resolution": 38,
        },
        headlines=[
            "Fed officials signal caution on inflation.",
            "Markets reduce expectations for near-term rate cuts.",
        ],
    )

    print(test_scores.model_dump_json(indent=2))