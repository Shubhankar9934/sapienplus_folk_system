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
