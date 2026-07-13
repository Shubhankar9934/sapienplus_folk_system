# FOLK AI Council

An evidence-centric cultural-intelligence platform. It reviews statistically
generated FOLK scores for 171 base + 26 extension countries through a layered research
workflow and produces calibrated final scores, deterministic confidence, verified
references, full audit trails, and a **culture-first country profile** built for humans:
"if I moved here tomorrow, what cultural realities would I experience?"

> This is a **cultural research workflow**, not a chatbot debate platform. The hierarchy
> Framework Data -> Framework Signals -> Knowledge Pack -> Evidence -> Council Deliberation
> -> Integration -> Judgement -> Calibration -> Cultural Profile -> Website Profile is
> preserved throughout.

Each country is exported as **one self-contained document** (`outputs/countries/{ISO3}.json`)
containing evidence-grounded cultural themes, a visible Cultural Fingerprint (D1–D4),
reasoning-first council views, and the methodology behind every score.

## The four dimensions


| Code | Dimension  | Low pole (3)         | High pole (97)          |
| ---- | ---------- | -------------------- | ----------------------- |
| D1   | Identity   | Social (group-first) | Self (individual-first) |
| D2   | Expression | Restrained           | Open                    |
| D3   | Structure  | Fluid                | Certain                 |
| D4   | Drive      | Accepting            | Striving                |


Interpretive guardrails: D2 Open != extroverted; D3 != governance quality; D4 != individual work ethic.

## Architecture (frozen)

`L1 Data -> L2 Knowledge + Framework Signal Analyzer -> L3 Evidence -> L3.5 Reference Verification -> L4 Research Council (Statistician / Comparativist / Country Specialist / Devil's Advocate) -> L5 Integrator -> L6 Judge Council -> L7 Country Calibration -> L8 Global Calibration -> L8.5 Human Review Queue -> L9 Confidence -> L10 Cultural Profile (1 grounded LLM call + deterministic grounding filter) -> L11 Exports`. Cross-cutting: AuditTrace, RegionalCalibrationMemory, RunMetrics.

> **Culture-first changes:** the old narrative engine + validator are replaced by a single
> grounded cultural-profile call whose every observation must link to evidence `claim_ids`
> (a deterministic filter drops anything ungrounded). The council is **adaptive** — it skips
> the cross-critique/revision phases when the specialists already agree — and the
> decision-engine prose calls were removed. Net effect: ~16 LLM calls/country (down from ~28).



## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev,llm]"
cp .env.example .env            # then fill in keys (or set FOLK_PROVIDER_MODE=mock)
folk info
```

Set `FOLK_PROVIDER_MODE=mock` to run the entire pipeline offline with the deterministic
provider (no API keys needed) - used by the test suite.

## Source-of-truth documents (`Docs/`)

- `FOLK_AI_Council_System_Brief.docx` - technical build brief
- `Cultural_Intelligence_Framework.docx` + `Cultural_Dimensions_Framework_Note_1.txt` - framework intent
- `FOLK_Agent_Prompts_v2.md` - the council/judge/cultural-themes prompts (intellectual core)
- `INDEX OF 171 - WITH FRAMEWORK SCORES.xlsx` - the input dataset



## Smoke test (offline, no API keys)

The fastest way to verify everything works end-to-end. `mock` mode runs the entire
pipeline with the deterministic provider — no keys, no cost, a few seconds.

```powershell
# 1. Run the test suite (uses mock mode automatically)
pytest

# 2. Generate a few country profiles offline + export the culture-first docs
$env:FOLK_PROVIDER_MODE = "mock"
python -m folk.cli run --isos "KOR,DEU,JPN" --no-resume
Remove-Item Env:FOLK_PROVIDER_MODE          # clear the override afterwards
```

This writes `outputs/countries/{KOR,DEU,JPN}.json`, `outputs/index.json`, and
`outputs/run_summary.txt`. Inspect a country doc to confirm the structure
(snapshot, cultural_themes, council_views, methodology) looks right.

```bash
# macOS/Linux equivalent
FOLK_PROVIDER_MODE=mock python -m folk.cli run --isos "KOR,DEU,JPN" --no-resume
```

You're also fully set up for a **live run**. All three providers (Anthropic
`claude-sonnet-4-6`, OpenAI `gpt-4o`, DeepSeek `deepseek-chat`) connect, config resolves
to **live**, the SDKs are installed, per-country failures are non-fatal, and `outputs/`
is clean.

## How to run

**1. Open a fresh terminal** in the project root and make sure the mock override isn't set (it would override `.env`):

```powershell
cd C:\Users\Shubhankar\Desktop\FOLK
Remove-Item Env:FOLK_PROVIDER_MODE -ErrorAction SilentlyContinue
python -m folk.cli info
```

Confirm it prints `Provider mode: live`.

**2. Sanity-check the anchors live (cheap, ~5 countries / ~85 calls):**

```powershell
python -m folk.cli calibrate
```

Expect `passed=True` with KOR_d1=50, TUR_d2=50, TUR_d4=50, COL_d3=50. (Reference-country range warnings for NLD/JPN are informational, not failures.)

**3. Small live smoke test first (recommended, ~32 calls):**

```powershell
python -m folk.cli run --isos "KOR,DEU" --no-resume
```

Check the per-country docs in `outputs/countries/` look right before the big run.

> Note: the report aggregates **every** profile in the DB, not just the ISOs you
> passed. If older runs are still saved, a 2-country smoke test will report all of
> them. Reset first (step 4) if you want the report to reflect only this run.

**4. Reset to a clean slate (optional, before a fresh full run):**

Wipe the database, the resume checkpoint, and stale `folk_`* report files so the
next run starts from scratch:

```powershell
python -m folk.cli reset
```

Add `--keep-outputs` to clear the database only and leave existing report files in place:

```powershell
python -m folk.cli reset --keep-outputs
```

**5. Full run — all 197 countries:**

```powershell
python -m folk.cli run
```

To wipe everything and run from scratch in a single command, use `--fresh`
(equivalent to `reset` then `run`):

```powershell
python -m folk.cli run --fresh
```

**6. Re-export anytime from the saved DB (no API calls):**

```powershell
python -m folk.cli export
```

Add `--full-exports` to `run` or `export` to also emit the legacy aggregate
JSON/Excel deliverables (off by default):

```powershell
python -m folk.cli export --full-exports
```



## Serve the platform (backend API + frontend)

The frontend reads the exported `outputs/` over HTTP. Run the API and the Next.js app
in **two terminals**.

**Terminal 1 — backend API** (serves `outputs/countries/*.json` + `index.json`):

```powershell
python -m folk.cli api                 # http://127.0.0.1:8000 (add --reload while developing)
```

Requires the API extra: `pip install -e ".[api]"`. Endpoints include `/api/stats`,
`/api/countries`, `/api/countries/{iso3}`, `/api/countries/{iso3}/council`,
`/api/countries/{iso3}/sources`, and `/api/map`.

**Terminal 2 — frontend** (Next.js 15 + React Query):

```powershell
cd frontend
npm install                            # first time only
npm run dev                            # http://localhost:3000
```

The frontend points at the API via `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

For a production build, use `npm run build` then `npm run start`.

## Where output is saved

Everything writes to `**outputs/**` automatically. The default run is **culture-first**:

- `outputs/countries/{ISO3}.json` — one self-contained doc per country (cultural profile
  - resolved sources + score methodology). This is what the API/frontend serve.
- `outputs/index.json` — slim country list (fingerprint readings, scores) + global stats.
- `outputs/run_summary.txt` — validation + calibration + human-review queue summary.
- `outputs/folk.sqlite` — the database (enables resume).
- `outputs/folk_run_log.jsonl` — per-country log.

With `--full-exports`, the legacy aggregate deliverables are added too:
`folk_final_scores.json/.xlsx`, `folk_adjustment_log.xlsx`,
`folk_reference_library.json`, `folk_validation_report.json`.

## Important notes

- **Scale/cost:** ~~16 LLM calls per country (≤12 council + 1 integrator + 2 judges + 1 grounded cultural profile) × 197 ≈ **~~3,150 real API calls** across the three providers, and fewer when the adaptive council skips the debate phases for countries where specialists agree. It will take a while and cost real money — that's why I suggest the 2-country test first.
- **Resumable:** if the run is interrupted, just run `python -m folk.cli run` again — it skips countries already in the DB and continues (checkpoints every 10). For a fully fresh DB, use `python -m folk.cli reset` (or `python -m folk.cli run --fresh`) instead of deleting `outputs/folk.sqlite` by hand.
- **Failures don't abort:** any country whose model output can't be parsed is logged, added to `failed_countries` in the report, and the batch keeps going.
- **Rotate your keys** after this, since they were shared in chat.

The FastAPI app lives at `folk.api.app:app` (module-level `app` on line 394), and the project uses a `src/` layout with `uvicorn` provided via the `api` optional dependency.

Here's how to start it on port 8000.

**1. Install the API dependencies (once):**

```powershell

pip install -e ".[api]"

```

**2. Run uvicorn on port 8000:**

```powershell

uvicorn folk.api.app:app --host 0.0.0.0 --port 8000 --reload

```

Notes:

- Run both from the project root `c:\Users\Shubhankar\Desktop\FOLK`).
- `pip install -e ".[api]"` makes the `folk` package importable (handles the `src/` layout) and installs `fastapi` + `uvicorn[standard]`.
- `--reload` auto-restarts on code changes; drop it for production.
- If you'd rather not install the package, you can instead set the source path:

```powershell

$env:PYTHONPATH="src"; uvicorn [folk.api.app](http://folk.api.app):app --port 8000 --reload

```

Want me to run it for you?

python scripts/generate_baseline_vs_[final.py](http://final.py)

python -m folk.cli run --isos "TZA,TJK,FJI,OMN,HND,KEN,DOM,SYR,BIH,SLE,BFA,LUX,POL,MAR,BTN,MNG,QAT,AUT,KAZ,VNM,ZMB,GEO,MYS,MWI,MMR" --audit