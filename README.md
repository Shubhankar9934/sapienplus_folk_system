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


Here's how to start it on port 8000.

**1. Install the API dependencies (once):**

```powershell

pip install -e ".[api]"

```

**2. Run uvicorn on port 8000:**

```powershell

uvicorn folk.api.app:app --host 0.0.0.0 --port 8000 --reload

```


