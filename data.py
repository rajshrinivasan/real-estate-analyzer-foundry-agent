"""
Simulated market data for the Real Estate Market Analyzer.

In production these would be replaced by live API integrations:
  - Property listings: Zillow / Redfin API
  - Neighbourhood stats: Walk Score API
  - School ratings: GreatSchools API
  - Crime indices: FBI Uniform Crime Reporting (UCR)
  - Mortgage rates: Freddie Mac Primary Mortgage Market Survey
"""

LISTINGS_DATA = {
    "austin": {
        "median_price": 485000,
        "active_listings": 3240,
        "new_listings_30d": 890,
        "median_days_on_market": 18,
        "list_to_sale_ratio": 0.97,
        "price_trend_yoy": +4.2,
        "inventory_months": 2.1,
    },
    "phoenix": {
        "median_price": 412000,
        "active_listings": 5100,
        "new_listings_30d": 1420,
        "median_days_on_market": 28,
        "list_to_sale_ratio": 0.95,
        "price_trend_yoy": -1.8,
        "inventory_months": 3.6,
    },
    "denver": {
        "median_price": 558000,
        "active_listings": 2870,
        "new_listings_30d": 740,
        "median_days_on_market": 22,
        "list_to_sale_ratio": 0.98,
        "price_trend_yoy": +2.1,
        "inventory_months": 2.4,
    },
    "miami": {
        "median_price": 621000,
        "active_listings": 4200,
        "new_listings_30d": 980,
        "median_days_on_market": 35,
        "list_to_sale_ratio": 0.93,
        "price_trend_yoy": +6.8,
        "inventory_months": 4.1,
    },
}

NEIGHBORHOOD_DATA = {
    "austin": {
        "walkability": 52,
        "transit_score": 38,
        "amenities": ["tech hub", "live music", "parks", "UT campus proximity"],
        "avg_commute_min": 28,
    },
    "phoenix": {
        "walkability": 41,
        "transit_score": 29,
        "amenities": ["golf courses", "desert trails", "sunshine 300+ days/yr"],
        "avg_commute_min": 24,
    },
    "denver": {
        "walkability": 61,
        "transit_score": 55,
        "amenities": ["ski access", "mountain biking", "craft beer scene", "RiNo arts district"],
        "avg_commute_min": 26,
    },
    "miami": {
        "walkability": 78,
        "transit_score": 57,
        "amenities": ["beaches", "nightlife", "international food", "Brickell finance district"],
        "avg_commute_min": 34,
    },
}

SCHOOL_DATA = {
    "austin": {
        "district_rating": 7.8,
        "top_schools": ["Liberal Arts & Science Academy", "Ann Richards School"],
        "avg_class_size": 21,
        "graduation_rate": 91.2,
    },
    "phoenix": {
        "district_rating": 6.2,
        "top_schools": ["Basis Phoenix", "Great Hearts Academies"],
        "avg_class_size": 26,
        "graduation_rate": 84.7,
    },
    "denver": {
        "district_rating": 7.1,
        "top_schools": ["Denver School of the Arts", "East High School"],
        "avg_class_size": 23,
        "graduation_rate": 88.4,
    },
    "miami": {
        "district_rating": 7.4,
        "top_schools": ["Design & Architecture Senior High", "iPrep Academy"],
        "avg_class_size": 24,
        "graduation_rate": 87.9,
    },
}

CRIME_DATA = {
    "austin": {
        "violent_crime_index": 32,
        "property_crime_index": 48,
        "trend": "declining",
        "vs_national_avg": -12,
    },
    "phoenix": {
        "violent_crime_index": 51,
        "property_crime_index": 67,
        "trend": "stable",
        "vs_national_avg": +18,
    },
    "denver": {
        "violent_crime_index": 38,
        "property_crime_index": 55,
        "trend": "declining",
        "vs_national_avg": -5,
    },
    "miami": {
        "violent_crime_index": 44,
        "property_crime_index": 58,
        "trend": "stable",
        "vs_national_avg": +8,
    },
}

MORTGAGE_RATES = {
    "30yr_fixed": 6.85,
    "15yr_fixed": 6.12,
    "5_1_arm": 6.24,
    "jumbo_30yr": 7.10,
    "fha_30yr": 6.61,
}
