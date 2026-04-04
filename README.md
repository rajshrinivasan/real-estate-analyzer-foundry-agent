# Real Estate Market Analyzer

An Azure AI Foundry agent that answers natural-language questions about residential property markets in Austin, Phoenix, Denver, and Miami.

**Key pattern — async concurrent tool execution:** when the model requests multiple data sources in a single turn, all tool calls fire in parallel via `asyncio.gather()`. Total wait time equals the slowest tool, not the sum.

```
Sequential: 1.2 + 0.8 + 1.5 + 0.9 + 0.5 = 4.9 s
Concurrent: max(1.2, 0.8, 1.5, 0.9, 0.5) = 1.5 s   (3.3× faster)
```

Ships two interfaces: an interactive **CLI** and a **FastAPI web UI**.

---

## Architecture

```
┌────────────────────┐    ┌────────────────────┐
│        CLI         │    │      Web UI        │
│     agent.py       │    │  app.py · FastAPI  │
└─────────┬──────────┘    └──────────┬─────────┘
          └──────────────┬───────────┘
                         │
            ┌────────────▼────────────┐
            │      AgentSession       │
            │  orchestration layer    │
            └────────────┬────────────┘
                         │
            ┌────────────▼────────────┐
            │  Azure AI Foundry Agent │
            │  gpt-4o · tool routing  │
            └────────────┬────────────┘
                         │
               asyncio.gather()
                         │
    ┌──────┬─────────────┼──────────┬──────┐
    ▼      ▼             ▼          ▼      ▼
[List.] [Neigh.] [Schools] [Crime] [Mortg.]
  1.2s    0.8s     1.5s     0.9s    0.5s
          │                         │
          └────────────┬────────────┘
                       ▼
                   data.py
             simulated data stores
```

---

## Files

```
14-real-estate-analyzer/
├── agent.py               # AgentSession class + CLI entry point
├── app.py                 # FastAPI web application
├── tools.py               # Five async tool functions
├── data.py                # Simulated market data stores
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

```bash
pytest -v
```

Sample output:

```
test_tools.py::test_get_property_listings[austin] PASSED
test_tools.py::test_get_property_listings[phoenix] PASSED
test_tools.py::test_get_property_listings[denver] PASSED
test_tools.py::test_get_property_listings[miami] PASSED
test_tools.py::test_get_property_listings_unknown_city PASSED
test_tools.py::test_get_property_listings_case_insensitive PASSED
test_tools.py::test_get_neighborhood_stats[austin] PASSED
...
test_tools.py::test_concurrent_execution_is_faster_than_sequential PASSED

28 passed in 3.07s
```

---

## Sample timing output (CLI)

```
You: Analyse Austin for a family buyer with a $500k budget.

  [tools] batch 1: 5 call(s) concurrently:
    → get_property_listings({'city': 'austin'})
    → get_neighborhood_stats({'city': 'austin'})
    → get_school_ratings({'city': 'austin'})
    → get_crime_index({'city': 'austin'})
    → get_mortgage_rates({'loan_type': '30yr_fixed'})
  [tools] completed in 1.51s (sequential would be ~4.9s)

Assistant: Austin is a solid **BUY** for family buyers...
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
