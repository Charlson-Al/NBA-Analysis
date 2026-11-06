---
name: nba-v22-research
description: Guide NBA-Analysis research through the approved November 3 V2.2 stages, evidence records and lock checklist without assigning basketball judgments.
---

# NBA V2.2 research execution

Use for an authorized player-prop research session, execution audit or checklist
review in this repository. This skill is navigation, not a replacement framework,
a new framework version, or permission to collect restricted source data.
Do not spawn specialized subagents. Do not schedule work or place wagers.

## Authority at intake

1. Read root AGENTS.md and the complete authoritative source:
   `docs/framework/source/nba-player-props-v2.2-2026-11-03.txt`.
2. Check its SHA-256 against `manifests/framework-sources.json` and the validator's
   pinned digest. Read the explicit approval in `docs/governance/decisions.md`.
3. Read `docs/governance/v22-execution-refinements.md`; establish which approvals
   apply at the research checkpoint. Retain date/time and approval references.
   A later approval is not contemporaneous evidence for a historical slate.
4. Flag conflicting source versions/instructions. Preserve the historical rules
   actually used and report the conflict; never silently replace historical text.
5. Confirm user scope and authorized sources/private storage. Standard full-game
   PrizePicks lines govern ranking/selection after the approved restriction.
   Eight-market screening remains broad; disagreement is not automatic exclusion.

## Private execution record

Follow `docs/research/execution-tracker.md`. Use the `tracker` CLI with an explicit
owner-only root outside Git. Initialize the session, seed unreviewed coverage,
and append records referencing source IDs and exact input event IDs (`basis`).
Run `check` at intake and after material changes. Exit 2 means findings, not a
crash or automatic Pass. Review the private Markdown report. Never put real
research inputs, credentials, placement evidence or private reports in public Git.
Use synthetic examples for code tests. Preserve raw authorized source artifacts
privately; the tracker stores references/hashes, not source authenticity proofs.

## Five existing stages

1. **Environment/personnel (§1A–1E).** Evaluate both offenses and defenses,
   compatible pace/efficiency/Four Factors/shot channels, schedule and scripts.
   Distinguish tendencies from exploitable vulnerabilities. Verify personnel,
   rotations and credible DC minutes. Link shared uncertainties to every affected
   candidate; preserve source cutoffs, samples, units, filters and denominators.
2. **Models (§2A–2F).** Screen credible rotation players over PTS, REB, AST, 3PM,
   PR, PA, RA, PRA, considering Higher and Lower. Preserve original DC forecasts,
   minutes and accessible uncertainty. Preserve original DARKO statistical values,
   minutes and rate basis; DPM is not a box-score rate. Validate compatible
   normalization once to DC minutes and normalize components before summing.
   Compare exact thresholds; investigate splits and independently supported
   opportunities. Do not average or alter official projections.
3. **Independent validation (§3A–3C).** The analyst supplies each existing 0–2
   factor: role, opportunities, matchup, sustainability. Require distinct evidence
   and distinguish volume, quality and conversion. Verify player-specific shot,
   passing, rebound or three-point channels and combined components. Missing data
   is not zero or automatically neutral. Leave unsupported factors incomplete.
4. **Outlook (§4A–4E).** Analyst records supported direction/neighborhood and
   realistic failure scenarios without constructing a third projection model.
   Keep every material risk resolved, carried or disqualifying with rationale.
   Credible minutes sensitivities remain separate diagnostics, not new forecasts.
5. **Market/ranking (§5A–5I).** Verify exact eligible threshold, provider, tier,
   availability, payout and settlement; distinguish winning/tie/losing counts.
   Recompute model relationship on line changes. Analyst judges variability,
   meaningful advantage, strongest player lane, rank and original grade. Preserve
   existing grade eligibility: A-range requires agreement and at least 7/8 plus
   all other §5D conditions; genuine disagreement has B+ maximum. These are
   eligibility limits, not automatic grades. Compare the weakest finalist with
   the strongest credible eligible exclusion substantively; disclose comparison
   coverage and consider teammate competition/correlation/shared scripts.

## Lock, preserve and review

- Review every §III lock row (L01–L17 in the generated checklist). Recheck material
  personnel/market developments. A mechanically clean record is not permission
  to finalize: final analytical decisions remain with the analyst/user.
- Record research candidates, finalized analytical selections and explicitly
  confirmed wagers separately. Never infer placement from a recommendation.
- Pin the exact reviewed versions in an append-only decision record. Retain its
  event ID for `report --at`; do not change a pregame grade after results.
- Apply §§IV–V postgame using the original checkpoint. Review wins and losses,
  combined components and exclusions without hindsight. Missing opportunity
  tracking stays missing; box scores do not establish chances or shot quality.
- Preserve the five-slate protocol and historical warning dispositions. Reuse
  verified current findings and update only affected conclusions when evidence
  changes. No new scores, grade ceilings, model adjustments or versions.
