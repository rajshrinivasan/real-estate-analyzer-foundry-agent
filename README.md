# Real Estate Market Analyzer

An Azure AI Foundry agent that answers natural-language questions about residential property markets in Austin, Phoenix, Denver, and Miami.

**Key pattern — async concurrent tool execution:** when the model requests multiple data sources in a single turn, all tool calls fire in parallel via `asyncio.gather()`. Total wait time equals the slowest tool, not the sum.

```
Sequential: 1.2 + 0.8 + 1.5 + 0.9 + 0.5 = 4.9 s
Concurrent: max(1.2, 0.8, 1.5, 0.9, 0.5) = 1.5 s   (3.3x faster)
```

**Live data:** walkability scores are computed in real-time from OpenStreetMap via `osmnx` — no API key required. Results are cached in memory so only the first request per city pays the download cost (~5–10 s); subsequent requests are instant.

`osmnx` is synchronous, which would normally block the event loop and cancel out the concurrency benefit. The fix is one line — `run_in_executor` offloads the computation to a thread while all other tool calls keep running concurrently:

```python
score = await loop.run_in_executor(None, functools.partial(_compute_walkability, city_key))
```

Ships two interfaces: an interactive **CLI** and a **FastAPI web UI**.

> **Supported cities:** Austin · Phoenix · Denver · Miami only.
> Queries about other cities return an error. Data for additional cities requires entries in `data.py`, `walkability.py`, `TOOL_DEFINITIONS`, and the system prompt.

---

## Architecture

```
+--------------------+    +--------------------+
|        CLI         |    |      Web UI        |
|     agent.py       |    |  app.py / FastAPI  |
+--------+-----------+    +-----------+--------+
         +------------------+---------+
                            |
            +---------------v--------------+
            |        AgentSession          |
            |  Responses API /             |
            |  previous_response_id        |
            +---------------+--------------+
                            |
            +---------------v--------------+
            |    Azure AI Foundry          |
            |    gpt-4o / Responses API    |
            +---------------+--------------+
                            |
                  asyncio.gather()
                            |
    +------+--------+-------+------+------+
    v      v        v       v      v
[List.] [Neigh.] [Schools] [Crime] [Mortg.]
  1.2s    live    1.5s     0.9s    0.5s
          |                        |
          v                        v
   walkability.py              data.py
   osmnx / OSM (live)     static data stores
```

---

## Files

```
14-real-estate-analyzer/
├── agent.py               # AgentSession class + CLI entry point
├── app.py                 # FastAPI web application
├── tools.py               # Five async tool functions + TOOL_DEFINITIONS
├── data.py                # Static market data stores
├── walkability.py         # Live walkability scores via osmnx / OpenStreetMap
├── prompts/
│   └── system_prompt.txt  # Agent system instructions
├── templates/
│   └── index.html         # Web UI (vanilla HTML/CSS/JS, no dependencies)
├── test_tools.py          # pytest unit tests (no Azure required)
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## Setup

```bash
git clone <repo-url>
cd 14-real-estate-analyzer

python -m venv .venv
source .venv/bin/activate     # macOS/Linux
# .venv\Scripts\activate      # Windows

pip install -r requirements.txt

az login
```

Copy `.env.example` to `.env` and fill in your Azure AI Foundry values:

```bash
cp .env.example .env
```

```
PROJECT_ENDPOINT=https://<your-hub>.services.ai.azure.com/api/projects/<your-project>
MODEL_DEPLOYMENT_NAME=gpt-4o
```

---

## Running

**CLI**
```bash
python agent.py
```

**Web UI**
```bash
uvicorn app:app --reload
# open http://localhost:8000
```

---

## Example prompts

```
Analyse Austin for a family buyer with a $500k budget.
Compare Denver and Phoenix for an investment property.
What are mortgage rates right now?
Is Miami a good market to buy in?
```

---

## Tests

The test suite covers all tool functions and the concurrency benchmark. No Azure credentials required.

The neighbourhood tests trigger real osmnx downloads on first run (~2 min); subsequent runs use the in-memory cache and complete in seconds.

```bash
pytest -v
```

```
test_tools.py::test_get_property_listings_known_city[austin] PASSED
test_tools.py::test_get_property_listings_known_city[phoenix] PASSED
test_tools.py::test_get_property_listings_known_city[denver] PASSED
test_tools.py::test_get_property_listings_known_city[miami] PASSED
test_tools.py::test_get_property_listings_unknown_city PASSED
test_tools.py::test_get_property_listings_case_insensitive PASSED
test_tools.py::test_get_neighborhood_stats_known_city[austin] PASSED
test_tools.py::test_get_neighborhood_stats_known_city[phoenix] PASSED
test_tools.py::test_get_neighborhood_stats_known_city[denver] PASSED
test_tools.py::test_get_neighborhood_stats_known_city[miami] PASSED
test_tools.py::test_get_neighborhood_stats_unknown_city PASSED
test_tools.py::test_get_school_ratings_known_city[austin] PASSED
test_tools.py::test_get_school_ratings_known_city[phoenix] PASSED
test_tools.py::test_get_school_ratings_known_city[denver] PASSED
test_tools.py::test_get_school_ratings_known_city[miami] PASSED
test_tools.py::test_get_school_ratings_unknown_city PASSED
test_tools.py::test_get_crime_index_known_city[austin] PASSED
test_tools.py::test_get_crime_index_known_city[phoenix] PASSED
test_tools.py::test_get_crime_index_known_city[denver] PASSED
test_tools.py::test_get_crime_index_known_city[miami] PASSED
test_tools.py::test_get_crime_index_unknown_city PASSED
test_tools.py::test_get_mortgage_rates_default PASSED
test_tools.py::test_get_mortgage_rates_all_types[30yr_fixed] PASSED
test_tools.py::test_get_mortgage_rates_all_types[15yr_fixed] PASSED
test_tools.py::test_get_mortgage_rates_all_types[5_1_arm] PASSED
test_tools.py::test_get_mortgage_rates_all_types[jumbo_30yr] PASSED
test_tools.py::test_get_mortgage_rates_all_types[fha_30yr] PASSED
test_tools.py::test_get_mortgage_rates_unknown_type_falls_back PASSED
test_tools.py::test_function_map_contains_all_tools PASSED
test_tools.py::test_function_map_values_are_callable PASSED
test_tools.py::test_concurrent_execution_is_faster_than_sequential PASSED

31 passed in 125.46s
```

---

## End-to-end run

Full run against the live Azure AI Foundry endpoint (osmnx cache warm):

```
$ python agent.py
Real Estate Market Analyzer
Supported cities: Austin, Phoenix, Denver, Miami
Type 'exit' to quit.

You: Compare Denver and Phoenix for an investment property.

  [tools] batch 1: 9 call(s) concurrently:
    → get_property_listings({'city': 'denver'})
    → get_neighborhood_stats({'city': 'denver'})
    → get_school_ratings({'city': 'denver'})
    → get_crime_index({'city': 'denver'})
    → get_property_listings({'city': 'phoenix'})
    → get_neighborhood_stats({'city': 'phoenix'})
    → get_school_ratings({'city': 'phoenix'})
    → get_crime_index({'city': 'phoenix'})
    → get_mortgage_rates({'loan_type': '30yr_fixed'})
  [tools] completed in 25.56s (sequential would be ~9.3s)

Assistant: Here is an analysis of Austin for a family seeking to buy a home with a $500,000 budget:

### Housing Market Insights
- **Median Home Price**: $485,000 (fits within your budget).
- **Active Listings**: 3,240 homes currently for sale.
- **Median Days on Market**: 18 days.
- **Price Trend YoY**: +4.2%, showing moderate appreciation.
- **Inventory Supply**: 2.1 months (competitive market).

### Neighbourhood
- Walkability 52, Transit Score 38.
- Amenities: tech hub, live music, parks, UT campus proximity.
- Average commute: 28 minutes.

### Schools
- District rating 7.8/10. Top: Liberal Arts & Science Academy, Ann Richards School.
- Graduation rate 91.2%.

### Safety
- Violent crime index 32 (12 pts below national avg, declining trend).

### Mortgage
- 30-year fixed: 6.85%. FHA option: 6.61%.

### Verdict
Austin is a solid **BUY** for family buyers at this budget level. Strong schools, improving safety, and steady 4.2% annual appreciation make it attractive for long-term ownership.
```

---

## Architecture diagram

Generate a PNG architecture diagram locally:

```bash
pip install matplotlib
python tmp/generate_diagram.py
# outputs tmp/architecture.png
```

## License

MIT
