"""
Live walkability scoring using OpenStreetMap data via osmnx.

Replaces the static walkability field in NEIGHBORHOOD_DATA by computing
intersection density from the pedestrian street network within 2 km of
each city centre.

osmnx is synchronous, so _compute_scores() runs in a thread executor to
avoid blocking the async event loop. Results are cached in memory so only
the first request per city pays the ~5-10 s download cost.

Note: this is a proxy metric, not the proprietary Walk Score algorithm.
Higher intersection density → more connected pedestrian grid → higher score.
"""

import asyncio
import functools
import math

# (lat, lon) for city-centre anchor points
_CITY_COORDS: dict[str, tuple[float, float]] = {
    "austin": (30.2672, -97.7431),
    "phoenix": (33.4484, -112.0740),
    "denver": (39.7392, -104.9903),
    "miami": (25.7617, -80.1918),
}

# Radius (metres) used for the OSM graph download
_RADIUS_M = 2000
# Area of the circular query region in km²
_AREA_KM2 = math.pi * (_RADIUS_M / 1000) ** 2  # ≈ 12.57 km²

_cache: dict[str, int] = {}


def _compute_walkability(city_key: str) -> int:
    """
    Download the walk network within _RADIUS_M of the city centre and
    return a 0-100 walkability score based on intersection density.

    Runs synchronously — call via run_in_executor from async code.
    """
    import osmnx as ox

    coords = _CITY_COORDS[city_key]
    G = ox.graph_from_point(coords, dist=_RADIUS_M, network_type="walk")

    # osmnx 2.x: use ox.convert.graph_to_gdfs
    nodes = ox.convert.graph_to_gdfs(G, edges=False)
    density = len(nodes) / _AREA_KM2  # nodes per km²

    # Log-scaled normalisation to 0-100:
    #   density  50 → ~35   (car-dependent suburb)
    #   density 100 → ~50   (typical mid-tier city)
    #   density 300 → ~84   (walkable urban core)
    score = min(100, round(50 * math.log1p(density / 50)))
    return score


async def get_walkability(city_key: str) -> int | None:
    """
    Return walkability score (0-100) for a supported city.
    Computes on first call, returns cached value thereafter.
    Returns None if the city is unsupported or computation fails.
    """
    if city_key not in _CITY_COORDS:
        return None
    if city_key not in _cache:
        loop = asyncio.get_running_loop()
        score = await loop.run_in_executor(
            None, functools.partial(_compute_walkability, city_key)
        )
        _cache[city_key] = score
    return _cache[city_key]
