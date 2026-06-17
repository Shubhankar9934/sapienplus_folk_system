---
name: Fix Adjustment Log Provenance
overview: Make the adjustment log and dissent record deterministically derived from canonical pipeline values (not LLM free text), add a hard consistency invariant, fix the narrative validator to actually receive the narrative, and stop global calibration from false-flagging missing anchors on subset/smoke runs.
todos:
  - id: deterministic-adjustments
    content: In integrator _enforce_invariants, re-derive adjustment_log and dissent_record from enforced canonical scores (thread council in; extract _dissent helper). Do not touch final_scores.
    status: completed
  - id: consistency-invariant
    content: Add ScoreConsistencyError + assert adjustment_log.baseline==baseline_scores and adjustment_log.final==final_scores (and dissent final_score) in CountryProcessor.process before returning.
    status: completed
  - id: validator-prompt
    content: Include the composed narrative text + final scores in the NarrativeValidator user prompt so the LLM validates real content (fixes KOR false-fail).
    status: completed
  - id: global-anchor-skip
    content: In GlobalCalibrator, skip anchors whose country is absent from the processed vectors instead of flagging them missing; keep present-but-wrong as a violation.
    status: completed
  - id: regression-tests
    content: "Add tests: adjustment-log provenance, invariant raises on tamper, end-to-end log==profile scores, validator PASS not queued, global subset run has no anchor_violation."
    status: completed
isProject: false
---

# Fix Adjustment Log Provenance (and two smaller smoke-test issues)

The final scores are canonical and correct. Do NOT modify scoring (`final_scores`, the CI clamp, judges, calibration scores). The work is to fix the audit artifacts that drifted from the pipeline and add guards.

## Root cause (confirmed)

In live mode, `generate_structured` merges the LLM JSON over the deterministic hint (`payload = {**mock_hint, **payload}`, [src/folk/llm/base.py](src/folk/llm/base.py) L84-88). The integrator's `_enforce_invariants` then re-derives `final_scores` and `anchor_positions` from canonical data but leaves `adjustment_log`/`dissent_record` as whatever the LLM wrote ([src/folk/integrator/engine.py](src/folk/integrator/engine.py) L53-76). So the LLM's hallucinated "textbook Germany" (D2 38.5->36, D4 72->68) survives, while baselines (62.95/79.41) and finals (62/78) live everywhere else.

## 1. Make adjustment log + dissent deterministic (primary fix)

In [src/folk/integrator/engine.py](src/folk/integrator/engine.py):
- In `_enforce_invariants`, after `out.final_scores = fixed`, also re-derive the audit records from the enforced canonical scores (mirroring the existing `anchor_positions` recompute):
  - `out.adjustment_log = self._adjustments(pack, fixed)` -> guarantees `baseline == pack.baselines[d].baseline` (== `profile.baseline_scores`) and `final == fixed[d]` (== `profile.final_scores`).
  - Re-derive `out.dissent_record` from `council.phase3` against `fixed` so `final_score` matches the canonical final.
- Thread `council` into `_enforce_invariants` (signature becomes `_enforce_invariants(out, hint, pack, council)`); `integrate()` already has `council`. Extract the dissent-building loop from `_compute` (L102-111) into a helper `_dissent(phase3, locks, final)` reused by both `_compute` and `_enforce_invariants`.
- Net effect: the LLM may still phrase reasoning, but provenance fields (baseline/final/proposed/final_score) are always pipeline-derived. This keeps `final_scores` untouched (no scoring change).

## 2. Hard invariant: adjustment log must match profile scores

Add a small validator (new `src/folk/pipeline/invariants.py`, or a function in [src/folk/pipeline/processor.py](src/folk/pipeline/processor.py)) and call it in `CountryProcessor.process` right after `_assemble_profile`, before returning:
- For each `a` in `profile.adjustment_log`: assert `a.baseline == profile.baseline_scores[a.dimension]` (float-tolerant) and `int(a.final) == profile.final_scores[a.dimension].score`.
- Also assert each `dissent_record[].final_score == profile.final_scores[dim].score`.
- On violation raise `ScoreConsistencyError(iso3, dimension, detail)`.
- This fails the country hard: `Pipeline._process_one` is wrapped in try/except ([src/folk/pipeline/pipeline.py](src/folk/pipeline/pipeline.py) L83-88), so the country is recorded in `failed_countries` and never persisted/exported with an inconsistent log, while the batch continues (consistent with existing resilience). Nothing inconsistent can reach exports.

## 3. Feed the narrative to the narrative validator (fixes KOR false-fail)

In [src/folk/narrative/validator.py](src/folk/narrative/validator.py) `validate`:
- The user prompt currently is `narrative_validator_prompt() + "\nCOUNTRY: {iso3}"` only - the LLM literally has no narrative to check and returns FAIL ("No CountryNarrative text was provided").
- Append the actual content to the user prompt: the composed narrative (executive summary, full narrative, website card, regional, per-dimension interpretations) plus `integ.final_scores`, so the LLM validates real text. The deterministic `_check` already computes the correct PASS/FAIL hint; this aligns the live LLM with it.
- Result: KOR no longer spuriously fails `narrative_validation` -> drops out of the human review queue.

## 4. Global calibration: ignore missing anchors on subset runs

In [src/folk/calibration/global_calibration.py](src/folk/calibration/global_calibration.py) L50-56:
- When an anchor country is not in the processed `vectors` (`v is None`), skip it (`continue`) instead of appending `"<ISO> missing"`.
- Keep the real check: anchor present but `!= 50` still records a violation.
- This clears the false `anchor_violation` flag and `requires_redeliberation=True` on the 2-country smoke run, while still catching a genuinely wrong anchor in a full run.

## 5. Regression tests

Add to [tests/test_council_integrator.py](tests/test_council_integrator.py) (and a small new test module if cleaner):
- Adjustment log provenance: after `Integrator().integrate(...)`, every `adjustment_log[d].baseline == pack.baselines[d].baseline` and `.final == out.final_scores[d]`; every `dissent_record.final_score == out.final_scores[dim]`.
- Invariant guard: construct a profile whose adjustment log is tampered (baseline/final altered) and assert the consistency check raises `ScoreConsistencyError`.
- End-to-end ([tests/test_integration.py](tests/test_integration.py)): for every processed profile and every `adjustment_log` entry, `entry.baseline == baseline_scores[dim]` and `entry.final == final_scores[dim].score`; and `narrative.dimensions[d].score == final_scores[d].score`.
- Narrative validator: a passing narrative yields `verdict == PASS` and is not queued for `narrative_validation_failed`.
- Global calibration subset: `GlobalCalibrator().calibrate([KOR, DEU vectors])` produces no `anchor_violation` flag and `requires_redeliberation is False`.

## Out of scope (per instruction)
- No changes to `final_scores`, the CI clamp in `scoring.py`, judges, or calibration score math.
- `KOR:D1` midpoint review (D1 locked to 50) is expected/benign; left as-is.