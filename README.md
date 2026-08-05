# SAP Extensibility Decision Engine

Decides how a change should be built on S/4HANA — standard, config, key user,
in-app developer extension, or side-by-side — and shows the evidence behind it.

## Why this exists

AI coding tools pick up *after* the extensibility decision is made. They write
the code faster, which means a wrong choice now arrives sooner with better
syntax. The decision itself is made in a corridor conversation by one of a
handful of architects, from memory, and never written down. This tool makes
that decision explainable, consistent and auditable.

## Repo layout

```
app.py                  Streamlit UI
run_eval.py             Offline evaluation (backup for the live run)
requirements.txt
engine/
  __init__.py           MUST be in GitHub or you get ModuleNotFoundError
  schemas.py            Pydantic contracts
  llm.py                Gemini client, JSON enforcement, one retry
  intake.py             Step 1 — free text to structured requirement
  retrieval.py          Step 2 — search the grounded catalogue
  rules.py              Step 3 — deterministic tier rules
  decision.py           Step 4 — model writes the recommendation
  validator.py          Step 5 — strip anything invented
  pipeline.py           Runs 1-5 in order
data/
  mm_catalogue.json     The grounding corpus
  tier_rules.yaml       Rules an architect can edit
  gold_requirements.json  10 labelled test cases
```

## Deploy

1. Push everything to GitHub. **Check `engine/__init__.py` is actually there.**
   The GitHub web uploader silently skips empty folders and files starting with
   a dot in some browsers. If `engine/` is missing or empty, the deployed app
   fails with `ModuleNotFoundError: No module named 'engine'`.
2. Streamlit Community Cloud → New app → point at `app.py`.
3. Settings → Secrets → add:
   ```toml
   GEMINI_API_KEY = "your-key"
   ```
4. Deploy.

There's also a sidebar key box as a fallback, and `GEMINI_API_KEY` as an
environment variable works locally.

**Deploy a hello-world version on day one, not the night before.** First
deploys fail on something stupid and you don't want to find that out with
hours left.

## Before you demo

- Catalogue entries are marked `high`, `medium` or `low` confidence. Anything
  `low` should be deleted or replaced with an object you have actually used.
  The whole pitch is "this tool doesn't invent objects" — if the catalogue
  contains invented objects, an SAP person in the room will spot it.
- Twenty minutes with an architect scanning the object IDs covers this.

## The three requirements to demo

- **R01** — PO approval above 50k. Answer is standard workflow config. Teams
  routinely build a custom release routine because nobody checked.
- **R03** — carrier portal needs live stock. Answer is side-by-side, because
  the audience is outside the company.
- **R10** — predict late deliveries using weather data. Answer is **escalate**.

R10 is the one that wins the room. Everyone can show a tool being confident.
Almost nobody shows one admitting it doesn't know.

## Where the catalogue comes from in a real engagement

Hand-built here so we could move fast. In an engagement it's generated:

| Source | Where it comes from |
|---|---|
| Released APIs | SAP Business Accelerator Hub, OData metadata |
| Released CDS views, BAdIs | ADT released-objects tree, BAdI repository |
| Simplification items | SAP Readiness Check export |
| Key-user extensibility | Custom Fields and Logic business contexts |
| Custom code impact | ATC with the S/4HANA readiness variant |

One ingestion script normalises those exports into the same JSON schema. Run
offline, commit the result. The app never talks to SAP at runtime — no
connectivity, no credentials, no live system needed for a demo.
