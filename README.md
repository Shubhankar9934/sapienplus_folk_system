# FOLK AI Council

An evidence-centric cultural-intelligence scoring platform. It reviews statistically
generated FOLK scores for 171 base + 26 extension countries through a layered research
workflow and produces calibrated final scores, deterministic confidence, verified
references, full audit trails, and website-ready narratives.

> This is a **cultural research workflow**, not a chatbot debate platform. The hierarchy
> Framework Data -> Framework Signals -> Knowledge Pack -> Evidence -> Council Deliberation
> -> Integration -> Judgement -> Calibration -> Narrative -> Website Profile is preserved
> throughout.

## The four dimensions


| Code | Dimension  | Low pole (3)         | High pole (97)          |
| ---- | ---------- | -------------------- | ----------------------- |
| D1   | Identity   | Social (group-first) | Self (individual-first) |
| D2   | Expression | Restrained           | Open                    |
| D3   | Structure  | Fluid                | Certain                 |
| D4   | Drive      | Accepting            | Striving                |


Interpretive guardrails: D2 Open != extroverted; D3 != governance quality; D4 != individual work ethic.

## Architecture (frozen)

`L1 Data -> L2 Knowledge + Framework Signal Analyzer -> L3 Evidence -> L3.5 Reference Verification -> L4 Research Council (Statistician / Comparativist / Country Specialist / Devil's Advocate) -> L5 Integrator -> L6 Judge Council -> L7 Country Calibration -> L8 Global Calibration -> L8.5 Human Review Queue -> L9 Confidence -> L10 Narrative -> L10.5 Narrative Validator -> L11 Exports`. Cross-cutting: AuditTrace, RegionalCalibrationMemory, RunMetrics.

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
- `FOLK_Agent_Prompts_v2.md` - the council/judge/narrative prompts (intellectual core)
- `INDEX OF 171 - WITH FRAMEWORK SCORES.xlsx` - the input dataset

## Testing

```bash
pytest
```

You're fully set up for a live run. All three providers (Anthropic `claude-sonnet-4-6`, OpenAI `gpt-4o`, DeepSeek `deepseek-chat`) connect, config resolves to **live**, the SDKs are installed, per-country failures are now non-fatal, and `outputs/` is clean.

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

**3. Small live smoke test first (recommended, ~34 calls):**

```powershell
python -m folk.cli run --isos "KOR,DEU" --no-resume
```

Check the files in `outputs/` look right before the big run.

> Note: the report aggregates **every** profile in the DB, not just the ISOs you
> passed. If older runs are still saved, a 2-country smoke test will report all of
> them. Reset first (step 4) if you want the report to reflect only this run.

**4. Reset to a clean slate (optional, before a fresh full run):**

Wipe the database, the resume checkpoint, and stale `folk_*` report files so the
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

## Where output is saved
Everything writes to **`outputs/`** automatically:
- `folk_final_scores.json` — full country profiles
- `folk_final_scores.xlsx` — flat score table
- `folk_adjustment_log.xlsx` — adjustment history
- `folk_reference_library.json` — deduplicated references
- `folk_validation_report.json` / `.txt` — validation + calibration + review queue
- `folk_run_log.jsonl` — per-country log
- `folk.sqlite` — the database (enables resume)

## Important notes
- **Scale/cost:** ~17 LLM calls per country (12 council + 1 integrator + 2 judges + 1 narrative + 1 validator) × 197 ≈ **~3,350 real API calls** across the three providers. It will take a while and cost real money — that's why I suggest the 2-country test first.
- **Resumable:** if the run is interrupted, just run `python -m folk.cli run` again — it skips countries already in the DB and continues (checkpoints every 10). For a fully fresh DB, use `python -m folk.cli reset` (or `python -m folk.cli run --fresh`) instead of deleting `outputs/folk.sqlite` by hand.
- **Failures don't abort:** any country whose model output can't be parsed is logged, added to `failed_countries` in the report, and the batch keeps going.
- **Rotate your keys** after this, since they were shared in chat.

