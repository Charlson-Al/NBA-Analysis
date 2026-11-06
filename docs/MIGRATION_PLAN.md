# Planned evolution — proposal, not approved framework modification

| Stage | Deliverable | Promotion gate |
|---|---|---|
| POC (current) | Locked source files, CSV vs DOCX numeric audit, tests | 30-team coverage + zero mismatches; disclose coverage limits |
| Data integrity | Per-source snapshots, units, exact last-game cutoff, checksum and source manifest | Source cutoffs independently verified; no mixed denominators |
| Profiles | Reproducible per-team structured scouting evidence and DOCX output | Review 30 teams manually against source pages; no unsupported causal inference |
| Game packets | Matchup + personnel + player opportunity data | Confirm injuries/rotations, opponent resistance and player ownership |
| Projections | Preserve external forecasts; compare to independent supported expectations | Latest *approved* framework implemented and verified on known examples |
| Postgame | Immutable pregame archive, actuals, error diagnostics | Audit historical decision integrity, record failure modes without hindsight |

Source permissions and availability must be checked before creating ingestion scripts. Data not available by compliant, reproducible means remains manually supplied and clearly attributed.

## Suggested Codex kickoff prompt

Read AGENTS.md, README.md, reports/audit.json, and docs/MIGRATION_PLAN.md. Do not edit raw files. Explain the audit results and propose a source-manifest schema for the next stage. Do not write scraping code or modify analytical rules without explicit approval.
