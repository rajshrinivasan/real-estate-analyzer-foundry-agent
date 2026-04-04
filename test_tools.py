"""
Unit tests for async tool functions.

These tests run entirely locally — no Azure credentials required.
They validate tool outputs, error handling, and the concurrency speedup.
"""

import asyncio
import json
import time

import pytest

from tools import (
    FUNCTION_MAP,
    get_crime_index,
    get_mortgage_rates,
    get_neighborhood_stats,
    get_property_listings,
    get_school_ratings,
)

SUPPORTED_CITIES = ["austin", "phoenix", "denver", "miami"]


# ── Property listings ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("city", SUPPORTED_CITIES)
async def test_get_property_listings_known_city(city):
    data = json.loads(await get_property_listings(city))
    assert "error" not in data
    assert data["city"] == city
    assert data["median_price"] > 0
    assert 0 < data["inventory_months"] < 12
    assert 0 < data["list_to_sale_ratio"] <= 1


async def test_get_property_listings_unknown_city():
    data = json.loads(await get_property_listings("atlantis"))
    assert "error" in data


async def test_get_property_listings_case_insensitive():
    lower = json.loads(await get_property_listings("austin"))
    upper = json.loads(await get_property_listings("Austin"))
    assert lower["median_price"] == upper["median_price"]


# ── Neighbourhood stats ───────────────────────────────────────────────────────

@pytest.mark.parametrize("city", SUPPORTED_CITIES)
async def test_get_neighborhood_stats_known_city(city):
    data = json.loads(await get_neighborhood_stats(city))
    assert "error" not in data
    assert 0 <= data["walkability"] <= 100
    assert 0 <= data["transit_score"] <= 100
    assert isinstance(data["amenities"], list)
    assert len(data["amenities"]) > 0
    assert data["avg_commute_min"] > 0


async def test_get_neighborhood_stats_unknown_city():
    data = json.loads(await get_neighborhood_stats("neverland"))
    assert "error" in data


# ── School ratings ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("city", SUPPORTED_CITIES)
async def test_get_school_ratings_known_city(city):
    data = json.loads(await get_school_ratings(city))
    assert "error" not in data
    assert 0 <= data["district_rating"] <= 10
    assert data["graduation_rate"] > 50
    assert isinstance(data["top_schools"], list)


async def test_get_school_ratings_unknown_city():
    data = json.loads(await get_school_ratings("narnia"))
    assert "error" in data


# ── Crime index ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("city", SUPPORTED_CITIES)
async def test_get_crime_index_known_city(city):
    data = json.loads(await get_crime_index(city))
    assert "error" not in data
    assert data["violent_crime_index"] > 0
    assert data["property_crime_index"] > 0
    assert data["trend"] in ("declining", "stable", "rising")


async def test_get_crime_index_unknown_city():
    data = json.loads(await get_crime_index("gotham"))
    assert "error" in data


# ── Mortgage rates ────────────────────────────────────────────────────────────

async def test_get_mortgage_rates_default():
    data = json.loads(await get_mortgage_rates())
    assert data["requested_type"] == "30yr_fixed"
    assert 2.0 < data["rate"] < 15.0
    assert "all_rates" in data
    assert len(data["all_rates"]) == 5


@pytest.mark.parametrize("loan_type", [
    "30yr_fixed", "15yr_fixed", "5_1_arm", "jumbo_30yr", "fha_30yr"
])
async def test_get_mortgage_rates_all_types(loan_type):
    data = json.loads(await get_mortgage_rates(loan_type))
    assert data["requested_type"] == loan_type
    assert data["rate"] > 0


async def test_get_mortgage_rates_unknown_type_falls_back():
    # Unknown loan type should fall back to the 30yr_fixed rate
    data = json.loads(await get_mortgage_rates("unknown_type"))
    assert data["rate"] == data["all_rates"]["30yr_fixed"]


# ── FUNCTION_MAP completeness ─────────────────────────────────────────────────

def test_function_map_contains_all_tools():
    expected = {
        "get_property_listings",
        "get_neighborhood_stats",
        "get_school_ratings",
        "get_crime_index",
        "get_mortgage_rates",
    }
    assert set(FUNCTION_MAP.keys()) == expected


def test_function_map_values_are_callable():
    for name, fn in FUNCTION_MAP.items():
        assert callable(fn), f"{name} is not callable"


# ── Concurrency benchmark ─────────────────────────────────────────────────────

async def test_concurrent_execution_is_faster_than_sequential():
    """
    Running all five tools with asyncio.gather() should complete in roughly
    the time of the slowest tool (~1.5 s), not the sum (~4.9 s).
    """
    sequential_estimate = 1.2 + 0.8 + 1.5 + 0.9 + 0.5  # 4.9 s

    t0 = time.perf_counter()
    await asyncio.gather(
        get_property_listings("austin"),
        get_neighborhood_stats("austin"),
        get_school_ratings("austin"),
        get_crime_index("austin"),
        get_mortgage_rates("30yr_fixed"),
    )
    elapsed = time.perf_counter() - t0

    assert elapsed < sequential_estimate, (
        f"Concurrent ({elapsed:.2f}s) was not faster than sequential ({sequential_estimate}s)"
    )
    # Allow generous headroom for slow CI environments
    assert elapsed < 2.5, f"Concurrent execution took {elapsed:.2f}s — expected ~1.5s"
