# NBA Analysis Hub — Codex proof of concept

## Purpose
Test whether the existing 2026–27 team statistics CSV and the consolidated V1.2 team-profiles DOCX can be brought into a controlled, reproducible research repository **without changing source numbers**.

**This is not an NBA prediction model and is not game-day-ready.**

## Inputs
- `data/source/NBA_Team_Stats_2026-27_Download.csv` — original 30-team November 3 dataset
- `data/source/NBA_Team_Profiles_2026-27_V1.2.docx` — original V1.2 narrative and per-team tables

## Run on your PC or in Codex

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python src/audit.py
python -m unittest discover -s tests -v
```

Open the folder as a Codex workspace or commit it to a private Git repository. Codex should read `AGENTS.md` before modifying code or datasets.

## What the audit does
- Validates exactly 30 distinct NBA team abbreviations and basic numeric percentage ranges.
- Compares 43 displayed numeric CSV fields for each of 30 teams against the **original** V1.2 DOCX using direct cell-level comparisons (1,290 checks total).
- Produces `reports/audit.json` with mismatches, anomalies and explicit unresolved-cutoff / personnel / shot-zone warnings.
- Tests that deliberate source-data tampering causes a failed audit.

## What it does **not** do
- Does not verify source websites or game cutoffs, reconstruct unverified shot zones, reconcile historical chart values, or determine whether a defensive tendency is exploitable.
- Does not audit DOCX narrative conclusions, source provenance authenticity, or all data fields; 18 other CSV columns, plus the DOCX archival shot-zone tables, are not included in numeric reconciliation.
- Does not extract restricted websites, connect to a live NBA API, make player-level projections, or produce picks.

## Next implementation gates
1. Obtain and version the **complete latest approved** player-prop framework, not just its high-level project summary.
2. Create a source manifest with date range, collection time, units, ownership and verified-cutoff status for every dataset.
3. Add authorized source ingestion adapters and independent leaderboards/definition tests.
4. Add player game logs, minutes, opportunities and injury/rotation inputs with tested provenance.
5. Only after those pass: build reproducible game packets, model comparisons, and immutable postgame archives.

Review `docs/MIGRATION_PLAN.md` for the proposed repository growth path.
