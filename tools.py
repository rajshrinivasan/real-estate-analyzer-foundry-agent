"""
Async tool functions for the Real Estate Market Analyzer.

Each function simulates realistic network latency with asyncio.sleep().
When the agent requests multiple tools in one turn, they execute concurrently
via asyncio.gather() in agent.py — total wait time equals the slowest tool,
not the sum of all tools.

Latencies are intentionally varied to make the concurrency benefit visible
in the timing output.
"""

import asyncio
import json

from data import LISTINGS_DATA, MORTGAGE_RATES, NEIGHBORHOOD_DATA, SCHOOL_DATA, CRIME_DATA
from walkability import get_walkability


async def get_property_listings(city: str) -> str:
    """
    Fetch current property listing data for a city.

    Args:
        city: City name (austin, phoenix, denver, miami)

    Returns:
        Listing inventory, median price, days on market, and price trend data.
    """
    await asyncio.sleep(1.2)  # simulate MLS API latency
    city_key = city.lower().strip()
    data = LISTINGS_DATA.get(city_key)
    if not data:
        return json.dumps({"error": f"No listing data available for {city}"})
    return json.dumps({"city": city, **data})


async def get_neighborhood_stats(city: str) -> str:
    """
    Fetch walkability, transit, amenities, and commute data for a city.

    Args:
        city: City name (austin, phoenix, denver, miami)

    Returns:
        Walkability score, transit score, key amenities, and average commute time.
    """
    city_key = city.lower().strip()
    data = NEIGHBORHOOD_DATA.get(city_key)
    if not data:
        return json.dumps({"error": f"No neighbourhood data for {city}"})

    # Replace static walkability with live OpenStreetMap computation.
    # Falls back to the hardcoded value if osmnx fails.
    live_score = await get_walkability(city_key)
    if live_score is not None:
        data = {**data, "walkability": live_score}

    return json.dumps({"city": city, **data})


async def get_school_ratings(city: str) -> str:
    """
    Fetch school district ratings and top schools for a city.

    Args:
        city: City name (austin, phoenix, denver, miami)

    Returns:
        District rating, top school names, average class size, and graduation rate.
    """
    await asyncio.sleep(1.5)  # simulate school data API latency (slowest)
    city_key = city.lower().strip()
    data = SCHOOL_DATA.get(city_key)
    if not data:
        return json.dumps({"error": f"No school data for {city}"})
    return json.dumps({"city": city, **data})


async def get_crime_index(city: str) -> str:
    """
    Fetch violent and property crime indices for a city.

    Args:
        city: City name (austin, phoenix, denver, miami)

    Returns:
        Violent crime index, property crime index, trend, and comparison to national average.
    """
    await asyncio.sleep(0.9)  # simulate crime stats API latency
    city_key = city.lower().strip()
    data = CRIME_DATA.get(city_key)
    if not data:
        return json.dumps({"error": f"No crime data for {city}"})
    return json.dumps({"city": city, **data})


async def get_mortgage_rates(loan_type: str = "30yr_fixed") -> str:
    """
    Fetch current mortgage interest rates.

    Args:
        loan_type: One of: 30yr_fixed, 15yr_fixed, 5_1_arm, jumbo_30yr, fha_30yr

    Returns:
        Current rate for the requested loan type plus all available rates.
    """
    await asyncio.sleep(0.5)  # simulate rates API latency (fastest)
    rate = MORTGAGE_RATES.get(loan_type, MORTGAGE_RATES["30yr_fixed"])
    return json.dumps({
        "requested_type": loan_type,
        "rate": rate,
        "all_rates": MORTGAGE_RATES,
        "as_of": "2026-03-31",
    })


FUNCTION_MAP = {
    "get_property_listings": get_property_listings,
    "get_neighborhood_stats": get_neighborhood_stats,
    "get_school_ratings": get_school_ratings,
    "get_crime_index": get_crime_index,
    "get_mortgage_rates": get_mortgage_rates,
}

# Responses-API tool definitions (flat format, not nested under "function")
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "get_property_listings",
        "description": "Fetch current property listing data for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name: austin, phoenix, denver, or miami",
                }
            },
            "required": ["city"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "get_neighborhood_stats",
        "description": "Fetch walkability, transit score, amenities, and average commute time for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name: austin, phoenix, denver, or miami",
                }
            },
            "required": ["city"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "get_school_ratings",
        "description": "Fetch school district rating, top school names, class size, and graduation rate for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name: austin, phoenix, denver, or miami",
                }
            },
            "required": ["city"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "get_crime_index",
        "description": "Fetch violent and property crime indices, trend, and comparison to national average for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name: austin, phoenix, denver, or miami",
                }
            },
            "required": ["city"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "get_mortgage_rates",
        "description": "Fetch current mortgage interest rates.",
        "parameters": {
            "type": "object",
            "properties": {
                "loan_type": {
                    "type": "string",
                    "description": (
                        "Loan type: 30yr_fixed, 15yr_fixed, 5_1_arm, jumbo_30yr, or fha_30yr. "
                        "Defaults to 30yr_fixed."
                    ),
                }
            },
            "required": [],
        },
        "strict": False,
    },
]
